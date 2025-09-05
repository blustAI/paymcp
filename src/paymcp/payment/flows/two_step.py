# paymcp/payment/flows/two_step.py
import functools
from typing import Dict, Any
from ...utils.messages import payment_prompt_message
from typing import cast
import logging
logger = logging.getLogger(__name__)

PENDING_ARGS: Dict[str, Dict[str, Any]] = {} #TODO redis?


def make_paid_wrapper(func, mcp, provider, price_info):
    """
    Implements the two‑step payment flow:

    1. The original tool is wrapped by an *initiate* step that returns
       `payment_url` and `payment_id` to the client.
    2. A dynamically registered tool `confirm_<tool>` waits for payment,
       validates it, and only then calls the original function.
    """

    confirm_tool_name = f"confirm_{func.__name__}_payment"

    # --- Step 2: payment confirmation -----------------------------------------
    @mcp.tool(
        name=confirm_tool_name,
        description=f"Confirm payment and execute {func.__name__}()"
    )
    async def _confirm_tool(payment_id: str):
        logger.info(f"[confirm_tool] Received payment_id={payment_id}")
        original_args = PENDING_ARGS.pop(str(payment_id), None)
        logger.debug(f"[confirm_tool] PENDING_ARGS keys: {list(PENDING_ARGS.keys())}")
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
        return await func(**original_args)

    # --- Step 1: payment initiation -------------------------------------------
    @functools.wraps(func)
    async def _initiate_wrapper(*args, **kwargs):
        payment_id, payment_url = provider.create_payment(
            amount=price_info["price"],
            currency=price_info["currency"],
            description=f"{func.__name__}() execution fee"
        )
        message = payment_prompt_message(
            payment_url, price_info["price"], price_info["currency"]
        )

        pid_str = str(payment_id)
        PENDING_ARGS[pid_str] = kwargs

        # Return data for the user / LLM
        return {
            "message": message,
            "payment_url": payment_url,
            "payment_id": pid_str,
            "next_step": confirm_tool_name,
        }

    return _initiate_wrapper