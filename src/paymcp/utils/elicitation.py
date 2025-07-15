import inspect
from .responseSchema import SimpleActionSchema
import logging
logger = logging.getLogger(__name__)

async def run_elicitation_loop(ctx, func, message, provider, payment_id, max_attempts=5):
    for attempt in range(max_attempts):
        try:
            if "response_type" in inspect.signature(ctx.elicit).parameters:
                elicitation = await ctx.elicit(
                    message=message,
                    response_type=None
                )
            else:
                elicitation = await ctx.elicit(
                    message=message,
                    schema=SimpleActionSchema
                )
        except Exception as e:
            logger.warning(f"[run_elicitation_loop] Elicitation failed: {e}")
            raise RuntimeError("Elicitation failed during confirmation loop.") from e

        logger.debug(f"[run_elicitation_loop] Elicitation response: {elicitation}")

        if elicitation.action == "cancel" or elicitation.action == "decline":
            logger.debug("[run_elicitation_loop] User canceled payment")
            raise RuntimeError("Payment cancelled by user")

        status = provider.get_payment_status(payment_id)
        logger.debug(f"[run_elicitation_loop] Attempt {attempt+1}: payment status = {status}")
        if status == "paid" or status == "canceled":
            return status 
    return "pending"