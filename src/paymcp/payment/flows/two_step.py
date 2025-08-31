# paymcp/payment/flows/two_step.py
import functools
import inspect
import uuid
from typing import Dict, Any
from ...utils.messages import payment_prompt_message
from ...context import Context, create_context
import logging
logger = logging.getLogger(__name__)
PENDING_ARGS: Dict[str, Dict[str, Any]] = {}  # TODO redis?


def make_paid_wrapper(func, mcp, provider, price_info):
    """
    Implements the two‑step payment flow with Context support:
    1. The original tool is wrapped by an *initiate* step that returns
       `payment_url` and `payment_id` to the client.
    2. A dynamically registered tool `confirm_<tool>` waits for payment,
       validates it, and only then calls the original function with Context.
    """
    confirm_tool_name = f"confirm_{func.__name__}_payment"
    # Check if function expects a Context parameter
    sig = inspect.signature(func)
    expects_context = any(
        param.name.lower() in ('ctx', 'context') and
        (param.annotation == Context or 'Context' in str(param.annotation))
        for param in sig.parameters.values()
    )
    # --- Step 2: payment confirmation ------------------------------------

    @mcp.tool(
        name=confirm_tool_name,
        description=f"Confirm payment and execute {func.__name__}()"
    )
    async def _confirm_tool(payment_id: str):
        logger.info(f"[confirm_tool] Received payment_id={payment_id}")
        payment_data = PENDING_ARGS.pop(str(payment_id), None)
        logger.debug(
            f"[confirm_tool] PENDING_ARGS keys: {list(PENDING_ARGS.keys())}"
        )
        logger.debug(f"[confirm_tool] Retrieved payment_data: {payment_data}")
        if payment_data is None:
            raise RuntimeError("Unknown or expired payment_id")
        original_args = payment_data.get("args", {})
        context_data = payment_data.get("context", {})
        status = provider.get_payment_status(payment_id)
        if status != "paid":
            raise RuntimeError(
                f"Payment status is {status}, expected 'paid'"
            )
        logger.debug(
            f"[confirm_tool] Calling {func.__name__} with args: "
            f"{original_args}"
        )
        # Inject Context if the function expects it
        if expects_context:
            # Update context with confirmed payment info
            context_data["payment"]["payment_id"] = payment_id
            context_data["payment"]["status"] = status
            context = Context.from_dict(context_data)
            # Find the context parameter name
            context_param = next(
                param.name for param in sig.parameters.values()
                if param.name.lower() in ('ctx', 'context')
            )
            original_args[context_param] = context
            logger.debug(
                f"[confirm_tool] Injected context into parameter "
                f"'{context_param}'"
            )
        # Call the original tool with its initial arguments
        # (and context if needed)
        return await func(**original_args)
    # --- Step 1: payment initiation -------------------------------------

    @functools.wraps(func)
    async def _initiate_wrapper(*args, **kwargs):
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        # Create context data for this payment flow
        context_data = create_context(
            payment_amount=price_info["price"],
            payment_currency=price_info["currency"],
            payment_provider=(
                provider.__class__.__name__.lower().replace("provider", "")
            ),
            tool_name=func.__name__,
            request_id=request_id
        ).to_dict()
        payment_id, payment_url = provider.create_payment(
            amount=price_info["price"],
            currency=price_info["currency"],
            description=f"{func.__name__}() execution fee"
        )
        message = payment_prompt_message(
            payment_url, price_info["price"], price_info["currency"]
        )
        pid_str = str(payment_id)
        # Store both args and context data
        PENDING_ARGS[pid_str] = {
            "args": kwargs,
            "context": context_data
        }
        # Return data for the user / LLM
        return {
            "message": message,
            "payment_url": payment_url,
            "payment_id": pid_str,
            "next_step": confirm_tool_name,
        }
    return _initiate_wrapper
