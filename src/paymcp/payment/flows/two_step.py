import functools
import time
import logging
from typing import Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ...state_store import StateStoreProvider
from ...utils.messages import open_link_message, opened_webview_message
from ..webview import open_payment_webview_if_available
from ...utils.context import extract_session_id, log_context_info
from ...utils.state import (
    check_existing_payment,
    save_payment_state,
    update_payment_status,
    cleanup_payment_state
)
from ...utils.constants import PaymentStatus, ResponseType
from ...utils.flow import (
    call_original_tool,
    log_flow,
    extract_tool_description
)
from ...utils.response import (
    build_error_response,
    build_pending_response,
    build_success_response,
    format_two_step_message
)

logger = logging.getLogger(__name__)

# Legacy in-memory storage for backward compatibility
PENDING_ARGS: Dict[str, Dict[str, Any]] = {}


def retrieve_stored_args(
    payment_id: str,
    state_store: Optional['StateStoreProvider'] = None,
    logger: Optional[logging.Logger] = None
) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Retrieve stored arguments for a payment ID.

    This function handles the dual-storage strategy for two-step flow:
    1. First tries direct lookup by payment_id (most efficient)
    2. Falls back to iterating through sessions (for backward compatibility)
    3. Finally checks legacy PENDING_ARGS if state store unavailable

    Args:
        payment_id: The payment ID to look up
        state_store: Optional persistent storage (Redis, InMemory, etc.)
        logger: Optional logger for debug output

    Returns:
        Tuple of (original_args, state_key) where:
        - original_args: The stored tool arguments or None if not found
        - state_key: The key used to retrieve (for cleanup), or None
    """
    original_args = None
    state_key = None

    # Strategy 1: Check state store if available
    if state_store:
        # Try optimized O(1) lookup using payment_id index
        state = state_store.get_by_payment_id(payment_id)
        if state:
            original_args = state.get('tool_args', {})
            # Determine the actual storage key (could be session_id or payment_id)
            state_key = state.get('session_id') or payment_id
            log_flow(logger, 'TwoStep', 'debug',
                    f"Retrieved args via payment_id index, state_key={state_key}")
            return original_args, state_key

        # Fallback: Try direct key lookup (for backward compatibility)
        # This handles cases where payment_id is the primary key
        state = state_store.get(payment_id)
        if state:
            original_args = state.get('tool_args', {})
            state_key = payment_id
            session_id = state.get('session_id')
            log_flow(logger, 'TwoStep', 'debug',
                    f"Retrieved args from state store using payment_id as key, session_id={session_id}")
            return original_args, state_key

    # Strategy 2: Fall back to legacy in-memory PENDING_ARGS
    # This maintains backward compatibility with deployments that don't use state store
    if not original_args:
        original_args = PENDING_ARGS.get(str(payment_id), None)
        if original_args:
            log_flow(logger, 'TwoStep', 'debug',
                    f"Retrieved args from legacy PENDING_ARGS, keys: {list(PENDING_ARGS.keys())}")

    return original_args, state_key


def store_payment_args(
    session_id: Optional[str],
    payment_id: str,
    payment_url: str,
    tool_name: str,
    kwargs: Dict[str, Any],
    state_store: Optional['StateStoreProvider'] = None,
    logger: Optional[logging.Logger] = None
) -> None:
    """
    Store payment arguments using dual-key strategy for two-step flow.

    Storage strategy:
    1. Always store under session_id if available (primary key)
    2. Also store under payment_id for direct lookup in confirm step
    3. Fall back to legacy PENDING_ARGS if no state store

    This dual-key approach ensures:
    - Fast O(1) lookup in confirm step using payment_id
    - Session-based recovery after timeouts
    - Backward compatibility with older clients

    Args:
        session_id: Optional session identifier from client context
        payment_id: Unique payment identifier from provider
        payment_url: URL for payment completion
        tool_name: Name of the tool being paid for
        kwargs: Original tool arguments to store
        state_store: Optional persistent storage
        logger: Optional logger for debug output
    """
    pid_str = str(payment_id)

    # Primary storage: Store by session_id if available
    # This enables session-based recovery after timeouts
    save_payment_state(
        session_id, state_store, payment_id, payment_url,
        tool_name, kwargs, PaymentStatus.REQUESTED
    )

    # Note: With the new payment_id index in StateStore, we no longer need
    # to store duplicate entries. The StateStore automatically maintains
    # a payment_id -> key index for O(1) lookups.
    # We only need to ensure payment_id is included in the state.
    if state_store:
        # The StateStore will automatically index by payment_id
        # No need for duplicate storage anymore
        log_flow(logger, 'TwoStep', 'debug',
                f"State stored with automatic payment_id indexing")
    else:
        # Fallback: Use legacy in-memory storage when state store unavailable
        # This maintains backward compatibility but loses persistence on restart
        PENDING_ARGS[pid_str] = kwargs
        log_flow(logger, 'TwoStep', 'debug',
                f"Stored args in legacy PENDING_ARGS for payment_id={pid_str}")


def cleanup_payment_args(
    state_key: Optional[str],
    payment_id: str,
    state_store: Optional['StateStoreProvider'] = None,
    logger: Optional[logging.Logger] = None
) -> None:
    """
    Clean up payment arguments after successful execution.

    Cleanup strategy:
    1. Delete the primary entry (found via state_key)
    2. Delete the secondary payment_id entry if different
    3. Clean up legacy PENDING_ARGS if applicable

    This ensures no orphaned entries remain in storage, preventing:
    - Memory leaks from accumulating payment data
    - Confusion from stale payment entries
    - Potential security issues from lingering sensitive data

    Args:
        state_key: The key used to retrieve the args (session_id or payment_id)
        payment_id: The payment ID to clean up
        state_store: Optional persistent storage
        logger: Optional logger for debug output
    """
    if state_key and state_store:
        # Clean up the primary entry
        # The StateStore will automatically clean up the payment_id index
        cleanup_payment_state(state_key, state_store)
        log_flow(logger, 'TwoStep', 'debug',
                f"Cleaned up state for key={state_key}, payment_id index auto-removed")
    else:
        # Fallback: Clean up from legacy in-memory storage
        PENDING_ARGS.pop(str(payment_id), None)
        log_flow(logger, 'TwoStep', 'debug',
                f"Cleaned up legacy PENDING_ARGS for payment_id={payment_id}")


def make_paid_wrapper(func, mcp, provider, price_info, state_store: Optional['StateStoreProvider'] = None):
    """
    Implements the two‑step payment flow with timeout resilience.

    Flow Overview:
    1. INITIATE STEP: Original tool call triggers payment creation
       - Creates payment with provider
       - Stores tool arguments using dual-key strategy
       - Returns payment_url and confirm tool name to client

    2. CONFIRM STEP: Separate tool validates and executes
       - Client calls confirm_<tool>_payment with payment_id
       - Retrieves stored arguments (handles timeout recovery)
       - Validates payment status with provider
       - Executes original tool if paid
       - Cleans up all stored state

    Key Features:
    - Timeout resilience: State persists across client disconnections
    - Dual-key storage: Fast O(1) lookup while maintaining session tracking
    - Backward compatibility: Falls back to legacy in-memory storage
    - Idempotency: Reusing existing payments when appropriate

    Args:
        func: Original tool function to wrap
        mcp: MCP server instance for registering confirm tool
        provider: Payment provider for creating/checking payments
        price_info: Pricing configuration (amount, currency)
        state_store: Optional persistent storage for timeout recovery
    """

    confirm_tool_name = f"confirm_{func.__name__}_payment"

    # --- Step 2: Payment Confirmation Tool -----------------------------------
    # This is a separate MCP tool that gets registered for payment confirmation
    # It's called by the client after payment completion
    @mcp.tool(
        name=confirm_tool_name,
        description=f"Confirm payment and execute {func.__name__}()"
    )
    async def _confirm_tool(payment_id: str, ctx=None):
        """Confirmation tool: validates payment and executes original function."""
        log_flow(logger, 'TwoStep', 'info',
                f"[confirm_tool] Received payment_id={payment_id}")

        # Retrieve stored arguments using our dual-key retrieval strategy
        # This handles both direct payment_id lookup and session-based fallback
        original_args, state_key = retrieve_stored_args(
            payment_id, state_store, logger
        )

        log_flow(logger, 'TwoStep', 'debug',
                f"[confirm_tool] Retrieved args: {original_args}, state_key: {state_key}")

        # Validate that we found stored arguments
        # If not found, payment_id is invalid or expired (TTL exceeded)
        if original_args is None:
            return build_error_response(
                "Unknown or expired payment_id",
                reason="invalid_payment_id",
                payment_id=payment_id
            )

        # Verify payment status with the provider (source of truth)
        # This ensures payment was actually completed, not just claimed
        try:
            status = provider.get_payment_status(payment_id)
            log_flow(logger, 'TwoStep', 'debug',
                    f"[confirm_tool] Payment status: {status}")
        except Exception as e:
            # Provider communication failure - don't execute tool
            log_flow(logger, 'TwoStep', 'error',
                    f"[confirm_tool] Failed to get payment status: {e}")
            return build_error_response(
                f"Failed to check payment status: {str(e)}",
                reason="status_check_failed",
                payment_id=payment_id
            )

        # Only proceed if payment is confirmed paid
        if status != PaymentStatus.PAID:
            return build_error_response(
                f"Payment status is {status}, expected 'paid'",
                reason="payment_not_complete",
                payment_id=payment_id
            )

        log_flow(logger, 'TwoStep', 'debug',
                f"[confirm_tool] Calling {func.__name__} with args: {original_args}")

        # Execute the original tool with stored arguments
        # This is the actual work the user paid for
        result = await call_original_tool(func, {}, original_args)

        # Clean up all payment data (both session_id and payment_id entries)
        # This prevents memory leaks and removes sensitive data
        cleanup_payment_args(state_key, payment_id, state_store, logger)

        return build_success_response(result, payment_id)

    # --- Step 1: Payment Initiation Wrapper ----------------------------------
    # This wraps the original tool and handles payment creation
    @functools.wraps(func)
    async def _initiate_wrapper(*args, **kwargs):
        """Initiation wrapper: creates payment and returns payment info to client."""

        # Extract context and session ID for state management
        # Session ID enables recovery after timeouts
        ctx = kwargs.get("ctx", None)
        session_id = extract_session_id(ctx)

        # Log context details for debugging client integration issues
        log_context_info(ctx)

        log_flow(logger, 'TwoStep', 'debug',
                f"[initiate] Starting for {func.__name__}, session_id={session_id}")

        # Check for existing payment to ensure idempotency
        # This handles:
        # 1. Duplicate requests from impatient users
        # 2. Recovery after client timeout/reconnection
        # 3. Completed payments that can execute immediately
        payment_id, payment_url, stored_args, should_execute = check_existing_payment(
            session_id, state_store, provider, func.__name__, kwargs
        )

        # Optimization: Skip payment flow if already paid
        # This can happen when client reconnects after payment but before execution
        if should_execute:
            log_flow(logger, 'TwoStep', 'info',
                    "[initiate] Payment already completed, executing tool")
            if stored_args:
                # Use originally stored arguments (preserves exact request)
                merged_kwargs = {**kwargs}
                merged_kwargs.update(stored_args)
                return await call_original_tool(func, args, merged_kwargs)
            else:
                # Execute with current arguments (no stored state found)
                return await call_original_tool(func, args, kwargs)

        # Reuse existing pending payment to avoid duplicate charges
        # This is critical for user experience and prevents confusion
        if payment_id and payment_url:
            log_flow(logger, 'TwoStep', 'info',
                    f"[initiate] Payment pending, returning existing: {payment_id}")

            # Generate appropriate message based on client capabilities
            # Webview provides better UX when available
            if open_payment_webview_if_available(payment_url):
                message = opened_webview_message(
                    payment_url, price_info["price"], price_info["currency"]
                )
            else:
                message = open_link_message(
                    payment_url, price_info["price"], price_info["currency"]
                )

            response_msg = format_two_step_message(
                f"Payment still pending: {message}",
                payment_url,
                str(payment_id),
                confirm_tool_name
            )

            return build_pending_response(
                response_msg["message"],
                str(payment_id),
                payment_url,
                next_step=confirm_tool_name
            )

        # Create new payment session with provider
        # This is the first-time payment request for this tool invocation
        payment_id, payment_url = provider.create_payment(
            amount=price_info["price"],
            currency=price_info["currency"],
            description=extract_tool_description(func.__name__, 'two_step')
        )

        if open_payment_webview_if_available(payment_url):
            message = opened_webview_message(
                payment_url, price_info["price"], price_info["currency"]
            )
        else:
            message = open_link_message(
                payment_url, price_info["price"], price_info["currency"]
            )

        pid_str = str(payment_id)

        # Store payment arguments using dual-key strategy
        # This enables both fast lookup and session-based recovery
        store_payment_args(
            session_id, payment_id, payment_url,
            func.__name__, kwargs, state_store, logger
        )

        log_flow(logger, 'TwoStep', 'info',
                f"[initiate] Payment initiated pid={pid_str} url={payment_url} next={confirm_tool_name}")

        # Return structured response for client/LLM consumption
        # Includes all necessary info for payment completion and confirmation
        response_msg = format_two_step_message(
            message,
            payment_url,
            pid_str,
            confirm_tool_name
        )

        # Pending response indicates payment required before execution
        # Client should:
        # 1. Complete payment at payment_url
        # 2. Call confirm_tool_name with payment_id
        return build_pending_response(
            response_msg["message"],
            pid_str,
            payment_url,
            next_step=confirm_tool_name
        )

    return _initiate_wrapper