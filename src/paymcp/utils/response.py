"""
Response builder utilities for consistent MCP responses across payment flows.

This module standardizes how payment flows return data to MCP clients by providing
a unified interface for building response objects. It ensures all payment flows
return consistent, properly structured responses that work with different MCP clients.

Key Features:
1. Response standardization: Consistent structure across all payment flows
2. Type safety: Proper typing for response fields and status values
3. Client compatibility: Responses work with various MCP client implementations
4. Two-step flow support: Special handling for multi-step payment workflows
5. Error handling: Standardized error response formats

Why this exists:
- Different payment flows (elicitation, progress, sync) need consistent responses
- MCP clients expect predictable response structures for proper display
- Tool results need to be wrapped appropriately for client consumption
- Payment metadata (IDs, URLs, amounts) must be included consistently
"""

from typing import Any, Dict, List, Optional
from .constants import PaymentStatus, ResponseType


def build_response(
    message: str,
    status: str = ResponseType.SUCCESS,
    payment_id: Optional[str] = None,
    payment_url: Optional[str] = None,
    next_step: Optional[str] = None,
    reason: Optional[str] = None,
    raw_result: Any = None,
    amount: Optional[float] = None,
    currency: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build a standardized MCP response with consistent structure and fields.

    This is the core response builder used by all payment flows to ensure
    consistent output format. It handles optional fields gracefully and
    provides special formatting for two-step flows.

    Response Structure:
    - Always includes: message, status
    - Payment fields: payment_id, payment_url (when applicable)
    - Flow control: next_step (for two-step flows)
    - Error handling: reason (for error responses)
    - Tool results: raw (original tool output)
    - Metadata: amount, currency (for payment context)

    Args:
        message: Human-readable message describing the response.
                Example: "Payment completed successfully"
        status: Response status from ResponseType constants.
               Values: SUCCESS, PENDING, ERROR, CANCELED
        payment_id: Unique payment identifier from provider.
                   Format depends on provider (e.g., "pay_abc123", "txn_xyz")
        payment_url: URL where user completes payment.
                    Only included for pending payments.
        next_step: Name of next tool to call in two-step flows.
                  Example: "confirm_payment_abc123"
        reason: Detailed error reason for failed responses.
               Example: "Payment provider connection timeout"
        raw_result: Original tool execution result.
                   Preserved for clients that need the raw output.
        amount: Payment amount in the specified currency.
               Example: 5.99
        currency: Currency code for the payment amount.
                 Example: "USD", "EUR", "GBP"

    Returns:
        Dictionary with standardized MCP response structure.

        Basic response:
        {
            "message": "Tool completed",
            "status": "success",
            "payment_id": "pay_123"
        }

        Two-step response (includes structured_content):
        {
            "message": "Payment required",
            "status": "pending",
            "payment_id": "pay_123",
            "payment_url": "https://pay.me/123",
            "next_step": "confirm_payment_123",
            "structured_content": {
                "payment_url": "https://pay.me/123",
                "payment_id": "pay_123",
                "next_step": "confirm_payment_123",
                "status": "payment_required",
                "amount": 5.99,
                "currency": "USD"
            },
            "data": { ... } // same as structured_content
        }

    Example:
        >>> build_response(
        ...     message="Payment completed successfully",
        ...     status=ResponseType.SUCCESS,
        ...     payment_id="pay_abc123",
        ...     raw_result={"result": "Generated image"}
        ... )
    """
    # Start with base response structure
    response = {
        "message": message,
        "status": status,
    }

    # Add optional payment-related fields
    # These are included only when relevant to avoid cluttering responses
    if payment_id:
        response["payment_id"] = str(payment_id)  # Ensure string format
    if payment_url:
        response["payment_url"] = payment_url
    if next_step:
        response["next_step"] = next_step
    if reason:
        response["reason"] = reason
    if raw_result is not None:
        response["raw"] = raw_result

    # Special handling for two-step flows
    # These require structured data for client processing
    if next_step and payment_url:
        # Create structured data for programmatic access
        structured_data = {
            "payment_url": payment_url,
            "payment_id": str(payment_id) if payment_id else None,
            "next_step": next_step,
            # Status mapping for client compatibility
            "status": f"payment_{status}" if status != ResponseType.PENDING else "payment_required",
        }

        # Add financial information when available
        if amount is not None:
            structured_data["amount"] = amount
        if currency:
            structured_data["currency"] = currency

        # Include both field names for client compatibility
        # Some clients expect "structured_content", others "data"
        response["structured_content"] = structured_data
        response["data"] = structured_data

    return response


def build_error_response(
    message: str,
    reason: Optional[str] = None,
    payment_id: Optional[str] = None,
    payment_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build a standardized error response for payment failures.

    This convenience function ensures all error responses have consistent
    structure and include relevant context for debugging. It's used when
    payment flows encounter recoverable or unrecoverable errors.

    Common error scenarios:
    - Payment provider connection failures
    - Invalid payment credentials
    - User cancellation
    - Network timeouts
    - Malformed payment requests

    Args:
        message: User-friendly error message.
                Example: "Payment failed due to network error"
        reason: Technical details for debugging.
               Example: "Connection timeout after 30 seconds"
        payment_id: Payment ID if one was created before failure.
                   Useful for debugging and potential recovery.
        payment_url: Payment URL if one was generated.
                    May help with manual completion attempts.

    Returns:
        Error response dictionary with ERROR status.

    Example:
        >>> build_error_response(
        ...     message="Payment provider unavailable",
        ...     reason="HTTP 503 Service Unavailable",
        ...     payment_id="pay_failed_123"
        ... )
        {
            "message": "Payment provider unavailable",
            "status": "error",
            "reason": "HTTP 503 Service Unavailable",
            "payment_id": "pay_failed_123"
        }
    """
    return build_response(
        message=message,
        status=ResponseType.ERROR,
        payment_id=payment_id,
        payment_url=payment_url,
        reason=reason,
    )


def build_pending_response(
    message: str,
    payment_id: str,
    payment_url: str,
    next_step: Optional[str] = None,
    amount: Optional[float] = None,
    currency: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build a standardized pending payment response.

    This response type indicates that a payment has been initiated but not
    yet completed. It provides all necessary information for the user to
    complete the payment and for the client to continue the flow.

    Used by:
    - Two-step flows: Returns payment URL and confirmation tool name
    - Progress flows: Indicates payment is being processed
    - Elicitation flows: Prompts user to complete external payment

    Args:
        message: User instruction for completing payment.
                Example: "Please complete payment at the provided URL"
        payment_id: Unique identifier for tracking this payment.
                   Required for status checking and confirmation.
        payment_url: Where user goes to complete payment.
                    Must be a valid, accessible URL.
        next_step: Tool name for confirming payment (two-step flows).
                  Example: "confirm_payment_abc123"
        amount: Payment amount for user reference.
               Example: 9.99
        currency: Currency code for amount display.
                 Example: "USD"

    Returns:
        Pending response dictionary with PENDING status.

    Example:
        >>> build_pending_response(
        ...     message="Complete payment to continue",
        ...     payment_id="pay_123",
        ...     payment_url="https://checkout.provider.com/pay_123",
        ...     next_step="confirm_payment_123",
        ...     amount=5.00,
        ...     currency="USD"
        ... )
    """
    return build_response(
        message=message,
        status=ResponseType.PENDING,
        payment_id=payment_id,
        payment_url=payment_url,
        next_step=next_step,
        amount=amount,
        currency=currency,
    )


def build_canceled_response(
    message: str = "Payment canceled",
    payment_id: Optional[str] = None,
    payment_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build a standardized cancellation response for user-initiated cancellations.

    This response indicates that a payment was canceled by the user rather
    than failing due to technical issues. It's important to distinguish
    cancellations from failures for proper error handling and user experience.

    Cancellation scenarios:
    - User clicks "Cancel" in elicitation prompt
    - User closes payment window before completing
    - User explicitly declines payment in UI
    - Timeout after user inactivity

    Args:
        message: Cancellation message to display to user.
                Default: "Payment canceled"
                Can be customized: "Payment canceled by user"
        payment_id: Payment ID if one was created before cancellation.
                   Useful for cleanup and audit trails.
        payment_url: Payment URL if one was generated.
                    May be logged for debugging purposes.

    Returns:
        Cancellation response dictionary with CANCELED status.

    Example:
        >>> build_canceled_response(
        ...     message="Payment canceled by user",
        ...     payment_id="pay_canceled_123"
        ... )
        {
            "message": "Payment canceled by user",
            "status": "canceled",
            "payment_id": "pay_canceled_123"
        }
    """
    return build_response(
        message=message,
        status=ResponseType.CANCELED,
        payment_id=payment_id,
        payment_url=payment_url,
    )


def build_success_response(
    tool_result: Any,
    payment_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build a standardized success response after tool execution.

    This function handles the final step of payment flows: wrapping the
    actual tool result in a proper response format. It preserves the
    original tool output while adding payment context.

    Tool Result Handling:
    1. If tool_result is already a dict (structured response):
       - Preserve the existing structure
       - Add payment_id if missing
       - Ensure status field is present
    2. If tool_result is raw data (string, number, etc.):
       - Wrap in standard response structure
       - Include raw data in "raw" field
       - Add success status and payment context

    Args:
        tool_result: The actual result from executing the paid tool.
                    Can be any type: dict, string, number, list, object, etc.
                    Examples:
                    - {"text": "Generated content", "model": "gpt-4"}
                    - "Plain text response"
                    - 42
                    - ["item1", "item2", "item3"]
        payment_id: Payment identifier for tracking.
                   Added to response for audit and reference.

    Returns:
        Success response with tool result and payment context.

    Examples:
        >>> # Tool returns structured data
        >>> tool_output = {"generated_text": "Hello world", "tokens": 2}
        >>> build_success_response(tool_output, "pay_123")
        {
            "generated_text": "Hello world",
            "tokens": 2,
            "payment_id": "pay_123",
            "status": "success"
        }

        >>> # Tool returns simple string
        >>> tool_output = "Generated image saved to file.png"
        >>> build_success_response(tool_output, "pay_456")
        {
            "message": "Tool completed after payment",
            "status": "success",
            "payment_id": "pay_456",
            "raw": "Generated image saved to file.png"
        }
    """
    # Handle structured responses (already formatted)
    if isinstance(tool_result, dict):
        # Tool already returned a structured response
        # Add payment context while preserving existing structure
        enhanced_result = tool_result.copy()  # Don't modify original

        # Add payment tracking information
        if payment_id and "payment_id" not in enhanced_result:
            enhanced_result["payment_id"] = str(payment_id)

        # Ensure status field exists for client processing
        if "status" not in enhanced_result:
            enhanced_result["status"] = ResponseType.SUCCESS

        return enhanced_result

    # Handle raw/unstructured responses
    # Wrap the raw result in our standard response format
    return build_response(
        message="Tool completed after payment",
        status=ResponseType.SUCCESS,
        payment_id=payment_id,
        raw_result=tool_result,
    )


def format_two_step_message(
    message: str,
    payment_url: str,
    payment_id: str,
    confirm_tool_name: str,
) -> Dict[str, Any]:
    """
    Format a message dictionary specifically for two-step payment flows.

    Two-step flows separate payment initiation from tool execution:
    1. First call: Creates payment, returns URL and confirmation tool name
    2. Second call: User calls confirmation tool to execute after payment

    This function creates the standardized message format that clients
    expect for two-step flows. It provides all information needed for
    the client to guide the user through the process.

    Args:
        message: Payment instruction message for the user.
                Example: "Please complete payment and then call confirm_payment_123"
        payment_url: URL where user completes the payment.
                    Must be accessible and lead to a working payment form.
        payment_id: Unique payment identifier for tracking.
                   Used to correlate payment completion with tool execution.
        confirm_tool_name: Name of the tool to call after payment.
                          Example: "confirm_payment_abc123"

    Returns:
        Dictionary with two-step flow message structure.

    Example:
        >>> format_two_step_message(
        ...     message="Complete payment then call confirmation tool",
        ...     payment_url="https://pay.example.com/checkout/123",
        ...     payment_id="pay_123",
        ...     confirm_tool_name="confirm_payment_123"
        ... )
        {
            "message": "Complete payment then call confirmation tool",
            "payment_url": "https://pay.example.com/checkout/123",
            "payment_id": "pay_123",
            "next_step": "confirm_payment_123"
        }
    """
    return {
        "message": message,
        "payment_url": payment_url,
        "payment_id": str(payment_id),  # Ensure string format
        "next_step": confirm_tool_name,
    }