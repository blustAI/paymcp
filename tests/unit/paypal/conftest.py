"""
Pytest configuration and fixtures for PayPal provider tests.

This module provides common fixtures and configuration for all PayPal tests,
including test data, mock objects, and utility functions.
"""

import os
import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime

from paymcp.providers.paypal.provider import PayPalProvider
from paymcp.providers.paypal.config import PayPalConfig


@pytest.fixture
def valid_config():
    """Provide a valid PayPal configuration for testing."""
    return PayPalConfig(
        client_id="test_client_id_12345",
        client_secret="test_client_secret_67890",
        sandbox=True,
        return_url="https://example.com/payment/success",
        cancel_url="https://example.com/payment/cancel",
        brand_name="Test Store",
        locale="en-US",
        timeout=30,
        max_retries=3
    )


@pytest.fixture
def production_config():
    """Provide a production PayPal configuration for testing."""
    return PayPalConfig(
        client_id="prod_client_id_12345",
        client_secret="prod_client_secret_67890",
        sandbox=False,
        return_url="https://production.example.com/payment/success",
        cancel_url="https://production.example.com/payment/cancel",
        webhook_url="https://production.example.com/webhook",
        brand_name="Production Store"
    )


@pytest.fixture
def paypal_provider(valid_config):
    """Provide a PayPal provider instance for testing."""
    return PayPalProvider(config=valid_config)


@pytest.fixture
def mock_token_response():
    """Provide a mock successful token response."""
    mock_response = Mock()
    mock_response.json.return_value = {
        'access_token': 'mock_access_token_12345',
        'expires_in': 3600,
        'token_type': 'Bearer'
    }
    mock_response.raise_for_status.return_value = None
    mock_response.status_code = 200
    return mock_response


@pytest.fixture
def mock_payment_response():
    """Provide a mock successful payment creation response."""
    mock_response = Mock()
    mock_response.json.return_value = {
        'id': 'PAYID-TEST123456789',
        'status': 'CREATED',
        'links': [
            {
                'rel': 'self',
                'href': 'https://api-m.sandbox.paypal.com/v2/checkout/orders/PAYID-TEST123456789'
            },
            {
                'rel': 'approve',
                'href': 'https://www.sandbox.paypal.com/checkoutnow?token=PAYID-TEST123456789'
            }
        ],
        'create_time': '2024-01-01T10:00:00Z',
        'purchase_units': [
            {
                'amount': {
                    'currency_code': 'USD',
                    'value': '25.99'
                },
                'description': 'Test payment'
            }
        ]
    }
    mock_response.raise_for_status.return_value = None
    mock_response.status_code = 201
    return mock_response


@pytest.fixture
def mock_payment_status_response():
    """Provide a mock payment status response."""
    mock_response = Mock()
    mock_response.json.return_value = {
        'id': 'PAYID-TEST123456789',
        'status': 'APPROVED',
        'create_time': '2024-01-01T10:00:00Z',
        'update_time': '2024-01-01T10:05:00Z',
        'purchase_units': [
            {
                'amount': {
                    'currency_code': 'USD',
                    'value': '25.99'
                }
            }
        ]
    }
    mock_response.raise_for_status.return_value = None
    mock_response.status_code = 200
    return mock_response


@pytest.fixture
def mock_error_response():
    """Provide a mock error response."""
    mock_response = Mock()
    mock_response.json.return_value = {
        'error': 'invalid_client',
        'error_description': 'Client authentication failed'
    }
    mock_response.raise_for_status.side_effect = Exception("401 Unauthorized")
    mock_response.status_code = 401
    return mock_response


@pytest.fixture
def sample_payment_data():
    """Provide sample payment data for testing."""
    return {
        'amount': 25.99,
        'currency': 'USD',
        'description': 'Test payment for unit testing',
        'reference_id': 'TEST-REF-001',
        'metadata': {
            'test_mode': 'true',
            'source': 'unit_tests'
        }
    }


@pytest.fixture
def sample_currencies():
    """Provide sample currency codes for testing."""
    return ['USD', 'EUR', 'GBP', 'CAD', 'AUD', 'JPY']


@pytest.fixture
def integration_credentials():
    """Provide real credentials for integration tests (if available)."""
    return {
        'client_id': os.getenv('PAYPAL_CLIENT_ID'),
        'client_secret': os.getenv('PAYPAL_CLIENT_SECRET')
    }


@pytest.fixture
def skip_without_credentials():
    """Skip test if PayPal credentials are not available."""
    client_id = os.getenv('PAYPAL_CLIENT_ID')
    client_secret = os.getenv('PAYPAL_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        pytest.skip("PayPal credentials not found. Set PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET")


# Test markers
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (require real API calls)"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests (default)"
    )


@pytest.fixture
def mock_requests_session():
    """Provide a mock requests session."""
    session = MagicMock()
    
    # Mock successful token request
    token_response = Mock()
    token_response.json.return_value = {
        'access_token': 'mock_token',
        'expires_in': 3600
    }
    token_response.raise_for_status.return_value = None
    
    # Mock successful payment request
    payment_response = Mock()
    payment_response.json.return_value = {
        'id': 'PAYID-MOCK123',
        'status': 'CREATED',
        'links': [{'rel': 'approve', 'href': 'https://paypal.com/approve'}]
    }
    payment_response.raise_for_status.return_value = None
    
    session.post.return_value = payment_response
    session.get.return_value = payment_response
    
    return session


@pytest.fixture(autouse=True)
def clean_environment():
    """Clean up environment variables before each test."""
    # Store original values
    original_env = {}
    paypal_env_vars = [
        'PAYPAL_CLIENT_ID',
        'PAYPAL_CLIENT_SECRET', 
        'PAYPAL_SANDBOX',
        'PAYPAL_RETURN_URL',
        'PAYPAL_CANCEL_URL',
        'PAYPAL_WEBHOOK_URL',
        'PAYPAL_BRAND_NAME',
        'PAYPAL_LOCALE',
        'PAYPAL_TIMEOUT',
        'PAYPAL_MAX_RETRIES'
    ]
    
    for var in paypal_env_vars:
        original_env[var] = os.environ.get(var)
    
    yield
    
    # Restore original environment
    for var, value in original_env.items():
        if value is not None:
            os.environ[var] = value
        elif var in os.environ:
            del os.environ[var]


class PayPalTestHelper:
    """Helper class for PayPal testing utilities."""
    
    @staticmethod
    def create_mock_provider_with_token(config=None):
        """Create a PayPal provider with a pre-authenticated token."""
        if config is None:
            config = PayPalConfig(
                client_id="test_id",
                client_secret="test_secret",
                sandbox=True
            )
        
        provider = PayPalProvider(config=config)
        provider._access_token = "mock_token_12345"
        provider._token_expires_at = datetime.now().timestamp() + 3600
        
        return provider
    
    @staticmethod
    def assert_valid_payment_id(payment_id):
        """Assert that a payment ID has valid format."""
        assert payment_id is not None
        assert isinstance(payment_id, str)
        assert len(payment_id) > 10
        assert payment_id.strip() == payment_id  # No leading/trailing whitespace
    
    @staticmethod
    def assert_valid_payment_url(payment_url):
        """Assert that a payment URL has valid format."""
        assert payment_url is not None
        assert isinstance(payment_url, str)
        assert payment_url.startswith('https://')
        assert 'paypal.com' in payment_url.lower()


@pytest.fixture
def test_helper():
    """Provide PayPal test helper utilities."""
    return PayPalTestHelper


# Performance testing utilities
@pytest.fixture
def performance_timer():
    """Provide a simple performance timer for tests."""
    import time
    
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def start(self):
            self.start_time = time.time()
        
        def stop(self):
            self.end_time = time.time()
        
        @property
        def elapsed(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None
    
    return Timer()


# Parameterization helpers
@pytest.fixture(params=['USD', 'EUR', 'GBP', 'CAD'])
def currency_code(request):
    """Parameterized fixture for testing multiple currencies."""
    return request.param


@pytest.fixture(params=[1.00, 10.50, 100.99, 999.99])
def valid_amount(request):
    """Parameterized fixture for testing multiple valid amounts."""
    return request.param


@pytest.fixture(params=[True, False])
def sandbox_mode(request):
    """Parameterized fixture for testing both sandbox and production modes."""
    return request.param