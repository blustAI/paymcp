"""
State management utilities for payment session persistence and recovery.

This module provides critical functionality for handling payment state across
timeouts, disconnections, and reconnections. It implements the core logic for
ENG-114 (Client timeout issue) by persisting payment state in a StateStore.

Key Features:
1. Idempotency: Prevents duplicate payments for the same session
2. Recovery: Resumes payments after client timeout/disconnect
3. Cleanup: Manages state lifecycle to prevent memory leaks
4. Status tracking: Monitors payment progression through various states

The utilities work with any StateStoreProvider (InMemory, Redis, etc.)
to provide persistent payment state management.
"""
import logging
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)


def check_existing_payment(
    session_id: Optional[str],
    state_store: Any,
    provider: Any,
    tool_name: str,
    tool_args: Any
) -> Tuple[Optional[str], Optional[str], Optional[Dict], bool]:
    """
    Check for existing payment state and intelligently handle recovery scenarios.

    This is the core function for preventing duplicate payments. It:
    1. Looks up any existing payment for the current session
    2. Checks the actual payment status with the provider
    3. Decides whether to reuse, execute, or create new payment

    Recovery Scenarios Handled:
    - Client timeout: Payment completed after client disconnected
    - Duplicate request: Same tool called again in same session
    - Failed payment: Previous payment failed, need new one
    - Pending payment: Payment still processing, wait for completion

    Args:
        session_id: Current session ID from MCP context.
                   None means no session support.
        state_store: StateStore instance (InMemory, Redis, etc.).
                    None means state persistence disabled.
        provider: Payment provider instance with get_payment_status method.
        tool_name: Name of the tool being executed (for verification).
        tool_args: Current arguments passed to the tool.

    Returns:
        Tuple of (payment_id, payment_url, stored_args, should_execute_immediately):
        - payment_id: Existing payment ID if found, None otherwise
        - payment_url: Existing payment URL if found, None otherwise
        - stored_args: Original args from when payment was created
        - should_execute_immediately: True if payment already completed (skip flow)

    Example:
        >>> payment_id, url, args, execute = check_existing_payment(
        ...     "session_123", store, provider, "generate", {"prompt": "test"}
        ... )
        >>> if execute:
        ...     # Payment already done, execute tool immediately
        ...     return tool_function(**args or tool_args)
    """
    if not session_id or not state_store:
        return None, None, None, False

    # Step 1: Retrieve existing state from store
    logger.debug(f"Checking state store for session_id={session_id}")
    state = state_store.get(session_id)

    if not state:
        # No existing payment for this session
        return None, None, None, False

    # Step 2: Extract payment information from stored state
    logger.info(f"Found existing payment state for session_id={session_id}")
    payment_id = state.get('payment_id')
    payment_url = state.get('payment_url')
    stored_args = state.get('tool_args', {})
    stored_func_name = state.get('tool_name', '')

    # Step 3: Verify actual payment status with provider (source of truth)
    # This handles cases where payment completed after client disconnected
    try:
        status = provider.get_payment_status(payment_id)
        logger.info(f"Payment status for {payment_id}: {status}")

        # Scenario 1: Payment already completed (e.g., after timeout)
        if status == "paid":
            logger.info(f"Previous payment detected, executing with original request")
            # Clean up state since payment is done
            state_store.delete(session_id)

            # Use appropriate arguments based on tool match
            if stored_func_name == tool_name:
                # Same tool: use original args to maintain consistency
                return payment_id, payment_url, stored_args, True
            else:
                # Different tool: payment covers session, use current args
                return payment_id, payment_url, None, True

        # Scenario 2: Payment still in progress
        elif status in ("pending", "processing"):
            logger.info(f"Payment still pending, continuing with existing payment")
            # Reuse existing payment, don't create duplicate
            return payment_id, payment_url, None, False

        # Scenario 3: Payment failed or was canceled
        elif status in ("canceled", "expired", "failed"):
            logger.info(f"Previous payment {status}, creating new payment")
            # Clean up failed payment state
            state_store.delete(session_id)
            # Signal to create new payment
            return None, None, None, False

    except Exception as err:
        # Provider communication failure
        logger.error(f"Error checking payment status: {err}")
        # Conservative approach: clean up and create new payment
        # This prevents stuck states but might create duplicate payments
        state_store.delete(session_id)
        return None, None, None, False

    return payment_id, payment_url, None, False


def save_payment_state(
    session_id: Optional[str],
    state_store: Any,
    payment_id: str,
    payment_url: str,
    tool_name: str,
    tool_args: Any,
    status: str = 'requested'
) -> None:
    """
    Persist payment state for recovery after timeout or disconnection.

    This function saves all necessary information to resume a payment flow
    after the client reconnects. The state is keyed by session_id to ensure
    each session has at most one active payment.

    State Contents:
    - Payment details: ID, URL for completion
    - Tool information: Name and arguments for execution
    - Metadata: Status, timestamps for debugging

    The saved state enables:
    1. Resuming payment after client timeout
    2. Preventing duplicate payments
    3. Executing the correct tool with original args
    4. Debugging payment issues

    Args:
        session_id: Current session ID from MCP context.
                   If None, state won't be saved (no recovery).
        state_store: StateStore instance (InMemory, Redis, etc.).
                    If None, state won't be saved.
        payment_id: Unique payment ID from provider.
        payment_url: URL where user completes payment.
        tool_name: Name of the tool being paid for.
        tool_args: Original arguments to pass to tool after payment.
        status: Current payment status (default: 'requested').

    Side Effects:
        Writes to state_store with TTL based on store configuration.
        Overwrites any existing state for the session_id.

    Example:
        >>> save_payment_state(
        ...     "session_123", store, "pay_abc", "https://pay.me",
        ...     "generate", {"prompt": "test"}, "requested"
        ... )
    """
    if not session_id or not state_store:
        return

    logger.info(f"Storing payment state for session_id={session_id}")

    # Create comprehensive state object
    state_data = {
        'session_id': session_id,      # For cross-reference
        'payment_id': payment_id,      # Provider's payment identifier
        'payment_url': payment_url,    # Where user completes payment
        'tool_name': tool_name,        # Tool to execute after payment
        'tool_args': tool_args,        # Original args to preserve
        'status': status,              # Current payment status
        'created_at': __import__('time').time()  # Timestamp for TTL/debugging
    }

    # Store with automatic TTL based on StateStore configuration
    # InMemoryStore: Default 1 hour TTL
    # RedisStore: Configurable TTL
    state_store.put(session_id, state_data)


def update_payment_status(
    session_id: Optional[str],
    state_store: Any,
    status: str
) -> None:
    """
    Update the status of an existing payment state without losing other data.

    This function is used to track payment progression through various states:
    - requested: Initial state when payment created
    - pending: Payment URL opened, awaiting completion
    - paid: Payment successfully completed
    - timeout: Client disconnected while waiting
    - canceled: User explicitly canceled
    - failed: Payment failed for any reason

    Status updates are important for:
    1. Debugging payment issues
    2. Analytics and monitoring
    3. Deciding recovery strategy

    Args:
        session_id: Current session ID from MCP context.
        state_store: StateStore instance.
        status: New payment status to set.

    Side Effects:
        Updates existing state in store.
        If no existing state, this is a no-op.

    Example:
        >>> update_payment_status("session_123", store, "paid")
    """
    if not session_id or not state_store:
        return

    # Retrieve existing state
    state = state_store.get(session_id)
    if state:
        # Update only the status field, preserve other data
        state['status'] = status
        # Optional: Add status change timestamp for debugging
        state[f'status_{status}_at'] = __import__('time').time()
        # Write back to store
        state_store.put(session_id, state)
        logger.debug(f"Updated payment status to {status} for session_id={session_id}")
    else:
        logger.warning(f"No state found to update for session_id={session_id}")


def cleanup_payment_state(
    session_id: Optional[str],
    state_store: Any
) -> None:
    """
    Remove payment state after completion, cancellation, or failure.

    Cleanup is critical for:
    1. Preventing memory leaks in long-running services
    2. Removing sensitive payment information
    3. Allowing new payments for the session
    4. Maintaining clean state store

    This should be called:
    - After successful payment and tool execution
    - After payment cancellation
    - After payment failure (non-recoverable)
    - NOT after timeout (payment might still complete)

    Args:
        session_id: Current session ID from MCP context.
        state_store: StateStore instance.

    Side Effects:
        Deletes state from store.
        If using Redis, removes key immediately.
        If using InMemory, removes from map.

    Example:
        >>> # After successful execution
        >>> result = await tool_function(**args)
        >>> cleanup_payment_state(session_id, store)
        >>> return result
    """
    if session_id and state_store:
        state_store.delete(session_id)
        logger.debug(f"Cleaned up payment state for session_id={session_id}")