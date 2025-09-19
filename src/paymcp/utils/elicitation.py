"""Elicitation utility for payment confirmation flow.

This module is separated from the flow implementations for several reasons:
1. Reusability: The elicitation loop logic can be used by multiple payment flows
2. Separation of Concerns: Keeps flow logic focused on orchestration while
   this handles the complex MCP elicitation protocol details
3. Testability: Easier to unit test elicitation logic in isolation
4. Future extensibility: Can be enhanced to support different elicitation strategies
"""

import inspect
from .responseSchema import SimpleActionSchema
from types import SimpleNamespace
from .constants import PaymentStatus
import logging

logger = logging.getLogger(__name__)

async def run_elicitation_loop(
    ctx,
    func,  # Keep for backward compatibility, but can be removed in future
    message: str,
    provider,
    payment_id: str,
    max_attempts: int = 5
) -> str:
    """
    Run the elicitation loop to get user confirmation for payment.

    This function handles the interactive payment confirmation process by:
    1. Prompting the user to complete payment
    2. Checking payment status with the provider
    3. Handling user actions (accept/cancel/decline)
    4. Retrying until payment is confirmed or max attempts reached

    Why this is in utils rather than in the flow:
    - Reusability: Can be used by any flow that needs elicitation
    - Protocol handling: Encapsulates the complex MCP elicitation protocol
    - Error recovery: Centralizes elicitation error handling logic
    - Version compatibility: Handles different MCP client implementations

    Args:
        ctx: MCP context with elicitation support (must have ctx.elicit method)
        func: The original tool function (kept for backward compatibility, unused)
        message: Payment prompt message to show to user
        provider: Payment provider instance with get_payment_status method
        payment_id: Unique payment identifier from provider
        max_attempts: Maximum number of elicitation attempts (default: 5)

    Returns:
        Payment status string: 'paid', 'canceled', or 'pending'

    Raises:
        RuntimeError: If payment is canceled by user or elicitation fails
    """
    for attempt in range(max_attempts):
        # Step 1: Send elicitation prompt to user
        # This shows the payment message and waits for user action
        try:
            # Handle different MCP client implementations
            # Some use 'response_type' parameter, others use 'schema'
            if "response_type" in inspect.signature(ctx.elicit).parameters:
                # Newer MCP clients (e.g., FastMCP Python)
                logger.debug(f"[run_elicitation_loop] Attempt {attempt+1}, using response_type=None")
                elicitation = await ctx.elicit(
                    message=message,
                    response_type=None  # None means simple accept/decline UI
                )
            else:
                # Older MCP clients
                logger.debug(f"[run_elicitation_loop] Attempt {attempt+1}, using schema")
                elicitation = await ctx.elicit(
                    message=message,
                    schema=SimpleActionSchema  # Schema for structured response
                )
        except Exception as e:
            # Step 2: Handle elicitation errors
            # Some clients throw exceptions for certain actions instead of returning them
            logger.warning(f"[run_elicitation_loop] Elicitation failed: {e}")
            msg = str(e).lower()

            # Parse action from error message (workaround for client bugs)
            if "unexpected elicitation action" in msg:
                if "accept" in msg:
                    # User clicked accept but client threw error
                    logger.debug("[run_elicitation_loop] Treating 'accept' action as confirmation")
                    elicitation = SimpleNamespace(action="accept")
                elif any(x in msg for x in ("cancel", "decline")):
                    # User clicked cancel/decline but client threw error
                    logger.debug("[run_elicitation_loop] Treating 'cancel/decline' action as user cancellation")
                    elicitation = SimpleNamespace(action="cancel")
                else:
                    # Unknown action in error message
                    raise RuntimeError("Elicitation failed during confirmation loop.") from e
            else:
                # Non-recoverable elicitation error
                raise RuntimeError("Elicitation failed during confirmation loop.") from e

        # Step 3: Process user's elicitation response
        logger.debug(f"[run_elicitation_loop] Elicitation response: {elicitation}")

        # Check if user explicitly canceled
        if elicitation.action == "cancel" or elicitation.action == "decline":
            logger.debug("[run_elicitation_loop] User canceled payment")
            raise RuntimeError("Payment canceled by user")

        # Step 4: Check payment status with provider
        # Even if user clicked 'accept', we verify with the payment provider
        status = provider.get_payment_status(payment_id)
        logger.debug(f"[run_elicitation_loop]: payment status = {status}")

        # Return if payment is in a terminal state
        if status == PaymentStatus.PAID or status == PaymentStatus.CANCELED:
            return status

        # Payment still pending, continue loop for another attempt
        # This allows user time to complete payment in another window

    # Exhausted all attempts without payment completion
    logger.info(f"[run_elicitation_loop] Payment still pending after {max_attempts} attempts")
    return PaymentStatus.PENDING