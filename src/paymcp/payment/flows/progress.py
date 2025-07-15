# paymcp/payment/flows/progress.py
import asyncio
import functools
from typing import Any, Dict, Optional
from ...utils.messages import payment_prompt_message

DEFAULT_POLL_SECONDS = 3          # how often to poll provider.get_payment_status
MAX_WAIT_SECONDS = 15 * 60        # give up after 15 min 


def make_paid_wrapper(
    func,
    mcp,
    provider,
    price_info,
):
    """
    One-step flow that *holds the tool open* and reports progress
    via ctx.report_progress() until the payment is completed.
    """

    @functools.wraps(func)
    async def _progress_wrapper(*args, **kwargs):
        payment_id, payment_url = provider.create_payment(
            amount=price_info["price"],
            currency=price_info["currency"],
            description=f"{func.__name__}() execution fee"
        )
        ctx = kwargs.get("ctx", None)
        # Helper to emit progress safely
        async def _notify(message: str, progress: Optional[int] = None):
            if ctx is not None and hasattr(ctx, "report_progress"):
                await ctx.report_progress(
                    message=message,
                    progress=progress or 0,
                    total=100,
                )

        # Initial message with the payment link
        await _notify(
            payment_prompt_message(
                payment_url, price_info["price"], price_info["currency"]
            ),
            progress=0,
        )

        # Poll provider until paid, cancelled, or timeout
        waited = 0
        while waited < MAX_WAIT_SECONDS:
            await asyncio.sleep(DEFAULT_POLL_SECONDS)
            waited += DEFAULT_POLL_SECONDS

            status = provider.get_payment_status(payment_id)

            if status == "paid":
                await _notify("Payment received — generating result …", progress=100)
                break

            if status in ("cancelled", "expired", "failed"):
                raise RuntimeError(f"Payment status is {status}, expected 'paid'")

            # Still pending → ping progress
            await _notify(f"Waiting for payment … ({waited}s elapsed)")

        else:  # loop exhausted
            raise RuntimeError("Payment timeout reached; aborting")

        # Call the underlying tool with its original args/kwargs
        return await func(*args, **kwargs)

    return _progress_wrapper