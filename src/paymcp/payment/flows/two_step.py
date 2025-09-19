# paymcp/payment/flows/two_step.py
import functools
import time
import logging
from typing import Dict, Any
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
        # Extract session ID from context using utility
        session_id = extract_session_id(ctx)

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
            original_args = PENDING_ARGS.get(str(payment_id), None)
            logger.debug(f"[confirm_tool] PENDING_ARGS keys: {list(PENDING_ARGS.keys())}")
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

        # Clean up based on where we got the args from
        if state_key:
            # Args came from state store, clean up there
            cleanup_payment_state(state_key, state_store)
        else:
            # Args came from legacy PENDING_ARGS, remove from there
            PENDING_ARGS.pop(str(payment_id), None)

        return result

    # --- Step 1: payment initiation -------------------------------------------
    @functools.wraps(func)
    async def _initiate_wrapper(*args, **kwargs):
        # Extract session ID from context
        ctx = kwargs.get("ctx", None)
        session_id = extract_session_id(ctx)

        # Check for existing payment state using utility
        payment_id, payment_url, stored_args, should_execute = check_existing_payment(
            session_id, state_store, provider, func.__name__, kwargs
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

        # If payment exists but is still pending, return existing payment info
        if payment_id and payment_url:
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

        # Store payment state using utility
        save_payment_state(
            session_id, state_store, payment_id, payment_url,
            func.__name__, kwargs, 'requested'
        )

        # Also store by payment_id for backward compatibility with two-step flow
        if state_store and session_id and session_id != pid_str:
            state_store.put(pid_str, {
                'session_id': session_id,
                'payment_id': payment_id,
                'payment_url': payment_url,
                'tool_name': func.__name__,
                'tool_args': kwargs,
                'status': 'requested',
                'created_at': time.time()
            })
        elif not state_store:
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