# paymcp/payment/flows/elicitation.py
import functools
import time
import logging
from ...utils.messages import open_link_message, opened_webview_message
from ..webview import open_payment_webview_if_available
from ...utils.elicitation import run_elicitation_loop
from ...utils.context import extract_session_id, log_context_info
from ...utils.state import (
    check_existing_payment,
    save_payment_state,
    update_payment_status,
    cleanup_payment_state
)

logger = logging.getLogger(__name__)

def make_paid_wrapper(func, mcp, provider, price_info, state_store=None):
    """
    Single-step payment flow using elicitation during execution.
    Now with StateStore integration for ENG-114 timeout handling.
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        ctx = kwargs.get("ctx", None)
        logger.debug(f"[make_paid_wrapper] Starting tool: {func.__name__}")

        # Extract session ID from context using utility function
        session_id = extract_session_id(ctx)

        # Check for existing payment state
        payment_id, payment_url, stored_args, should_execute = check_existing_payment(
            session_id, state_store, provider, func.__name__, {'ctx': ctx}
        )

        # If payment was already completed, execute immediately
        if should_execute:
            if stored_args:
                # Use stored arguments
                merged_kwargs = {**kwargs}
                merged_kwargs.update(stored_args)
                return await func(*args, **merged_kwargs)
            else:
                # Execute with current arguments
                return await func(*args, **kwargs)

        # Create new payment if needed
        if not payment_id:
            # 1. Initiate payment
            payment_id, payment_url = provider.create_payment(
                amount=price_info["price"],
                currency=price_info["currency"],
                description=f"{func.__name__}() execution fee"
            )
            logger.debug(f"[make_paid_wrapper] Created payment with ID: {payment_id}")

            # Store payment state using utility
            save_payment_state(
                session_id, state_store, payment_id, payment_url,
                func.__name__, kwargs, 'requested'
            )

        if (open_payment_webview_if_available(payment_url)):
            message = opened_webview_message(
                payment_url, price_info["price"], price_info["currency"]
            )
        else:
            message = open_link_message(
                payment_url, price_info["price"], price_info["currency"]
            )

        # 2. Ask the user to confirm payment
        logger.debug(f"[make_paid_wrapper] Calling elicitation {ctx}")

        try:
            payment_status = await run_elicitation_loop(ctx, func, message, provider, payment_id)
        except Exception as e:
            logger.warning(f"[make_paid_wrapper] Payment confirmation failed: {e}")
            # Don't delete state on timeout - payment might still complete
            update_payment_status(session_id, state_store, 'timeout')
            raise

        if (payment_status=="paid"):
            logger.info(f"[make_paid_wrapper] Payment confirmed, calling {func.__name__}")

            # Update state to paid
            update_payment_status(session_id, state_store, 'paid')

            result = await func(*args,**kwargs) #calling original function

            # Clean up state after successful execution
            cleanup_payment_state(session_id, state_store)

            return result

        if (payment_status=="canceled"):
            logger.info(f"[make_paid_wrapper] Payment canceled")

            # Clean up state on cancellation
            cleanup_payment_state(session_id, state_store)

            return {
                "status": "canceled",
                "message": "Payment canceled by user"
            }
        else:
            logger.info(f"[make_paid_wrapper] Payment not received after retries")

            # Keep state for pending payments
            update_payment_status(session_id, state_store, 'pending')

            return {
                "status": "pending",
                "message": "We haven't received the payment yet. Click the button below to check again.",
                "next_step": func.__name__,
                "payment_id": str(payment_id)
            }

    return wrapper