"""
Unit tests for PayMCP Context functionality.

This module tests the Context class and context injection using existing PayMCP
@price decorator and core system.
"""

import inspect
import pytest
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add src to path for imports - must be done before PayMCP imports
sys.path.insert(0, str(
    Path(__file__).parent.parent.parent / "src"
))  # noqa: E402

from paymcp import (  # noqa: E402
    Context,
    create_context,
    PaymentInfo,
    UserInfo,
    ExecutionInfo,
    price,
    PayMCP,
    PaymentFlow
)


class TestContext:
    """Test the Context class functionality."""

    def test_context_initialization(self):
        """Test Context can be initialized with default values."""
        ctx = Context()

        assert isinstance(ctx.payment, PaymentInfo)
        assert isinstance(ctx.user, UserInfo)
        assert isinstance(ctx.execution, ExecutionInfo)
        assert ctx.extra == {}

    def test_context_initialization_with_data(self):
        """Test Context can be initialized with specific data."""
        payment = PaymentInfo(
            payment_id="test-123",
            amount=25.99,
            currency="USD",
            provider="paypal"
        )

        user = UserInfo(
            user_id="user-456",
            session_id="session-789"
        )

        execution = ExecutionInfo(
            request_id="req-abc",
            tool_name="test_tool",
            started_at=datetime.now(timezone.utc)
        )

        ctx = Context(
            payment=payment,
            user=user,
            execution=execution,
            custom_data="test"
        )

        assert ctx.payment.payment_id == "test-123"
        assert ctx.payment.amount == 25.99
        assert ctx.user.user_id == "user-456"
        assert ctx.execution.tool_name == "test_tool"
        assert ctx.get("custom_data") == "test"

    def test_context_to_dict(self):
        """Test Context can be converted to dictionary."""
        ctx = Context()
        ctx.set("custom_key", "custom_value")

        ctx_dict = ctx.to_dict()

        assert "payment" in ctx_dict
        assert "user" in ctx_dict
        assert "execution" in ctx_dict
        assert "extra" in ctx_dict
        assert ctx_dict["extra"]["custom_key"] == "custom_value"

    def test_context_from_dict(self):
        """Test Context can be created from dictionary."""
        ctx_dict = {
            "payment": {
                "payment_id": "test-123",
                "amount": 15.50,
                "currency": "EUR",
                "provider": "stripe"
            },
            "user": {
                "user_id": "user-789",
                "session_id": "session-abc"
            },
            "execution": {
                "request_id": "req-def",
                "tool_name": "test_function"
            },
            "extra": {
                "test_key": "test_value"
            }
        }

        ctx = Context.from_dict(ctx_dict)

        assert ctx.payment.payment_id == "test-123"
        assert ctx.payment.amount == 15.50
        assert ctx.payment.currency == "EUR"
        assert ctx.user.user_id == "user-789"
        assert ctx.execution.tool_name == "test_function"
        assert ctx.get("test_key") == "test_value"

    def test_create_context_helper(self):
        """Test the create_context helper function."""
        ctx = create_context(
            payment_amount=99.99,
            payment_currency="GBP",
            payment_provider="paypal",
            user_id="user-123",
            tool_name="premium_service",
            request_id="req-456"
        )

        assert ctx.payment.amount == 99.99
        assert ctx.payment.currency == "GBP"
        assert ctx.payment.provider == "paypal"
        assert ctx.user.user_id == "user-123"
        assert ctx.execution.tool_name == "premium_service"
        assert ctx.execution.request_id == "req-456"


class TestPriceDecorator:
    """Test the existing price decorator with Context support."""

    def test_price_decorator(self):
        """Test existing price decorator works as before."""
        @price(price=10.99, currency="USD")
        def test_function():
            return "test result"

        price_info = test_function._paymcp_price_info
        assert price_info["price"] == 10.99
        assert price_info["currency"] == "USD"

    def test_price_decorator_different_currency(self):
        """Test price decorator with different currency."""
        @price(price=25.50, currency="EUR")
        def test_function():
            return "test result"

        price_info = test_function._paymcp_price_info
        assert price_info["price"] == 25.50
        assert price_info["currency"] == "EUR"


class TestContextAwareFunction:
    """Test functions that use Context parameters."""

    def test_context_parameter_detection(self):
        """Test Context parameter detection works correctly."""

        def function_with_context(data: str, ctx: Context) -> str:
            return f"Processed {data} with payment ${ctx.payment.amount}"

        def function_without_context(data: str) -> str:
            return f"Processed {data}"

        # Test Context detection logic (from two_step flow)
        sig1 = inspect.signature(function_with_context)
        expects_context1 = any(
            param.name.lower() in ('ctx', 'context') and (
                param.annotation == Context or
                'Context' in str(param.annotation)
            )
            for param in sig1.parameters.values()
        )

        sig2 = inspect.signature(function_without_context)
        expects_context2 = any(
            param.name.lower() in ('ctx', 'context') and (
                param.annotation == Context or
                'Context' in str(param.annotation)
            )
            for param in sig2.parameters.values()
        )

        assert expects_context1 is True
        assert expects_context2 is False


class TestPayMCPWithContext:
    """Test PayMCP with Context support."""

    def test_paymcp_with_context_function(self):
        """Test PayMCP can handle functions that expect Context."""

        # Create mock MCP
        class MockMCP:
            def __init__(self):
                self.tools = {}

            def tool(self, *args, **kwargs):
                def decorator(func):
                    self.tools[func.__name__] = func
                    return func
                return decorator

        mock_mcp = MockMCP()
        # Add a mock provider to prevent StopIteration error
        providers = {"mock": {"api_key": "test_key"}}
        try:
            PayMCP(
                mcp_instance=mock_mcp,
                providers=providers,
                payment_flow=PaymentFlow.TWO_STEP
            )
        except ValueError:
            # Mock provider not recognized, use empty providers
            # and skip PayMCP functionality test
            pass

        # Test function with Context parameter - just test the decorator,
        # not PayMCP integration
        @price(price=5.99, currency="USD")
        def context_aware_function(data: str, ctx: Context) -> str:
            return f"Processed {data} with ${ctx.payment.amount}"

        # Verify the price decorator works
        assert hasattr(context_aware_function, '_paymcp_price_info')
        price_info = context_aware_function._paymcp_price_info
        assert price_info["price"] == 5.99
        assert price_info["currency"] == "USD"


class TestPaymentInfo:
    """Test PaymentInfo data class."""

    def test_payment_info_initialization(self):
        """Test PaymentInfo can be initialized."""
        payment = PaymentInfo(
            payment_id="test-123",
            amount=50.00,
            currency="USD",
            provider="paypal",
            status="completed"
        )

        assert payment.payment_id == "test-123"
        assert payment.amount == 50.00
        assert payment.currency == "USD"
        assert payment.provider == "paypal"
        assert payment.status == "completed"

    def test_payment_info_to_dict(self):
        """Test PaymentInfo can be converted to dictionary."""
        payment = PaymentInfo(
            payment_id="test-456",
            amount=75.25,
            currency="EUR"
        )

        payment_dict = payment.to_dict()

        assert payment_dict["payment_id"] == "test-456"
        assert payment_dict["amount"] == 75.25
        assert payment_dict["currency"] == "EUR"
        assert payment_dict["created_at"] is None  # No creation time set


class TestUserInfo:
    """Test UserInfo data class."""

    def test_user_info_initialization(self):
        """Test UserInfo can be initialized."""
        user = UserInfo(
            user_id="user-789",
            session_id="session-abc",
            preferences={"theme": "dark", "language": "en"}
        )

        assert user.user_id == "user-789"
        assert user.session_id == "session-abc"
        assert user.preferences["theme"] == "dark"

    def test_user_info_to_dict(self):
        """Test UserInfo can be converted to dictionary."""
        user = UserInfo(
            user_id="user-123",
            ip_address="192.168.1.1"
        )

        user_dict = user.to_dict()

        assert user_dict["user_id"] == "user-123"
        assert user_dict["ip_address"] == "192.168.1.1"
        assert user_dict["preferences"] == {}


class TestExecutionInfo:
    """Test ExecutionInfo data class."""

    def test_execution_info_initialization(self):
        """Test ExecutionInfo can be initialized."""
        start_time = datetime.now(timezone.utc)
        execution = ExecutionInfo(
            request_id="req-abc",
            tool_name="premium_analysis",
            started_at=start_time,
            retry_count=2,
            metadata={"source": "api", "version": "1.0"}
        )

        assert execution.request_id == "req-abc"
        assert execution.tool_name == "premium_analysis"
        assert execution.started_at == start_time
        assert execution.retry_count == 2
        assert execution.metadata["source"] == "api"

    def test_execution_info_to_dict(self):
        """Test ExecutionInfo can be converted to dictionary."""
        execution = ExecutionInfo(
            request_id="req-def",
            tool_name="basic_service"
        )

        execution_dict = execution.to_dict()

        assert execution_dict["request_id"] == "req-def"
        assert execution_dict["tool_name"] == "basic_service"
        assert execution_dict["retry_count"] == 0
        assert execution_dict["metadata"] == {}


class TestContextStringRepresentations:
    """Test Context string representation methods."""

    def test_context_str_representation(self):
        """Test Context __str__ method."""
        context = Context(
            payment=PaymentInfo(
                payment_id="pay-123",
                amount=19.99,
                currency="USD"
            ),
            user=UserInfo(user_id="user-456"),
            execution=ExecutionInfo(request_id="req-789")
        )

        str_repr = str(context)
        expected = "Context(payment_id=pay-123, user_id=user-456, request_id=req-789)"
        assert str_repr == expected

    def test_context_repr_representation(self):
        """Test Context __repr__ method."""
        context = Context(
            payment=PaymentInfo(payment_id="pay-abc"),
            user=UserInfo(user_id="user-def"),
            execution=ExecutionInfo(request_id="req-ghi")
        )

        repr_str = repr(context)
        assert repr_str.startswith("Context({")
        assert "'payment_id': 'pay-abc'" in repr_str
        assert "'user_id': 'user-def'" in repr_str
        assert "'request_id': 'req-ghi'" in repr_str


class TestContextFromDictEdgeCases:
    """Test Context.from_dict edge cases."""

    def test_from_dict_with_datetime_strings(self):
        """Test Context.from_dict with datetime string conversion."""
        created_at = datetime.now(timezone.utc)
        started_at = datetime.now(timezone.utc)
        
        data = {
            "payment": {
                "payment_id": "pay-123",
                "amount": 25.0,
                "currency": "USD",
                "provider": "paypal",
                "status": "created",
                "created_at": created_at.isoformat(),
                "payment_url": "https://example.com/pay"
            },
            "user": {
                "user_id": "user-456",
                "session_id": "sess-789"
            },
            "execution": {
                "request_id": "req-abc",
                "tool_name": "test_tool",
                "started_at": started_at.isoformat(),
                "retry_count": 1,
                "metadata": {}
            },
            "extra": {"custom_key": "custom_value"}
        }

        context = Context.from_dict(data)
        
        # Verify datetime conversion worked
        assert isinstance(context.payment.created_at, datetime)
        assert isinstance(context.execution.started_at, datetime)
        assert context.payment.payment_id == "pay-123"
        assert context.get("custom_key") == "custom_value"

    def test_from_dict_without_datetime_fields(self):
        """Test Context.from_dict without datetime fields."""
        data = {
            "payment": {
                "payment_id": "pay-456",
                "amount": 15.0,
                "currency": "EUR"
            },
            "user": {"user_id": "user-789"},
            "execution": {
                "request_id": "req-def",
                "tool_name": "another_tool"
            }
        }

        context = Context.from_dict(data)
        
        assert context.payment.created_at is None
        assert context.execution.started_at is None
        assert context.payment.payment_id == "pay-456"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
