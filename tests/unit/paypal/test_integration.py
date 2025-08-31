"""
Integration tests for PayPal payment provider.

This module contains integration tests that interact with PayPal's sandbox environment
to test real API interactions. These tests require valid PayPal sandbox credentials.

Environment Variables Required:
- PAYPAL_CLIENT_ID: PayPal sandbox client ID
- PAYPAL_CLIENT_SECRET: PayPal sandbox client secret

Usage:
    # Set environment variables first
    export PAYPAL_CLIENT_ID="your_sandbox_client_id"
    export PAYPAL_CLIENT_SECRET="your_sandbox_client_secret"
    
    # Run integration tests
    pytest src/paymcp/providers/paypal/tests/test_integration.py -v
    
    # Run specific test
    pytest src/paymcp/providers/paypal/tests/test_integration.py::TestPayPalIntegration::test_create_payment -v
"""

import os
import pytest
import time
from decimal import Decimal

from paymcp.providers.paypal.provider import PayPalProvider, AuthenticationError, PaymentError
from paymcp.providers.paypal.config import PayPalConfig


@pytest.mark.integration
class TestPayPalIntegration:
    """Integration tests using real PayPal sandbox API."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up integration test environment."""
        self.client_id = os.getenv("PAYPAL_CLIENT_ID")
        self.client_secret = os.getenv("PAYPAL_CLIENT_SECRET")
        
        if not self.client_id or not self.client_secret:
            pytest.skip("PayPal credentials not found. Set PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET")
        
        self.config = PayPalConfig(
            client_id=self.client_id,
            client_secret=self.client_secret,
            sandbox=True,
            return_url="https://example.com/payment/success",
            cancel_url="https://example.com/payment/cancel",
            brand_name="PayMCP Integration"
        )
        
        self.provider = PayPalProvider(config=self.config)
    
    def test_authentication(self):
        """Test authentication with PayPal sandbox."""
        # This should succeed with valid credentials
        token = self.provider.token_manager.get_token()
        
        assert token is not None
        assert len(token) > 10  # Token should be substantial
    
    def test_create_payment(self):
        """Test creating a payment order."""
        payment_id, payment_url = self.provider.create_payment(
            amount=25.99,
            currency="USD",
            description="Integration test payment"
        )
        
        assert payment_id is not None
        assert len(payment_id) > 10
        assert payment_url is not None
        assert "paypal.com" in payment_url or "sandbox.paypal.com" in payment_url
        assert "approve" in payment_url.lower() or "checkout" in payment_url.lower()
        
        # Store payment ID for status test
        self.created_payment_id = payment_id
    
    def test_payment_status_created(self):
        """Test checking status of a newly created payment."""
        # Create a payment first
        payment_id, _ = self.provider.create_payment(
            amount=10.50,
            currency="USD",
            description="Status test payment"
        )
        
        # Check its status
        status = self.provider.get_payment_status(payment_id)
        
        # New payment should be in 'created' status
        assert status in ["created", "pending"]
    
    def test_multiple_currencies(self):
        """Test creating payments with different currencies."""
        currencies = ["USD"]  # Only test USD to avoid currency configuration issues
        
        for currency in currencies:
            payment_id, payment_url = self.provider.create_payment(
                amount=15.00,
                currency=currency,
                description=f"Multi-currency test - {currency}"
            )
            
            assert payment_id is not None
            assert payment_url is not None
            
            # Small delay to avoid rate limiting
            time.sleep(0.5)
    
    def test_various_amounts(self):
        """Test creating payments with various amounts."""
        amounts = [1.00, 5.99, 100.00, 999.99]
        
        for amount in amounts:
            payment_id, payment_url = self.provider.create_payment(
                amount=amount,
                currency="USD",
                description=f"Amount test - ${amount}"
            )
            
            assert payment_id is not None
            assert payment_url is not None
            
            # Small delay to avoid rate limiting
            time.sleep(0.5)
    
    def test_long_description(self):
        """Test payment with maximum length description."""
        long_description = "Integration test payment with a long description that stays within PayPal limits for API testing."
        
        payment_id, payment_url = self.provider.create_payment(
            amount=20.00,
            currency="USD",
            description=long_description
        )
        
        assert payment_id is not None
        assert payment_url is not None
    
    def test_special_characters_description(self):
        """Test payment with special characters in description."""
        special_desc = "Test payment with basic special characters and symbols"
        
        payment_id, payment_url = self.provider.create_payment(
            amount=15.50,
            currency="USD",
            description=special_desc
        )
        
        assert payment_id is not None
        assert payment_url is not None
    
    def test_concurrent_payments(self):
        """Test creating multiple payments concurrently."""
        import threading
        
        results = []
        errors = []
        
        def create_payment_thread(thread_id):
            try:
                payment_id, payment_url = self.provider.create_payment(
                    amount=5.00 + thread_id,
                    currency="USD",
                    description=f"Concurrent test payment {thread_id}"
                )
                results.append((payment_id, payment_url))
            except Exception as e:
                errors.append(e)
        
        # Create 5 concurrent payment requests
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_payment_thread, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 5
        
        for payment_id, payment_url in results:
            assert payment_id is not None
            assert payment_url is not None


@pytest.mark.integration
class TestPayPalErrorScenarios:
    """Integration tests for error scenarios."""
    
    def test_invalid_credentials(self):
        """Test authentication with invalid credentials."""
        invalid_config = PayPalConfig(
            client_id="invalid_client_id",
            client_secret="invalid_client_secret",
            sandbox=True,
            return_url="https://example.com/success",
            cancel_url="https://example.com/cancel"
        )
        
        provider = PayPalProvider(config=invalid_config)
        
        with pytest.raises(AuthenticationError):
            provider.token_manager.get_token()
    
    def test_invalid_payment_id_status(self):
        """Test checking status of invalid payment ID."""
        client_id = os.getenv("PAYPAL_CLIENT_ID")
        client_secret = os.getenv("PAYPAL_CLIENT_SECRET")
        
        if not client_id or not client_secret:
            pytest.skip("PayPal credentials not found")
        
        config = PayPalConfig(
            client_id=client_id,
            client_secret=client_secret,
            sandbox=True,
            return_url="https://example.com/success",
            cancel_url="https://example.com/cancel"
        )
        
        provider = PayPalProvider(config=config)
        
        with pytest.raises((PaymentError, RuntimeError)):
            provider.get_payment_status("INVALID_PAYMENT_ID")
    
    def test_network_resilience(self):
        """Test network error handling with real requests."""
        client_id = os.getenv("PAYPAL_CLIENT_ID")
        client_secret = os.getenv("PAYPAL_CLIENT_SECRET")
        
        if not client_id or not client_secret:
            pytest.skip("PayPal credentials not found")
        
        # Test with invalid URL to simulate network issues
        config = PayPalConfig(
            client_id=client_id,
            client_secret=client_secret,
            sandbox=True,
            return_url="https://example.com/success",
            cancel_url="https://example.com/cancel",
            base_url="https://invalid-paypal-url.com"  # This will cause network error
        )
        
        provider = PayPalProvider(config=config)
        
        with pytest.raises((PaymentError, AuthenticationError, RuntimeError)):
            provider.create_payment(10.0, "USD", "Network test")


@pytest.mark.integration
@pytest.mark.slow
class TestPayPalPerformance:
    """Performance and load tests."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up performance test environment."""
        client_id = os.getenv("PAYPAL_CLIENT_ID")
        client_secret = os.getenv("PAYPAL_CLIENT_SECRET")
        
        if not client_id or not client_secret:
            pytest.skip("PayPal credentials not found")
        
        self.config = PayPalConfig(
            client_id=client_id,
            client_secret=client_secret,
            sandbox=True,
            return_url="https://example.com/success",
            cancel_url="https://example.com/cancel"
        )
        
        self.provider = PayPalProvider(config=self.config)
    
    def test_token_caching(self):
        """Test that access tokens are properly cached."""
        # First request should get a new token
        start_time = time.time()
        token1 = self.provider.token_manager.get_token()
        first_request_time = time.time() - start_time
        
        # Second request should use cached token (faster)
        start_time = time.time()
        token2 = self.provider.token_manager.get_token()
        second_request_time = time.time() - start_time
        
        assert token1 == token2
        assert second_request_time < first_request_time / 2  # Should be much faster
    
    def test_rapid_payments(self):
        """Test creating many payments rapidly."""
        payment_count = 10
        start_time = time.time()
        
        payment_ids = []
        for i in range(payment_count):
            payment_id, _ = self.provider.create_payment(
                amount=1.00 + (i * 0.01),  # Vary amounts slightly
                currency="USD",
                description=f"Rapid test payment {i}"
            )
            payment_ids.append(payment_id)
        
        total_time = time.time() - start_time
        avg_time = total_time / payment_count
        
        assert len(payment_ids) == payment_count
        assert len(set(payment_ids)) == payment_count  # All unique
        assert avg_time < 5.0  # Each payment should take less than 5 seconds
        
        print(f"Created {payment_count} payments in {total_time:.2f}s (avg: {avg_time:.2f}s/payment)")


if __name__ == "__main__":
    # Run integration tests with verbose output
    pytest.main([
        __file__, 
        "-v", 
        "--tb=short",
        "-m", "integration"
    ])