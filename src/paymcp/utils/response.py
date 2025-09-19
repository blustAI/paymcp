"""
Response builder utilities for consistent MCP responses
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
    Build a standard MCP response

    Args:
        message: Human-readable message
        status: Response status
        payment_id: Payment identifier
        payment_url: Payment URL
        next_step: Next tool to call (for two-step flow)
        reason: Error reason
        raw_result: Raw tool result
        amount: Payment amount
        currency: Payment currency

    Returns:
        Standardized response dictionary
    """
    response = {
        "message": message,
        "status": status,
    }

    # Add payment fields if provided
    if payment_id:
        response["payment_id"] = str(payment_id)
    if payment_url:
        response["payment_url"] = payment_url
    if next_step:
        response["next_step"] = next_step
    if reason:
        response["reason"] = reason
    if raw_result is not None:
        response["raw"] = raw_result

    # Add structured content for two-step flow
    if next_step and payment_url:
        structured_data = {
            "payment_url": payment_url,
            "payment_id": str(payment_id) if payment_id else None,
            "next_step": next_step,
            "status": f"payment_{status}" if status != ResponseType.PENDING else "payment_required",
        }
        if amount is not None:
            structured_data["amount"] = amount
        if currency:
            structured_data["currency"] = currency

        response["structured_content"] = structured_data
        response["data"] = structured_data

    return response


def build_error_response(
    message: str,
    reason: Optional[str] = None,
    payment_id: Optional[str] = None,
    payment_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Build an error response"""
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
    """Build a payment pending response"""
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
    """Build a payment canceled response"""
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
    Build a successful tool execution response

    Args:
        tool_result: Result from the tool execution
        payment_id: Payment identifier

    Returns:
        Success response with tool result
    """
    # If tool result is already a properly formatted response, return it
    if isinstance(tool_result, dict):
        # Add payment info if not present
        if payment_id and "payment_id" not in tool_result:
            tool_result["payment_id"] = str(payment_id)
        if "status" not in tool_result:
            tool_result["status"] = ResponseType.SUCCESS
        return tool_result

    # Otherwise, wrap the result
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
    Format a message for two-step flow

    Args:
        message: Payment prompt message
        payment_url: URL for payment
        payment_id: Payment identifier
        confirm_tool_name: Name of confirmation tool

    Returns:
        Formatted message dictionary
    """
    return {
        "message": message,
        "payment_url": payment_url,
        "payment_id": str(payment_id),
        "next_step": confirm_tool_name,
    }