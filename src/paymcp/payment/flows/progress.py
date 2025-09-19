import asyncio
import functools
import time
import logging
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ...state_store import StateStoreProvider
from ...utils.messages import open_link_message, opened_webview_message
from ..webview import open_payment_webview_if_available
from ...utils.context import extract_session_id, log_context_info
from ...utils.state import (
    check_existing_payment,
    save_payment_state,
    update_payment_status,
    cleanup_payment_state
)
from ...utils.constants import PaymentStatus, ResponseType, Timing
from ...utils.flow import (
    call_original_tool,
    delay,
    is_client_aborted,
    log_flow,
    extract_tool_description
)
from ...utils.response import (
    build_error_response,
    build_canceled_response,
    build_success_response
)

logger = logging.getLogger(__name__)


def make_paid_wrapper(
    func,
    mcp,
    provider,
    price_info,
    state_store: Optional['StateStoreProvider'] = None,
):
    """
    One-step flow that *holds the tool open* and reports progress
    via ctx.report_progress() until the payment is completed.

    Refactored to use shared utilities for DRY principle.
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
            else:
                log_flow(logger, 'Progress', 'debug',
                        f"progress {progress}/100: {message}")

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
                return await call_original_tool(func, {}, merged_kwargs)
            else:
                # Execute with current arguments
                return await call_original_tool(func, args, kwargs)

        # Create new payment if needed
        if not payment_id:
            payment_id, payment_url = provider.create_payment(
                amount=price_info["price"],
                currency=price_info["currency"],
                description=extract_tool_description(func.__name__, 'progress')
            )

            # Store payment state
            save_payment_state(
                session_id, state_store, payment_id, payment_url,
                func.__name__, kwargs, PaymentStatus.REQUESTED
            )
            log_flow(logger, 'Progress', 'debug',
                    f"created payment id={payment_id} url={payment_url}")

        # Generate appropriate message based on webview availability
        if open_payment_webview_if_available(payment_url):
            message = opened_webview_message(
                payment_url, price_info["price"], price_info["currency"]
            )
        else:
            message = open_link_message(
                payment_url, price_info["price"], price_info["currency"]
            )

        # Initial message with the payment link
        await _notify(message, progress=0)

        # Poll provider until paid, canceled, or timeout
        waited = 0
        while waited < Timing.MAX_WAIT_SECONDS:
            # Check for client abort
            if is_client_aborted(ctx):
                log_flow(logger, 'Progress', 'warning',
                        'Client aborted while waiting for payment')
                cleanup_payment_state(session_id, state_store)
                return build_canceled_response(
                    "Payment aborted by client",
                    payment_id,
                    payment_url
                )

            await delay(Timing.DEFAULT_POLL_SECONDS)
            waited += Timing.DEFAULT_POLL_SECONDS

            status = provider.get_payment_status(payment_id)
            log_flow(logger, 'Progress', 'debug',
                    f"poll status={status} waited={waited}s")

            if status == PaymentStatus.PAID:
                await _notify("Payment received — generating result …", progress=100)

                # Update state to paid
                update_payment_status(session_id, state_store, PaymentStatus.PAID)
                break

            if status in (PaymentStatus.CANCELED, PaymentStatus.EXPIRED, PaymentStatus.FAILED):
                # Clean up state on failure
                cleanup_payment_state(session_id, state_store)
                await _notify(f"Payment {status} — aborting", progress=0)
                return build_canceled_response(
                    f"Payment status is {status}",
                    payment_id,
                    payment_url
                )

            # Still pending → ping progress
            pct = min(int((waited / Timing.MAX_WAIT_SECONDS) * 99), 99)
            await _notify(f"Waiting for payment … ({waited}s elapsed)", progress=pct)

        else:  # loop exhausted
            # Don't delete state on timeout - payment might still complete
            update_payment_status(session_id, state_store, PaymentStatus.TIMEOUT)
            log_flow(logger, 'Progress', 'warning',
                    f"Payment timeout for payment_id={payment_id}")
            return build_error_response(
                "Payment timeout reached; aborting",
                reason="timeout",
                payment_id=payment_id,
                payment_url=payment_url
            )

        # Payment succeeded - call the original tool
        log_flow(logger, 'Progress', 'info',
                f"payment confirmed; invoking original tool {func.__name__}")

        result = await call_original_tool(func, args, kwargs)

        # Clean up state after successful execution
        cleanup_payment_state(session_id, state_store)

        return build_success_response(result, payment_id)

    return _progress_wrapper