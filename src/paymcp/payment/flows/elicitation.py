import functools
import logging
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ...state_store import StateStoreProvider
from ...utils.messages import open_link_message, opened_webview_message
from ..webview import open_payment_webview_if_available
from ...utils.elicitation import run_elicitation_loop
from ...utils.context import extract_session_id, log_context_info
from ...utils.state import (
    check_existing_payment,
    save_payment_state,
    update_payment_status,
    cleanup_payment_state
)
from ...utils.constants import PaymentStatus, ResponseType
from ...utils.flow import (
    call_original_tool,
    log_flow,
    extract_tool_description
)
from ...utils.response import (
    build_canceled_response,
    build_pending_response,
    build_success_response
)

logger = logging.getLogger(__name__)


def make_paid_wrapper(func, mcp, provider, price_info, state_store: Optional['StateStoreProvider'] = None):
    """
    Single-step payment flow using elicitation for inline payment confirmation.

    Flow Overview:
    1. Tool invocation triggers payment creation
    2. Client is prompted via elicitation to confirm payment
    3. Tool polls provider for payment status
    4. On success: executes original tool and returns result
    5. On cancel: returns canceled response
    6. On timeout: returns pending status for retry

    Key Features:
    - Inline payment flow: No separate confirmation tool needed
    - Interactive: Uses MCP elicitation for real-time user feedback
    - Timeout resilient: State persists for recovery
    - Session-based: Tracks payments per session for idempotency

    Advantages:
    - Better UX: Single tool call from user perspective
    - Simpler client integration: No need to handle confirm tools
    - Real-time feedback: Client shows payment progress

    Limitations:
    - Requires elicitation support in MCP client
    - Holds connection open during payment (max timeout applies)

    Args:
        func: Original tool function to wrap
        mcp: MCP server instance (unused but kept for API consistency)
        provider: Payment provider for creating/checking payments
        price_info: Pricing configuration (price, currency)
        state_store: Optional persistent storage for timeout recovery
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        """Wrapper that adds elicitation-based payment flow to the original tool."""

        # Extract context for elicitation support
        ctx = kwargs.get("ctx", None)

        log_flow(logger, 'Elicitation', 'debug',
                f"Starting tool: {func.__name__}")

        # Log context details to debug client integration
        log_context_info(ctx)

        # Extract session ID for state management and recovery
        # Session ID enables payment reuse after timeouts
        session_id = extract_session_id(ctx)

        # Check for existing payment to ensure idempotency
        # This handles:
        # 1. Recovery after client timeout/disconnection
        # 2. Duplicate requests from impatient users
        # 3. Already completed payments that can execute immediately
        payment_id, payment_url, stored_args, should_execute = check_existing_payment(
            session_id, state_store, provider, func.__name__, kwargs
        )

        # Optimization: Skip payment flow if already paid
        # This happens when client reconnects after payment completion
        if should_execute:
            log_flow(logger, 'Elicitation', 'info',
                    "Payment already completed, executing tool")
            if stored_args:
                # Use originally stored arguments (preserves exact request)
                merged_kwargs = {**kwargs}
                merged_kwargs.update(stored_args)
                return await call_original_tool(func, args, merged_kwargs)
            else:
                # Execute with current arguments (no stored state)
                return await call_original_tool(func, args, kwargs)

        # Create new payment if not reusing existing one
        if not payment_id:
            # Initiate new payment session with provider
            payment_id, payment_url = provider.create_payment(
                amount=price_info["price"],
                currency=price_info["currency"],
                description=extract_tool_description(func.__name__, 'elicitation')
            )
            log_flow(logger, 'Elicitation', 'debug',
                    f"Created payment with ID: {payment_id}")

            # Persist payment state for recovery after timeouts
            # Uses session_id as primary key for efficient lookup
            save_payment_state(
                session_id, state_store, payment_id, payment_url,
                func.__name__, kwargs, PaymentStatus.REQUESTED
            )

        # Generate user-friendly payment message
        # Attempts to open webview for better UX if available
        if open_payment_webview_if_available(payment_url):
            message = opened_webview_message(
                payment_url, price_info["price"], price_info["currency"]
            )
        else:
            # Fallback to standard link message
            message = open_link_message(
                payment_url, price_info["price"], price_info["currency"]
            )

        # Interactive payment confirmation via elicitation
        # This sends prompts to the client and polls for payment status
        log_flow(logger, 'Elicitation', 'debug',
                f"Calling elicitation with context {ctx}")

        try:
            # Run elicitation loop:
            # 1. Prompts user to complete payment
            # 2. Polls provider for payment status
            # 3. Returns final status (paid/canceled/timeout)
            payment_status = await run_elicitation_loop(
                ctx, func, message, provider, payment_id
            )
        except Exception as e:
            # Handle elicitation failures (timeout, client disconnect, etc.)
            log_flow(logger, 'Elicitation', 'warning',
                    f"Payment confirmation failed: {e}")
            # IMPORTANT: Don't delete state on timeout
            # Payment might still complete asynchronously
            update_payment_status(session_id, state_store, PaymentStatus.TIMEOUT)
            raise

        # Process payment result and take appropriate action
        if payment_status == PaymentStatus.PAID:
            # Payment successful - execute the tool
            log_flow(logger, 'Elicitation', 'info',
                    f"Payment confirmed, calling {func.__name__}")

            # Update state to reflect successful payment
            update_payment_status(session_id, state_store, PaymentStatus.PAID)

            # Execute the original tool function
            # This is the actual work the user paid for
            result = await call_original_tool(func, args, kwargs)

            # Clean up state after successful execution
            # Removes payment data to prevent memory leaks
            cleanup_payment_state(session_id, state_store)

            return build_success_response(result, payment_id)

        elif payment_status == PaymentStatus.CANCELED:
            # User explicitly canceled the payment
            log_flow(logger, 'Elicitation', 'info', "Payment canceled")

            # Clean up state since payment won't complete
            cleanup_payment_state(session_id, state_store)

            # Return structured canceled response
            # Client can retry by calling the tool again
            return build_canceled_response(
                "Payment canceled by user",
                payment_id,
                payment_url
            )

        else:
            # Payment still pending after elicitation attempts
            # This can happen if:
            # 1. User is still completing payment
            # 2. Provider processing is delayed
            # 3. Network issues preventing status updates
            log_flow(logger, 'Elicitation', 'info',
                    "Payment not received after retries")

            # Keep state for future recovery
            # User can retry by calling the tool again
            update_payment_status(session_id, state_store, PaymentStatus.PENDING)

            # Return pending status with retry instructions
            # next_step points back to this same tool for retry
            return build_pending_response(
                "We haven't received the payment yet. Click the button below to check again.",
                payment_id,
                payment_url,
                next_step=func.__name__  # Retry calls same tool
            )

    return wrapper