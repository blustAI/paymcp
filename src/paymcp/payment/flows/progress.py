# paymcp/payment/flows/progress.py
import asyncio
import functools
import time
import logging
from typing import Any, Dict, Optional
from ...utils.messages import open_link_message, opened_webview_message
from ..webview import open_payment_webview_if_available

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
        session_id = None

        # Try to get session ID from context
        if ctx and hasattr(ctx, 'session'):
            if hasattr(ctx.session, 'id'):
                session_id = ctx.session.id
            elif hasattr(ctx.session, 'session_id'):
                session_id = ctx.session.session_id

        # Helper to emit progress safely
        async def _notify(message: str, progress: Optional[int] = None):
            if ctx is not None and hasattr(ctx, "report_progress"):
                await ctx.report_progress(
                    message=message,
                    progress=progress or 0,
                    total=100,
                )

        # Check for existing payment state if we have a session ID and state store
        if session_id and state_store:
            logger.debug(f"Checking state store for session_id={session_id}")
            state = state_store.get(session_id)

            if state:
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
                        # Payment already completed! Execute tool with original arguments
                        await _notify("Previous payment detected — executing with original request …", progress=100)

                        # Clean up state
                        state_store.delete(session_id)

                        # Use stored arguments if they were for this function
                        if stored_func_name == func.__name__:
                            # Merge stored args with current kwargs (stored args take precedence)
                            merged_kwargs = {**kwargs}
                            merged_kwargs.update(stored_args)
                            return await func(*args, **merged_kwargs)
                        else:
                            # Different function, just execute normally
                            return await func(*args, **kwargs)

                    elif status in ("pending", "processing"):
                        # Payment still pending, show the payment URL again
                        await _notify(
                            f"Payment still pending — please complete payment at: {payment_url}",
                            progress=50
                        )

                        # Continue to polling loop below
                        # Don't create a new payment

                    elif status in ("canceled", "expired", "failed"):
                        # Payment failed, clean up and create new one
                        logger.info(f"Previous payment {status}, creating new payment")
                        state_store.delete(session_id)
                        # Fall through to create new payment
                        payment_id = None
                        payment_url = None

                except Exception as e:
                    logger.error(f"Error checking payment status: {e}")
                    # If we can't check status, create a new payment
                    state_store.delete(session_id)
                    payment_id = None
                    payment_url = None
            else:
                payment_id = None
                payment_url = None
        else:
            payment_id = None
            payment_url = None

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

                # Update state to paid if we have state store
                if session_id and state_store:
                    state = state_store.get(session_id)
                    if state:
                        state['status'] = 'paid'
                        state_store.put(session_id, state)

                break

            if status in ("canceled", "expired", "failed"):
                # Clean up state on failure
                if session_id and state_store:
                    state_store.delete(session_id)
                raise RuntimeError(f"Payment status is {status}, expected 'paid'")

            # Still pending → ping progress
            await _notify(f"Waiting for payment … ({waited}s elapsed)")

        else:  # loop exhausted
            # Don't delete state on timeout - payment might still complete
            if session_id and state_store:
                state = state_store.get(session_id)
                if state:
                    state['status'] = 'timeout'
                    state_store.put(session_id, state)
            raise RuntimeError("Payment timeout reached; aborting")

        # Call the underlying tool with its original args/kwargs
        result = await func(*args, **kwargs)

        # Clean up state after successful execution
        if session_id and state_store:
            state_store.delete(session_id)

        return result

    return _progress_wrapper