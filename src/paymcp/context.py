"""
PayMCP Context Module
Provides context objects that are passed to MCP tools to access payment
information,
user details, and execution metadata.
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime, timezone


@dataclass
class PaymentInfo:
    """Information about a payment transaction."""
    payment_id: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    provider: Optional[str] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    payment_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "payment_id": self.payment_id,
            "amount": self.amount,
            "currency": self.currency,
            "provider": self.provider,
            "status": self.status,
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
            "payment_url": self.payment_url
        }


@dataclass
class UserInfo:
    """Information about the user making the request."""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "preferences": self.preferences or {}
        }


@dataclass
class ExecutionInfo:
    """Information about the current execution context."""
    request_id: Optional[str] = None
    tool_name: Optional[str] = None
    started_at: Optional[datetime] = None
    retry_count: int = 0
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "request_id": self.request_id,
            "tool_name": self.tool_name,
            "started_at": (
                self.started_at.isoformat() if self.started_at else None
            ),
            "retry_count": self.retry_count,
            "metadata": self.metadata or {}
        }


class Context:
    """
    Context object passed to PayMCP tools containing payment, user, and
    execution information.
    This context allows tools to access information about:
    - Payment details (amount, currency, provider)
    - User information (session, preferences)
    - Execution context (request ID, timing)
    Example:
        @mcp.tool()
        @price(amount=5.99, currency="USD")
        def premium_service(data: str, ctx: Context) -> str:
            # Access payment information
            payment_amount = ctx.payment.amount
            payment_currency = ctx.payment.currency
            # Access user information
            user_id = ctx.user.user_id
            # Access execution information
            request_id = ctx.execution.request_id
            return (
                f"Processing {data} for ${payment_amount} {payment_currency}"
            )
    """

    def __init__(
        self,
        payment: Optional[PaymentInfo] = None,
        user: Optional[UserInfo] = None,
        execution: Optional[ExecutionInfo] = None,
        **kwargs
    ):
        self.payment = payment or PaymentInfo()
        self.user = user or UserInfo()
        self.execution = execution or ExecutionInfo()
        # Store any additional context data
        self.extra = kwargs

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the extra context data."""
        return self.extra.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a value in the extra context data."""
        self.extra[key] = value

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary representation."""
        return {
            "payment": self.payment.to_dict(),
            "user": self.user.to_dict(),
            "execution": self.execution.to_dict(),
            "extra": self.extra
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Context":
        """Create Context from dictionary representation."""
        payment_data = data.get("payment", {})
        user_data = data.get("user", {})
        execution_data = data.get("execution", {})
        extra_data = data.get("extra", {})
        # Convert datetime strings back to datetime objects
        if payment_data.get("created_at"):
            payment_data["created_at"] = datetime.fromisoformat(
                payment_data["created_at"]
            )
        if execution_data.get("started_at"):
            execution_data["started_at"] = datetime.fromisoformat(
                execution_data["started_at"]
            )
        return cls(
            payment=PaymentInfo(**payment_data),
            user=UserInfo(**user_data),
            execution=ExecutionInfo(**execution_data),
            **extra_data
        )

    def __str__(self) -> str:
        """String representation of context."""
        payment_id = self.payment.payment_id
        user_id = self.user.user_id
        request_id = self.execution.request_id
        return (
            f"Context(payment_id={payment_id}, user_id={user_id}, "
            f"request_id={request_id})"
        )

    def __repr__(self) -> str:
        """Detailed representation of context."""
        return f"Context({self.to_dict()})"


def create_context(
    payment_amount: Optional[float] = None,
    payment_currency: Optional[str] = None,
    payment_provider: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    tool_name: Optional[str] = None,
    request_id: Optional[str] = None,
    **kwargs
) -> Context:
    """
    Convenience function to create a Context object.
    Args:
        payment_amount: Payment amount
        payment_currency: Payment currency
        payment_provider: Payment provider name
        user_id: User identifier
        session_id: Session identifier
        tool_name: Name of the tool being executed
        request_id: Request identifier
        **kwargs: Additional context data
    Returns:
        Context object with the provided information
    """
    payment = PaymentInfo(
        amount=payment_amount,
        currency=payment_currency,
        provider=payment_provider,
        created_at=datetime.now(timezone.utc) if payment_amount else None
    )
    user = UserInfo(
        user_id=user_id,
        session_id=session_id
    )
    execution = ExecutionInfo(
        tool_name=tool_name,
        request_id=request_id,
        started_at=datetime.now(timezone.utc)
    )
    return Context(
        payment=payment,
        user=user,
        execution=execution,
        **kwargs
    )
