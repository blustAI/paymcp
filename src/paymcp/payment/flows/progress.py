# paymcp/payment/flows/progress.py
import asyncio
import functools
import time
import logging
from typing import Any, Dict, Optional
from ...utils.messages import open_link_message, opened_webview_message
from ..webview import open_payment_webview_if_available
from ...utils.context import extract_session_id, log_context_info
from ...utils.state import (
    check_existing_payment,
    save_payment_state,
    update_payment_status,
    cleanup_payment_state
)

logger = logging.getLogger(__name__)

DEFAULT_POLL_SECONDS = 3          # how often to poll provider.get_payment_status
MAX_WAIT_SECONDS = 15 * 60        # give up after 15 min


def make_paid_wrapper(
    func,
    mcp,
    provider,
    price_info,
    state_store=None,  # StateStore for handling timeouts
):
    """
    One-step flow that *holds the tool open* and reports progress
    via ctx.report_progress() until the payment is completed.

    Now with StateStore integration for ENG-114 timeout handling.
    """

    @functools.wraps(func)
    async def _progress_wrapper(*args, **kwargs):
        # Extract session ID from context
        ctx = kwargs.get("ctx", None)

        # Optional: log context info for debugging
        log_context_info(ctx)

        # Extract session ID using utility function
        session_id = extract_session_id(ctx)

        # Helper to emit progress safely
        async def _notify(message: str, progress: Optional[int] = None):
            if ctx is not None and hasattr(ctx, "report_progress"):
                await ctx.report_progress(
                    message=message,
                    progress=progress or 0,
                    total=100,
                )

        # Check for existing payment state
        payment_id, payment_url, stored_args, should_execute = check_existing_payment(
            session_id, state_store, provider, func.__name__, kwargs
        )

        # If payment was already completed, execute immediately
        if should_execute:
            await _notify("Previous payment detected — executing with original request …", progress=100)
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
            payment_id, payment_url = provider.create_payment(
                amount=price_info["price"],
                currency=price_info["currency"],
                description=f"{func.__name__}() execution fee"
            )

            # Store payment state if we have session ID and state store
            if session_id and state_store:
                logger.info(f"Storing payment state for session_id={session_id}")
                state_store.put(session_id, {
                    'session_id': session_id,
                    'payment_id': payment_id,
                    'payment_url': payment_url,
                    'tool_name': func.__name__,
                    'tool_args': kwargs,  # Store all kwargs for replay
                    'status': 'requested',
                    'created_at': time.time()
                })

        if (open_payment_webview_if_available(payment_url)):
            message = opened_webview_message(
                payment_url, price_info["price"], price_info["currency"]
            )
        else:
            message = open_link_message(
                payment_url, price_info["price"], price_info["currency"]
            )

        # Initial message with the payment link
        await _notify(
            message,
            progress=0,
        )

        # Poll provider until paid, canceled, or timeout
        waited = 0
        while waited < MAX_WAIT_SECONDS:
            await asyncio.sleep(DEFAULT_POLL_SECONDS)
            waited += DEFAULT_POLL_SECONDS

            status = provider.get_payment_status(payment_id)

            if status == "paid":
                await _notify("Payment received — generating result …", progress=100)

                # Update state to paid
                update_payment_status(session_id, state_store, 'paid')

                break

            if status in ("canceled", "expired", "failed"):
                # Clean up state on failure
                cleanup_payment_state(session_id, state_store)
                raise RuntimeError(f"Payment status is {status}, expected 'paid'")

            # Still pending → ping progress
            await _notify(f"Waiting for payment … ({waited}s elapsed)")

        else:  # loop exhausted
            # Don't delete state on timeout - payment might still complete
            update_payment_status(session_id, state_store, 'timeout')
            raise RuntimeError("Payment timeout reached; aborting")

        # Call the underlying tool with its original args/kwargs
        result = await func(*args, **kwargs)

        # Clean up state after successful execution
        cleanup_payment_state(session_id, state_store)

        return result

    return _progress_wrapper