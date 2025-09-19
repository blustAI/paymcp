# paymcp/payment/flows/elicitation.py
import functools
import time
import logging
from ...utils.messages import open_link_message, opened_webview_message
from ..webview import open_payment_webview_if_available
from ...utils.elicitation import run_elicitation_loop

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

        # Extract session ID from context
        session_id = None

        # Try to get session ID from context
        if ctx and hasattr(ctx, 'session'):
            if hasattr(ctx.session, 'id'):
                session_id = ctx.session.id
            elif hasattr(ctx.session, 'session_id'):
                session_id = ctx.session.session_id

        # Check for existing payment state if we have a session ID and state store
        payment_id = None
        payment_url = None

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
                        logger.info(f"[make_paid_wrapper] Previous payment detected, executing with original request")

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
                        # Payment still pending, use existing payment
                        logger.info(f"Payment still pending, continuing with existing payment")
                        # Continue to elicitation with existing payment

                    elif status in ("canceled", "expired", "failed"):
                        # Payment failed, clean up and create new one
                        logger.info(f"Previous payment {status}, creating new payment")
                        state_store.delete(session_id)
                        payment_id = None
                        payment_url = None

                except Exception as e:
                    logger.error(f"Error checking payment status: {e}")
                    # If we can't check status, create a new payment
                    state_store.delete(session_id)
                    payment_id = None
                    payment_url = None

        # Create new payment if needed
        if not payment_id:
            # 1. Initiate payment
            payment_id, payment_url = provider.create_payment(
                amount=price_info["price"],
                currency=price_info["currency"],
                description=f"{func.__name__}() execution fee"
            )
            logger.debug(f"[make_paid_wrapper] Created payment with ID: {payment_id}")

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

        # 2. Ask the user to confirm payment
        logger.debug(f"[make_paid_wrapper] Calling elicitation {ctx}")

        try:
            payment_status = await run_elicitation_loop(ctx, func, message, provider, payment_id)
        except Exception as e:
            logger.warning(f"[make_paid_wrapper] Payment confirmation failed: {e}")
            # Don't delete state on timeout - payment might still complete
            if session_id and state_store:
                state = state_store.get(session_id)
                if state:
                    state['status'] = 'timeout'
                    state_store.put(session_id, state)
            raise

        if (payment_status=="paid"):
            logger.info(f"[make_paid_wrapper] Payment confirmed, calling {func.__name__}")

            # Update state to paid if we have state store
            if session_id and state_store:
                state = state_store.get(session_id)
                if state:
                    state['status'] = 'paid'
                    state_store.put(session_id, state)

            result = await func(*args,**kwargs) #calling original function

            # Clean up state after successful execution
            if session_id and state_store:
                state_store.delete(session_id)

            return result

        if (payment_status=="canceled"):
            logger.info(f"[make_paid_wrapper] Payment canceled")

            # Clean up state on cancellation
            if session_id and state_store:
                state_store.delete(session_id)

            return {
                "status": "canceled",
                "message": "Payment canceled by user"
            }
        else:
            logger.info(f"[make_paid_wrapper] Payment not received after retries")

            # Keep state for pending payments
            if session_id and state_store:
                state = state_store.get(session_id)
                if state:
                    state['status'] = 'pending'
                    state_store.put(session_id, state)

            return {
                "status": "pending",
                "message": "We haven't received the payment yet. Click the button below to check again.",
                "next_step": func.__name__,
                "payment_id": str(payment_id)
            }

    return wrapper