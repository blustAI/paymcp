"""
State handling utilities for payment session management.
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
    Check for existing payment state and handle recovery.

    Args:
        session_id: Current session ID
        state_store: StateStore instance
        provider: Payment provider instance
        tool_name: Name of the tool being executed
        tool_args: Arguments passed to the tool

    Returns:
        Tuple of (payment_id, payment_url, stored_args, should_execute_immediately)
        - should_execute_immediately is True if payment was already completed
    """
    if not session_id or not state_store:
        return None, None, None, False

    logger.debug(f"Checking state store for session_id={session_id}")
    state = state_store.get(session_id)

    if not state:
        return None, None, None, False

    logger.info(f"Found existing payment state for session_id={session_id}")
    payment_id = state.get('payment_id')
    payment_url = state.get('payment_url')
    stored_args = state.get('tool_args', {})
    stored_func_name = state.get('tool_name', '')

    # Check payment status with provider
    try:
        status = provider.get_payment_status(payment_id)
        logger.info(f"Payment status for {payment_id}: {status}")

        if status == "paid":
            # Payment already completed!
            logger.info(f"Previous payment detected, executing with original request")
            # Clean up state
            state_store.delete(session_id)

            # Return stored args if they were for this function
            if stored_func_name == tool_name:
                return payment_id, payment_url, stored_args, True
            else:
                # Different function, use current args
                return payment_id, payment_url, None, True

        elif status in ("pending", "processing"):
            # Payment still pending, use existing payment
            logger.info(f"Payment still pending, continuing with existing payment")
            return payment_id, payment_url, None, False

        elif status in ("canceled", "expired", "failed"):
            # Payment failed, clean up and create new one
            logger.info(f"Previous payment {status}, creating new payment")
            state_store.delete(session_id)
            return None, None, None, False

    except Exception as err:
        logger.error(f"Error checking payment status: {err}")
        # If we can't check status, clean up and create new payment
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
    Save payment state for recovery.

    Args:
        session_id: Current session ID
        state_store: StateStore instance
        payment_id: Payment ID from provider
        payment_url: Payment URL
        tool_name: Name of the tool being executed
        tool_args: Arguments passed to the tool
        status: Current payment status
    """
    if not session_id or not state_store:
        return

    logger.info(f"Storing payment state for session_id={session_id}")
    state_store.put(session_id, {
        'session_id': session_id,
        'payment_id': payment_id,
        'payment_url': payment_url,
        'tool_name': tool_name,
        'tool_args': tool_args,
        'status': status,
        'created_at': __import__('time').time()
    })


def update_payment_status(
    session_id: Optional[str],
    state_store: Any,
    status: str
) -> None:
    """
    Update the status of an existing payment state.

    Args:
        session_id: Current session ID
        state_store: StateStore instance
        status: New payment status
    """
    if not session_id or not state_store:
        return

    state = state_store.get(session_id)
    if state:
        state['status'] = status
        state_store.put(session_id, state)
        logger.debug(f"Updated payment status to {status} for session_id={session_id}")


def cleanup_payment_state(
    session_id: Optional[str],
    state_store: Any
) -> None:
    """
    Clean up payment state after completion or cancellation.

    Args:
        session_id: Current session ID
        state_store: StateStore instance
    """
    if session_id and state_store:
        state_store.delete(session_id)
        logger.debug(f"Cleaned up payment state for session_id={session_id}")