# paymcp/payment/flows/two_step.py
import functools
import time
import logging
from typing import Dict, Any
from ...utils.messages import open_link_message, opened_webview_message
from ..webview import open_payment_webview_if_available

logger = logging.getLogger(__name__)

# Legacy in-memory storage for backward compatibility
PENDING_ARGS: Dict[str, Dict[str, Any]] = {}


def make_paid_wrapper(func, mcp, provider, price_info, state_store=None):
    """
    Implements the two‑step payment flow:

    1. The original tool is wrapped by an *initiate* step that returns
       `payment_url` and `payment_id` to the client.
    2. A dynamically registered tool `confirm_<tool>` waits for payment,
       validates it, and only then calls the original function.

    Now uses StateStore for consistency with other flows (ENG-114).
    Falls back to in-memory storage if no StateStore provided.
    """

    confirm_tool_name = f"confirm_{func.__name__}_payment"

    # --- Step 2: payment confirmation -----------------------------------------
    @mcp.tool(
        name=confirm_tool_name,
        description=f"Confirm payment and execute {func.__name__}()"
    )
    async def _confirm_tool(payment_id: str, ctx=None):
        logger.info(f"[confirm_tool] Received payment_id={payment_id}")

        # Try to get session ID from context for state store
        session_id = None
        if ctx and hasattr(ctx, 'session'):
            if hasattr(ctx.session, 'id'):
                session_id = ctx.session.id
            elif hasattr(ctx.session, 'session_id'):
                session_id = ctx.session.session_id

        # Try to retrieve args from state store first
        original_args = None
        state_key = None

        if state_store:
            # First try with session_id if available
            if session_id:
                state = state_store.get(session_id)
                if state and state.get('payment_id') == payment_id:
                    original_args = state.get('tool_args', {})
                    state_key = session_id
                    logger.debug(f"[confirm_tool] Retrieved args from state store using session_id")

            # If not found by session_id, try payment_id as key
            if not original_args:
                state = state_store.get(payment_id)
                if state:
                    original_args = state.get('tool_args', {})
                    state_key = payment_id
                    logger.debug(f"[confirm_tool] Retrieved args from state store using payment_id")

        # Fall back to legacy PENDING_ARGS if not found in state store
        if not original_args:
            original_args = PENDING_ARGS.pop(str(payment_id), None)
            logger.debug(f"[confirm_tool] Retrieved args from legacy PENDING_ARGS")

        logger.debug(f"[confirm_tool] Retrieved args: {original_args}")
        if original_args is None:
            raise RuntimeError("Unknown or expired payment_id")

        status = provider.get_payment_status(payment_id)
        if status != "paid":
            raise RuntimeError(
                f"Payment status is {status}, expected 'paid'"
            )
        logger.debug(f"[confirm_tool] Calling {func.__name__} with args: {original_args}")

        # Call the original tool with its initial arguments
        result = await func(**original_args)

        # Clean up state if we used state store
        if state_store and state_key:
            state_store.delete(state_key)

        return result

    # --- Step 1: payment initiation -------------------------------------------
    @functools.wraps(func)
    async def _initiate_wrapper(*args, **kwargs):
        # Extract session ID from context
        ctx = kwargs.get("ctx", None)
        session_id = None

        # Try to get session ID from context
        if ctx and hasattr(ctx, 'session'):
            if hasattr(ctx.session, 'id'):
                session_id = ctx.session.id
            elif hasattr(ctx.session, 'session_id'):
                session_id = ctx.session.session_id

        # Check for existing payment state if we have a session ID and state store
        if session_id and state_store:
            logger.debug(f"Checking state store for session_id={session_id}")
            state = state_store.get(session_id)

            if state:
                logger.info(f"Found existing payment state for session_id={session_id}")
                payment_id = state.get('payment_id')
                payment_url = state.get('payment_url')
                stored_func_name = state.get('tool_name', '')

                # Check payment status with provider
                try:
                    status = provider.get_payment_status(payment_id)
                    logger.info(f"Payment status for {payment_id}: {status}")

                    if status == "paid":
                        # Payment already completed! Execute tool with original arguments
                        logger.info(f"Previous payment detected, executing immediately")

                        # Get original args from state
                        original_args = state.get('tool_args', {})

                        # Clean up state
                        state_store.delete(session_id)

                        # Use stored arguments if they were for this function
                        if stored_func_name == func.__name__:
                            # Merge stored args with current kwargs (stored args take precedence)
                            merged_kwargs = {**kwargs}
                            merged_kwargs.update(original_args)
                            return await func(*args, **merged_kwargs)
                        else:
                            # Different function, just execute normally
                            return await func(*args, **kwargs)

                    elif status in ("pending", "processing"):
                        # Payment still pending, return existing payment info
                        if (open_payment_webview_if_available(payment_url)):
                            message = opened_webview_message(
                                payment_url, price_info["price"], price_info["currency"]
                            )
                        else:
                            message = open_link_message(
                                payment_url, price_info["price"], price_info["currency"]
                            )

                        return {
                            "message": f"Payment still pending: {message}",
                            "payment_url": payment_url,
                            "payment_id": str(payment_id),
                            "next_step": confirm_tool_name,
                        }

                except Exception as e:
                    logger.error(f"Error checking payment status: {e}")
                    # Continue to create new payment if error

        # Create new payment
        payment_id, payment_url = provider.create_payment(
            amount=price_info["price"],
            currency=price_info["currency"],
            description=f"{func.__name__}() execution fee"
        )

        if (open_payment_webview_if_available(payment_url)):
            message = opened_webview_message(
                payment_url, price_info["price"], price_info["currency"]
            )
        else:
            message = open_link_message(
                payment_url, price_info["price"], price_info["currency"]
            )

        pid_str = str(payment_id)

        # Store in state store if available
        if state_store:
            # Use session_id as primary key if available, otherwise use payment_id
            store_key = session_id if session_id else pid_str
            logger.info(f"Storing payment state with key={store_key}")
            state_store.put(store_key, {
                'session_id': session_id,
                'payment_id': payment_id,
                'payment_url': payment_url,
                'tool_name': func.__name__,
                'tool_args': kwargs,  # Store all kwargs for replay
                'status': 'requested',
                'created_at': time.time()
            })

            # Also store by payment_id for backward compatibility
            if session_id and store_key != pid_str:
                state_store.put(pid_str, {
                    'session_id': session_id,
                    'payment_id': payment_id,
                    'payment_url': payment_url,
                    'tool_name': func.__name__,
                    'tool_args': kwargs,
                    'status': 'requested',
                    'created_at': time.time()
                })
        else:
            # Fall back to legacy PENDING_ARGS
            PENDING_ARGS[pid_str] = kwargs

        # Return data for the user / LLM
        return {
            "message": message,
            "payment_url": payment_url,
            "payment_id": pid_str,
            "next_step": confirm_tool_name,
        }

    return _initiate_wrapper