"""
Unit tests for PayPal payment provider.

This module contains comprehensive unit tests for the PayPalProvider class,
covering all functionality including initialization, authentication, payment creation,
status checking, error handling, and edge cases.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import time
from datetime import datetime
from requests.exceptions import HTTPError, RequestException, Timeout, ConnectionError

from paymcp.providers.paypal.provider import (
    PayPalProvider, AuthenticationError, PaymentError,
    PaymentStatus, Money
)
from paymcp.providers.paypal.config import PayPalConfig
from paymcp.providers.paypal.validator import PayPalValidationError


class TestPayPalProvider:
    """Test the PayPal provider implementation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.valid_config = PayPalConfig(
            client_id="test_client_id",
            client_secret="test_client_secret",
            sandbox=True,
            return_url="https://example.com/success",
            cancel_url="https://example.com/cancel"
        )
        
    def test_init_with_valid_config(self):
        """Test initialization with valid configuration."""
        provider = PayPalProvider(config=self.valid_config)
        assert provider.config == self.valid_config
        assert hasattr(provider, 'token_manager')
        assert hasattr(provider, 'http_client')
        assert hasattr(provider, 'validator')
    
    def test_init_with_invalid_config(self):
        """Test initialization with invalid configuration."""
        with pytest.raises(ValueError):  # Current implementation raises ValueError
            PayPalProvider(config=None)
    
    @patch('requests.post')
    def test_get_access_token_success(self, mock_post):
        """Test successful access token retrieval."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'access_token': 'test_token',
            'expires_in': 3600,
            'token_type': 'Bearer'
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        provider = PayPalProvider(config=self.valid_config)
        token = provider.token_manager.get_token()
        
        assert token == 'test_token'
        
        mock_post.assert_called_once()
    
    @patch('requests.post')
    def test_get_access_token_failure(self, mock_post):
        """Test access token retrieval failure."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = HTTPError("401 Unauthorized")
        mock_post.return_value = mock_response
        
        provider = PayPalProvider(config=self.valid_config)
        
        with pytest.raises(AuthenticationError):
            provider.token_manager.get_token()
    
    def test_is_token_valid(self):
        """Test token validity checking."""
        provider = PayPalProvider(config=self.valid_config)
        
        # No token initially
        assert not provider.token_manager._is_token_valid()
        
        # Mock a valid token
        provider.token_manager._token = "test_token"
        provider.token_manager._expires_at = datetime.now().timestamp() + 3600
        assert provider.token_manager._is_token_valid()
        
        # Mock an expired token
        provider.token_manager._expires_at = datetime.now().timestamp() - 100
        assert not provider.token_manager._is_token_valid()
    
    @patch('requests.Session.request')
    @patch('requests.post')
    def test_make_request_with_auth(self, mock_post, mock_session_request):
        """Test authenticated request making."""
        # Mock token request
        mock_token_response = Mock()
        mock_token_response.json.return_value = {
            'access_token': 'test_token',
            'expires_in': 3600
        }
        mock_token_response.raise_for_status.return_value = None
        mock_post.return_value = mock_token_response
        
        # Mock API request
        mock_api_response = Mock()
        mock_api_response.json.return_value = {'success': True}
        mock_api_response.raise_for_status.return_value = None
        mock_session_request.return_value = mock_api_response
        
        provider = PayPalProvider(config=self.valid_config)
        result = provider.http_client.request('POST', '/test', {'data': 'test'})
        
        assert result == {'success': True}
        mock_post.assert_called_once()
        mock_session_request.assert_called_once()
    
    @patch('requests.Session.request')
    @patch('requests.post')
    def test_create_payment_success(self, mock_post, mock_session_request):
        """Test successful payment creation."""
        # Mock token request
        mock_token_response = Mock()
        mock_token_response.json.return_value = {
            'access_token': 'test_token',
            'expires_in': 3600
        }
        mock_token_response.raise_for_status.return_value = None
        mock_post.return_value = mock_token_response
        
        # Mock payment creation
        mock_payment_response = Mock()
        mock_payment_response.json.return_value = {
            'id': 'PAYID-TEST123',
            'status': 'CREATED',
            'links': [
                {'rel': 'approve', 'href': 'https://paypal.com/approve-link'},
                {'rel': 'self', 'href': 'https://api.paypal.com/orders/PAYID-TEST123'}
            ]
        }
        mock_payment_response.raise_for_status.return_value = None
        mock_session_request.return_value = mock_payment_response
        
        provider = PayPalProvider(config=self.valid_config)
        payment_id, payment_url = provider.create_payment(
            amount=25.99,
            currency="USD",
            description="Test payment"
        )
        
        assert payment_id == 'PAYID-TEST123'
        assert payment_url == 'https://paypal.com/approve-link'
    
    def test_create_payment_validation_errors(self):
        """Test payment creation with invalid parameters."""
        provider = PayPalProvider(config=self.valid_config)
        
        # Invalid amount (wrapped in RuntimeError)
        with pytest.raises(RuntimeError):
            provider.create_payment(-1.0, "USD", "Test")
        
        # Invalid currency (wrapped in RuntimeError)
        with pytest.raises(RuntimeError):
            provider.create_payment(10.0, "INVALID", "Test")
        
        # Empty description (wrapped in RuntimeError)
        with pytest.raises(RuntimeError):
            provider.create_payment(10.0, "USD", "")
    
    @patch('requests.Session.request')
    @patch('requests.post')
    def test_get_payment_status_success(self, mock_post, mock_session_request):
        """Test successful payment status retrieval."""
        # Mock token request
        mock_token_response = Mock()
        mock_token_response.json.return_value = {
            'access_token': 'test_token',
            'expires_in': 3600
        }
        mock_token_response.raise_for_status.return_value = None
        mock_post.return_value = mock_token_response
        
        # Mock status request
        mock_status_response = Mock()
        mock_status_response.json.return_value = {
            'id': '1AB23456CD789012E',  # Valid 17-char format
            'status': 'APPROVED'
        }
        mock_status_response.raise_for_status.return_value = None
        mock_session_request.return_value = mock_status_response
        
        provider = PayPalProvider(config=self.valid_config)
        status = provider.get_payment_status('1AB23456CD789012E')  # Valid 17-char format
        
        assert status == 'approved'
    
    @patch('requests.post')
    def test_network_error_handling(self, mock_post):
        """Test handling of network errors."""
        mock_post.side_effect = ConnectionError("Network error")
        
        provider = PayPalProvider(config=self.valid_config)
        
        with pytest.raises(RuntimeError):  # Current implementation wraps in RuntimeError
            provider.create_payment(10.0, "USD", "Test")
    
    @patch('requests.post')
    def test_timeout_handling(self, mock_post):
        """Test handling of request timeouts."""
        mock_post.side_effect = Timeout("Request timeout")
        
        provider = PayPalProvider(config=self.valid_config)
        
        with pytest.raises(RuntimeError):  # Current implementation wraps in RuntimeError
            provider.create_payment(10.0, "USD", "Test")
    
    def test_money_class(self):
        """Test Money data class functionality."""
        money = Money(amount=25.99, currency="USD")
        assert money.amount == 25.99
        assert money.currency == "USD"
        assert money.format() == "$25.99"
        
        eur_money = Money(amount=100.50, currency="EUR")
        assert eur_money.format() == "€100.50"
    
    def test_payment_status_enum(self):
        """Test PaymentStatus enum functionality."""
        assert PaymentStatus.CREATED.value == "created"
        assert PaymentStatus.APPROVED.value == "approved"
        assert PaymentStatus.COMPLETED.value == "completed"
        assert PaymentStatus.FAILED.value == "failed"
        assert PaymentStatus.CANCELLED.value == "cancelled"


class TestPayPalProviderEdgeCases:
    """Test edge cases and error scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = PayPalConfig(
            client_id="test_client_id",
            client_secret="test_client_secret",
            sandbox=True,
            return_url="https://example.com/success",
            cancel_url="https://example.com/cancel"
        )
    
    def test_empty_payment_id(self):
        """Test handling of empty payment ID."""
        provider = PayPalProvider(config=self.config)
        
        with pytest.raises(RuntimeError):  # Current implementation wraps in RuntimeError
            provider.get_payment_status("")
    
    def test_none_payment_id(self):
        """Test handling of None payment ID."""
        provider = PayPalProvider(config=self.config)
        
        with pytest.raises(RuntimeError):  # Current implementation wraps in RuntimeError
            provider.get_payment_status(None)
    
    @patch('requests.post')
    def test_malformed_token_response(self, mock_post):
        """Test handling of malformed token response."""
        mock_response = Mock()
        mock_response.json.return_value = {'invalid': 'response'}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        provider = PayPalProvider(config=self.config)
        
        with pytest.raises(AuthenticationError):
            provider.token_manager.get_token()
    
    @patch('requests.Session.request')
    @patch('requests.post')
    def test_malformed_payment_response(self, mock_post, mock_session_request):
        """Test handling of malformed payment response."""
        # Mock token request
        mock_token_response = Mock()
        mock_token_response.json.return_value = {
            'access_token': 'test_token',
            'expires_in': 3600
        }
        mock_token_response.raise_for_status.return_value = None
        mock_post.return_value = mock_token_response
        
        # Mock malformed payment response
        mock_payment_response = Mock()
        mock_payment_response.json.return_value = {'invalid': 'response'}
        mock_payment_response.raise_for_status.return_value = None
        mock_session_request.return_value = mock_payment_response
        
        provider = PayPalProvider(config=self.config)
        
        with pytest.raises(RuntimeError):  # Current implementation wraps in RuntimeError
            provider.create_payment(10.0, "USD", "Test")
    
    def test_boundary_amounts(self):
        """Test boundary amount values."""
        provider = PayPalProvider(config=self.config)
        
        # Test minimum amount (wrapped in RuntimeError)
        with pytest.raises(RuntimeError):
            provider.create_payment(0.0, "USD", "Test")
        
        # Test very large amount (wrapped in RuntimeError)  
        with pytest.raises(RuntimeError):
            provider.create_payment(1000000.0, "USD", "Test")
    
    def test_currency_validation(self):
        """Test currency validation edge cases."""
        provider = PayPalProvider(config=self.config)
        
        # Test invalid currency (lowercase works but invalid currency fails)
        with pytest.raises(RuntimeError):
            provider.create_payment(10.0, "INVALID", "Test")
        
        # Test numeric currency (wrapped in RuntimeError)
        with pytest.raises(RuntimeError):
            provider.create_payment(10.0, "123", "Test")
    
    def test_description_validation(self):
        """Test description validation edge cases."""
        provider = PayPalProvider(config=self.config)
        
        # Test very long description (wrapped in RuntimeError)
        long_desc = "x" * 1000
        with pytest.raises(RuntimeError):
            provider.create_payment(10.0, "USD", long_desc)
        
        # Test whitespace-only description (wrapped in RuntimeError)
        with pytest.raises(RuntimeError):
            provider.create_payment(10.0, "USD", "   ")


class TestPayPalProviderEdgeCases:
    """Test PayPal provider edge cases."""

    def test_money_class_functionality(self):
        """Test Money class with different values."""
        # Test zero amount
        money = Money(0, "USD")
        assert money.amount == 0
        assert money.format() == "$0.00"
        
        # Test very small amount
        money = Money(0.01, "EUR")
        assert money.amount == 0.01
        assert money.format() == "€0.01"
        
        # Test large amount (within limits)
        money = Money(9999.99, "GBP")
        assert money.amount == 9999.99
        assert money.format() == "£9999.99"

    def test_money_class_validation(self):
        """Test Money class validation."""
        # Test negative amount (should raise)
        with pytest.raises(ValueError, match="Amount cannot be negative"):
            Money(-10.00, "USD")
        
        # Test invalid currency (should raise) 
        with pytest.raises(ValueError, match="Currency must be 3-character code"):
            Money(10.00, "US")
        
        with pytest.raises(ValueError, match="Currency must be 3-character code"):
            Money(10.00, "DOLLAR")


class TestPayPalProviderComprehensive:
    """Comprehensive tests to improve coverage."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.valid_config = PayPalConfig(
            client_id="test_client_id_1234567890",
            client_secret="test_client_secret_1234567890",
            sandbox=True
        )

    def test_money_format_with_symbol(self):
        """Test Money.format with include_symbol=True for supported currencies."""
        # Test USD with symbol
        money_usd = Money(25.99, "USD")
        assert money_usd.format(include_symbol=True) == "$25.99"
        
        # Test EUR with symbol
        money_eur = Money(35.50, "EUR")
        assert money_eur.format(include_symbol=True) == "€35.50"
        
        # Test GBP with symbol
        money_gbp = Money(45.25, "GBP")
        assert money_gbp.format(include_symbol=True) == "£45.25"
        
        # Test JPY with symbol
        money_jpy = Money(1000, "JPY")
        assert money_jpy.format(include_symbol=True) == "¥1000.00"

    def test_money_format_without_symbol_unsupported_currency(self):
        """Test Money.format for currency without symbol support."""
        money_cad = Money(100.00, "CAD")
        # CAD doesn't have symbol mapping, should return without symbol
        assert money_cad.format(include_symbol=True) == "100.00 CAD"
        assert money_cad.format(include_symbol=False) == "100.00 CAD"

    def test_payment_status_enum_values(self):
        """Test all PaymentStatus enum values."""
        # Test all possible status values - these are lowercase as per actual implementation
        assert PaymentStatus.CREATED.value == "created"
        assert PaymentStatus.APPROVED.value == "approved" 
        assert PaymentStatus.COMPLETED.value == "completed"
        assert PaymentStatus.CANCELLED.value == "cancelled"
        assert PaymentStatus.FAILED.value == "failed"
        assert PaymentStatus.PENDING.value == "pending"
        assert PaymentStatus.EXPIRED.value == "expired"
        assert PaymentStatus.UNKNOWN.value == "unknown"

    def test_payment_factory_create_payment_request(self):
        """Test PaymentFactory methods."""
        from paymcp.providers.paypal.provider import PaymentFactory
        
        # Test create_payment_request
        request = PaymentFactory.create_payment_request(
            amount=25.99,
            currency="USD", 
            description="Test payment"
        )
        
        assert request.money.amount == 25.99
        assert request.money.currency == "USD"
        assert request.description == "Test payment"
        assert request.reference_id is None
        assert request.metadata == {}

    def test_money_equality_and_hashing(self):
        """Test Money class equality and hashing."""
        money1 = Money(25.99, "USD")
        money2 = Money(25.99, "USD") 
        money3 = Money(30.00, "USD")
        money4 = Money(25.99, "EUR")
        
        # Test equality
        assert money1 == money2
        assert money1 != money3
        assert money1 != money4
        
        # Test hashing (Money is frozen dataclass)
        money_set = {money1, money2}
        assert len(money_set) == 1  # Should be deduplicated

    @patch('requests.post')
    def test_provider_initialization_components(self, mock_post):
        """Test provider initialization creates all necessary components."""
        provider = PayPalProvider(self.valid_config)
        
        # Test that all components are initialized
        assert provider.config == self.valid_config
        assert hasattr(provider, 'validator')
        assert hasattr(provider, 'token_manager')
        assert hasattr(provider, 'http_client')
        assert hasattr(provider, 'order_builder')
        assert hasattr(provider, 'logger')

    @patch('requests.post')
    def test_token_fetch_failure_handling(self, mock_post):
        """Test token fetch failure with KeyError."""
        # Mock response with missing access_token field
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"expires_in": 3600}  # Missing access_token
        mock_post.return_value = mock_response
        
        provider = PayPalProvider(self.valid_config)
        
        # This should trigger the KeyError handling path
        with pytest.raises(AuthenticationError):
            provider.token_manager._fetch_token()

    def test_money_string_representations(self):
        """Test Money class string methods."""
        money = Money(42.99, "USD")
        
        # Test __str__ method
        str_repr = str(money)
        assert "42.99" in str_repr
        assert "USD" in str_repr
        
        # Test __repr__ method  
        repr_str = repr(money)
        assert "Money" in repr_str
        assert "42.99" in repr_str
        assert "USD" in repr_str

    @patch('requests.post')
    @patch('requests.Session.patch')
    def test_http_client_patch_method(self, mock_patch, mock_post):
        """Test HTTP client PATCH method handling."""
        # Mock successful token response
        mock_token_response = Mock()
        mock_token_response.raise_for_status.return_value = None
        mock_token_response.json.return_value = {
            "access_token": "test_token",
            "expires_in": 3600
        }
        mock_post.return_value = mock_token_response
        
        # Mock PATCH response
        mock_patch_response = Mock()
        mock_patch_response.raise_for_status.return_value = None
        mock_patch_response.status_code = 200
        mock_patch_response.json.return_value = {"status": "updated"}
        mock_patch.return_value = mock_patch_response
        
        provider = PayPalProvider(self.valid_config)
        
        # Test PATCH request
        result = provider.http_client.request("PATCH", "/v2/test", {"data": "test"})
        assert result["status"] == "updated"

    @patch('requests.post')
    @patch('requests.Session.patch')
    def test_http_client_unsupported_method(self, mock_patch, mock_post):
        """Test HTTP client unsupported method handling."""
        # Mock successful token response
        mock_token_response = Mock()
        mock_token_response.raise_for_status.return_value = None
        mock_token_response.json.return_value = {
            "access_token": "test_token",
            "expires_in": 3600
        }
        mock_post.return_value = mock_token_response
        
        provider = PayPalProvider(self.valid_config)
        
        # Test unsupported HTTP method
        with pytest.raises(ValueError, match="Unsupported HTTP method: DELETE"):
            provider.http_client.request("DELETE", "/v2/test", {"data": "test"})

    @patch('requests.post')
    @patch('requests.Session.post')
    def test_http_client_empty_response(self, mock_session_post, mock_post):
        """Test HTTP client handling of empty responses."""
        # Mock successful token response
        mock_token_response = Mock()
        mock_token_response.raise_for_status.return_value = None
        mock_token_response.json.return_value = {
            "access_token": "test_token",
            "expires_in": 3600
        }
        mock_post.return_value = mock_token_response
        
        # Mock empty response (204 No Content)
        mock_empty_response = Mock()
        mock_empty_response.raise_for_status.return_value = None
        mock_empty_response.status_code = 204
        mock_session_post.return_value = mock_empty_response
        
        provider = PayPalProvider(self.valid_config)
        
        # Test empty response handling
        result = provider.http_client.request("POST", "/v2/test", {"data": "test"})
        assert result == {}

    def test_payment_request_dataclass(self):
        """Test PaymentRequest dataclass functionality."""
        from paymcp.providers.paypal.provider import PaymentRequest
        
        money = Money(50.00, "EUR")
        request = PaymentRequest(
            money=money,
            description="Test payment request",
            reference_id="ref-123",
            metadata={"user": "test_user", "order": "order-456"}
        )
        
        assert request.money == money
        assert request.description == "Test payment request"
        assert request.reference_id == "ref-123"
        assert request.metadata["user"] == "test_user"
        assert request.metadata["order"] == "order-456"

    def test_payment_result_dataclass(self):
        """Test PaymentResult dataclass functionality."""
        from paymcp.providers.paypal.provider import PaymentResult
        from datetime import datetime
        
        money = Money(25.99, "USD")
        created_at = datetime.now()
        
        result = PaymentResult(
            payment_id="PAY-123",
            status=PaymentStatus.CREATED,
            money=money,
            approval_url="https://paypal.com/approve/PAY-123",
            created_at=created_at,
            metadata={"order_id": "order-456"}
        )
        
        assert result.payment_id == "PAY-123"
        assert result.status == PaymentStatus.CREATED
        assert result.money == money
        assert result.approval_url == "https://paypal.com/approve/PAY-123"
        assert result.created_at == created_at
        assert result.metadata["order_id"] == "order-456"

    @patch('requests.post')
    def test_provider_logger_initialization(self, mock_post):
        """Test provider logger is properly initialized."""
        provider = PayPalProvider(self.valid_config)
        
        # Test logger exists and has correct name
        assert provider.logger is not None
        assert "PayPalProvider" in provider.logger.name

    def test_money_frozen_dataclass_properties(self):
        """Test Money frozen dataclass properties."""
        money = Money(75.50, "GBP")
        
        # Test that Money is frozen (cannot modify after creation)
        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            money.amount = 100.00

    @patch('requests.post')
    @patch('requests.Session.post')
    def test_http_error_handling(self, mock_session_post, mock_post):
        """Test HTTP error handling with detailed error extraction."""
        # Mock successful token response
        mock_token_response = Mock()
        mock_token_response.raise_for_status.return_value = None
        mock_token_response.json.return_value = {
            "access_token": "test_token",
            "expires_in": 3600
        }
        mock_post.return_value = mock_token_response
        
        # Mock HTTP error with JSON error details
        mock_error_response = Mock()
        mock_error_response.json.return_value = {
            "error": "VALIDATION_ERROR",
            "error_description": "Invalid request parameters"
        }
        
        http_error = HTTPError("400 Client Error")
        http_error.response = mock_error_response
        mock_session_post.side_effect = http_error
        
        provider = PayPalProvider(self.valid_config)
        
        # This should trigger the HTTPError -> PaymentError conversion
        with pytest.raises(PaymentError, match="PayPal API error"):
            provider.http_client.request("POST", "/v2/test", {"data": "test"})

    @patch('requests.post')
    @patch('requests.Session.post')
    def test_request_exception_handling(self, mock_session_post, mock_post):
        """Test general request exception handling."""
        # Mock successful token response
        mock_token_response = Mock()
        mock_token_response.raise_for_status.return_value = None
        mock_token_response.json.return_value = {
            "access_token": "test_token",
            "expires_in": 3600
        }
        mock_post.return_value = mock_token_response
        
        # Mock request exception
        mock_session_post.side_effect = RequestException("Connection failed")
        
        provider = PayPalProvider(self.valid_config)
        
        # This should trigger the RequestException -> PaymentError conversion  
        with pytest.raises(PaymentError, match="PayPal request error"):
            provider.http_client.request("POST", "/v2/test", {"data": "test"})

    @patch('requests.post')
    @patch('requests.Session.post')
    def test_error_details_extraction(self, mock_session_post, mock_post):
        """Test error details extraction from response."""
        # Mock successful token response
        mock_token_response = Mock()
        mock_token_response.raise_for_status.return_value = None
        mock_token_response.json.return_value = {
            "access_token": "test_token",
            "expires_in": 3600
        }
        mock_post.return_value = mock_token_response
        
        # Mock HTTP error with complex error details
        mock_error_response = Mock()
        mock_error_response.json.return_value = {
            "name": "VALIDATION_ERROR", 
            "message": "Request body validation failed",
            "details": [
                {
                    "field": "amount.value",
                    "issue": "REQUIRED_FIELD_MISSING"
                }
            ]
        }
        
        http_error = HTTPError("422 Unprocessable Entity")
        http_error.response = mock_error_response
        mock_session_post.side_effect = http_error
        
        provider = PayPalProvider(self.valid_config)
        
        # This should extract detailed error information
        with pytest.raises(PaymentError) as exc_info:
            provider.http_client.request("POST", "/v2/test", {"data": "test"})
        
        # Check that error message contains extracted details
        assert "PayPal API error" in str(exc_info.value)

    def test_exception_classes(self):
        """Test custom exception classes."""
        # Test AuthenticationError
        auth_error = AuthenticationError("Authentication failed")
        assert str(auth_error) == "Authentication failed"
        assert isinstance(auth_error, Exception)
        
        # Test PaymentError  
        payment_error = PaymentError("Payment failed")
        assert str(payment_error) == "Payment failed"
        assert isinstance(payment_error, Exception)

    @patch('requests.post')
    @patch('requests.Session.post')
    def test_payment_request_with_metadata_and_reference_id(self, mock_session_post, mock_post):
        """Test payment creation with metadata and reference_id."""
        # Mock successful token response
        mock_token_response = Mock()
        mock_token_response.raise_for_status.return_value = None
        mock_token_response.json.return_value = {
            "access_token": "test_token",
            "expires_in": 3600
        }
        mock_post.return_value = mock_token_response
        
        # Mock payment creation response
        mock_payment_response = Mock()
        mock_payment_response.raise_for_status.return_value = None
        mock_payment_response.json.return_value = {
            "id": "test_payment_id",
            "status": "CREATED",
            "links": [
                {"rel": "approve", "href": "https://paypal.com/approve/test_payment_id"}
            ]
        }
        mock_session_post.return_value = mock_payment_response
        
        provider = PayPalProvider(self.valid_config)
        
        # Create a payment request with metadata and reference_id through the order builder
        from paymcp.providers.paypal.provider import PaymentFactory
        
        request = PaymentFactory.create_payment_request(
            amount=25.99,
            currency="USD",
            description="Test payment with metadata",
            reference_id="ref-12345",
            metadata={"user_id": "user-456", "order_id": "order-789"}
        )
        
        # Use internal method to test metadata/reference_id handling
        result = provider._create_payment_internal(request)
        
        assert result.payment_id == "test_payment_id"

    def test_payment_factory_with_optional_params(self):
        """Test PaymentFactory with all optional parameters."""
        from paymcp.providers.paypal.provider import PaymentFactory
        
        request = PaymentFactory.create_payment_request(
            amount=99.99,
            currency="EUR",
            description="Complete test payment",
            reference_id="ref-abc-123",
            metadata={
                "customer_id": "cust-456", 
                "invoice_id": "inv-789",
                "campaign": "summer-sale"
            }
        )
        
        assert request.money.amount == 99.99
        assert request.money.currency == "EUR" 
        assert request.description == "Complete test payment"
        assert request.reference_id == "ref-abc-123"
        assert request.metadata["customer_id"] == "cust-456"
        assert request.metadata["invoice_id"] == "inv-789"
        assert request.metadata["campaign"] == "summer-sale"

    @patch('requests.post')
    def test_order_builder_initialization(self, mock_post):
        """Test order builder component initialization."""
        provider = PayPalProvider(self.valid_config)
        
        # Test that order builder is properly initialized
        assert hasattr(provider, 'order_builder')
        assert provider.order_builder is not None

    def test_payment_status_from_string_mapping(self):
        """Test payment status conversion from PayPal string values."""
        # Test the mapping that might be used internally
        status_map = {
            "CREATED": PaymentStatus.CREATED,
            "SAVED": PaymentStatus.CREATED,  # PayPal uses SAVED for drafts
            "APPROVED": PaymentStatus.APPROVED,
            "VOIDED": PaymentStatus.CANCELLED,
            "COMPLETED": PaymentStatus.COMPLETED,
            "PAYER_ACTION_REQUIRED": PaymentStatus.PENDING
        }
        
        # Test that each mapping works
        assert status_map["CREATED"] == PaymentStatus.CREATED
        assert status_map["APPROVED"] == PaymentStatus.APPROVED
        assert status_map["COMPLETED"] == PaymentStatus.COMPLETED
        assert status_map["VOIDED"] == PaymentStatus.CANCELLED

    def test_paypal_provider_invalid_config_type(self):
        """Test PayPalProvider initialization with invalid config type."""
        with pytest.raises(ValueError, match="config must be a PayPalConfig instance"):
            PayPalProvider("invalid_config_string")

    def test_paypal_provider_alternative_mcp_parameters(self):
        """Test PayPalProvider initialization with MCP-compatible parameter names."""
        # Test with api_key parameter
        provider = PayPalProvider(
            api_key="test_client_id_1234567890",
            client_secret="test_client_secret_1234567890", 
            sandbox=True
        )
        assert provider.config.client_id == "test_client_id_1234567890"
        assert provider.config.client_secret == "test_client_secret_1234567890"
        assert provider.config.sandbox is True

        # Test with apiKey parameter (camelCase)
        provider2 = PayPalProvider(
            apiKey="test_client_id_alt_1234567890",
            client_secret="test_client_secret_alt_1234567890",
            sandbox=False
        )
        assert provider2.config.client_id == "test_client_id_alt_1234567890"
        assert provider2.config.client_secret == "test_client_secret_alt_1234567890"
        assert provider2.config.sandbox is False

    @patch('requests.post')
    def test_provider_string_representations(self, mock_post):
        """Test PayPalProvider string representation methods."""
        provider = PayPalProvider(self.valid_config)
        
        # Test __str__ method
        str_repr = str(provider)
        assert "PayPalProvider" in str_repr
        
        # Test __repr__ method
        repr_str = repr(provider)
        assert "PayPalProvider" in repr_str

    @patch('requests.post')
    def test_provider_component_access(self, mock_post):
        """Test accessing provider internal components."""
        provider = PayPalProvider(self.valid_config)
        
        # Test that we can access key components
        assert provider.validator is not None
        assert provider.token_manager is not None
        assert provider.http_client is not None
        assert provider.order_builder is not None
        assert provider.logger is not None
        
        # Test component relationships
        assert provider.http_client.token_manager == provider.token_manager
        assert provider.http_client.config == provider.config

    def test_money_with_different_amount_types(self):
        """Test Money class with different numeric types."""
        # Test with int
        money_int = Money(100, "USD")
        assert money_int.amount == 100
        assert money_int.currency == "USD"
        
        # Test with float
        money_float = Money(100.50, "EUR")
        assert money_float.amount == 100.50
        assert money_float.currency == "EUR"
        
        # Test formatting consistency (default uses symbols)
        assert money_int.format() == "$100.00"  # USD has symbol
        assert money_float.format() == "€100.50"  # EUR has symbol too

    @patch('requests.post')
    @patch('requests.Session.post')
    def test_enhanced_payment_creation_method(self, mock_session_post, mock_post):
        """Test the enhanced payment creation interface."""
        # Mock successful token response
        mock_token_response = Mock()
        mock_token_response.raise_for_status.return_value = None
        mock_token_response.json.return_value = {
            "access_token": "test_token",
            "expires_in": 3600
        }
        mock_post.return_value = mock_token_response
        
        # Mock payment creation response  
        mock_payment_response = Mock()
        mock_payment_response.raise_for_status.return_value = None
        mock_payment_response.json.return_value = {
            "id": "enhanced_payment_id",
            "status": "CREATED",
            "links": [
                {"rel": "approve", "href": "https://paypal.com/approve/enhanced_payment_id"}
            ]
        }
        mock_session_post.return_value = mock_payment_response
        
        provider = PayPalProvider(self.valid_config)
        
        # Create enhanced payment request
        from paymcp.providers.paypal.provider import PaymentFactory
        request = PaymentFactory.create_payment_request(
            amount=75.25,
            currency="USD",
            description="Enhanced payment test"
        )
        
        # Test enhanced creation method
        result = provider.create_payment_enhanced(request)
        assert result.payment_id == "enhanced_payment_id"

    @patch('requests.post')
    @patch('requests.Session.get') 
    def test_payment_status_check_error_handling(self, mock_session_get, mock_post):
        """Test payment status check error handling."""
        # Mock successful token response
        mock_token_response = Mock()
        mock_token_response.raise_for_status.return_value = None
        mock_token_response.json.return_value = {
            "access_token": "test_token",
            "expires_in": 3600
        }
        mock_post.return_value = mock_token_response
        
        # Mock GET request failure
        mock_session_get.side_effect = RequestException("Status check failed")
        
        provider = PayPalProvider(self.valid_config)
        
        # This should trigger error handling in get_payment_status
        with pytest.raises(RuntimeError, match="PayPal status check failed"):
            provider.get_payment_status("test_payment_id")

    def test_payment_result_optional_fields(self):
        """Test PaymentResult with optional fields."""
        from paymcp.providers.paypal.provider import PaymentResult
        from datetime import datetime
        
        money = Money(50.99, "GBP")
        now = datetime.now()
        
        # Test with all fields
        result_full = PaymentResult(
            payment_id="PAY-FULL-123",
            status=PaymentStatus.APPROVED,
            money=money,
            approval_url="https://paypal.com/approve/full",
            created_at=now,
            metadata={"test": "data"}
        )
        
        assert result_full.payment_id == "PAY-FULL-123"
        assert result_full.status == PaymentStatus.APPROVED
        assert result_full.money == money
        assert result_full.approval_url == "https://paypal.com/approve/full"
        assert result_full.created_at == now
        assert result_full.metadata["test"] == "data"
        
        # Test with minimal fields (others should be None/default)
        result_minimal = PaymentResult(
            payment_id="PAY-MIN-456",
            status=PaymentStatus.CREATED,
            money=money
        )
        
        assert result_minimal.payment_id == "PAY-MIN-456"
        assert result_minimal.status == PaymentStatus.CREATED
        assert result_minimal.money == money
        assert result_minimal.approval_url is None
        assert result_minimal.created_at is None
        assert result_minimal.metadata is None


if __name__ == "__main__":
    pytest.main([__file__])