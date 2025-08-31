"""
Unit tests for PayPal configuration.

This module contains comprehensive unit tests for the PayPalConfig class,
covering configuration creation, validation, environment handling,
and security features.
"""

import os
import pytest
from unittest.mock import patch

from paymcp.providers.paypal.config import PayPalConfig, PayPalConfigError


class TestPayPalConfig:
    """Test the PayPal configuration class."""
    
    def test_init_with_valid_params(self):
        """Test initialization with valid parameters."""
        config = PayPalConfig(
            client_id="test_client_id",
            client_secret="test_client_secret",
            sandbox=True,
            return_url="https://example.com/success",
            cancel_url="https://example.com/cancel"
        )
        
        assert config.client_id == "test_client_id"
        assert config.client_secret == "test_client_secret"
        assert config.sandbox is True
        assert config.return_url == "https://example.com/success"
        assert config.cancel_url == "https://example.com/cancel"
        assert config.base_url == "https://api-m.sandbox.paypal.com"
        assert config.timeout == 30
        assert config.max_retries == 3
    
    def test_init_with_minimal_params(self):
        """Test initialization with minimal required parameters."""
        config = PayPalConfig(
            client_id="test_client_id",
            client_secret="test_client_secret"
        )
        
        assert config.client_id == "test_client_id"
        assert config.client_secret == "test_client_secret"
        assert config.sandbox is True  # Default to sandbox
        assert config.return_url is None
        assert config.cancel_url is None
        assert config.base_url == "https://api-m.sandbox.paypal.com"
    
    def test_production_environment(self):
        """Test production environment configuration."""
        config = PayPalConfig(
            client_id="test_client_id",
            client_secret="test_client_secret",
            sandbox=False
        )
        
        assert config.sandbox is False
        assert config.base_url == "https://api-m.paypal.com"
    
    def test_init_with_invalid_client_id(self):
        """Test initialization with invalid client ID."""
        with pytest.raises(PayPalConfigError):
            PayPalConfig(
                client_id="",
                client_secret="test_client_secret"
            )
        
        with pytest.raises(PayPalConfigError):
            PayPalConfig(
                client_id=None,
                client_secret="test_client_secret"
            )
    
    def test_init_with_invalid_client_secret(self):
        """Test initialization with invalid client secret."""
        with pytest.raises(PayPalConfigError):
            PayPalConfig(
                client_id="test_client_id",
                client_secret=""
            )
        
        with pytest.raises(PayPalConfigError):
            PayPalConfig(
                client_id="test_client_id",
                client_secret=None
            )
    
    def test_init_with_invalid_urls(self):
        """Test initialization with invalid URLs."""
        # HTTP URLs should be rejected in production mode
        with pytest.raises(PayPalConfigError):
            PayPalConfig(
                client_id="test_client_id_1234567890",
                client_secret="test_client_secret_1234567890", 
                sandbox=False,  # Production mode
                return_url="http://example.com"  # HTTP not allowed in production
            )
        
        # Invalid URL format should always be rejected
        with pytest.raises(PayPalConfigError):
            PayPalConfig(
                client_id="test_client_id_1234567890",
                client_secret="test_client_secret_1234567890",
                cancel_url="not-a-url"  # Invalid URL format
            )
    
    def test_custom_configuration(self):
        """Test custom configuration parameters."""
        config = PayPalConfig(
            client_id="test_client_id",
            client_secret="test_client_secret",
            sandbox=True,
            return_url="https://example.com/success",
            cancel_url="https://example.com/cancel",
            webhook_url="https://example.com/webhook",
            brand_name="Test Store",
            locale="en-US",
            timeout=60,
            max_retries=5
        )
        
        assert config.webhook_url == "https://example.com/webhook"
        assert config.brand_name == "Test Store"
        assert config.locale == "en-US"
        assert config.timeout == 60
        assert config.max_retries == 5
    
    def test_from_dict_method(self):
        """Test creating config from dictionary."""
        config_dict = {
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
            "sandbox": True,
            "return_url": "https://example.com/success",
            "cancel_url": "https://example.com/cancel",
            "brand_name": "Dict Store",
            "timeout": 45
        }
        
        config = PayPalConfig.from_dict(config_dict)
        
        assert config.client_id == "test_client_id"
        assert config.client_secret == "test_client_secret"
        assert config.sandbox is True
        assert config.return_url == "https://example.com/success"
        assert config.cancel_url == "https://example.com/cancel"
        assert config.brand_name == "Dict Store"
        assert config.timeout == 45
    
    def test_from_dict_with_missing_required(self):
        """Test from_dict with missing required fields."""
        incomplete_dict = {
            "client_id": "test_client_id"
            # Missing client_secret
        }
        
        with pytest.raises(PayPalConfigError):
            PayPalConfig.from_dict(incomplete_dict)
    
    @patch.dict(os.environ, {
        'PAYPAL_CLIENT_ID': 'env_client_id',
        'PAYPAL_CLIENT_SECRET': 'env_client_secret',
        'PAYPAL_SANDBOX': 'false',
        'PAYPAL_RETURN_URL': 'https://env.example.com/success',
        'PAYPAL_CANCEL_URL': 'https://env.example.com/cancel',
        'PAYPAL_BRAND_NAME': 'Env Store',
        'PAYPAL_TIMEOUT': '120'
    })
    def test_from_env_method(self):
        """Test creating config from environment variables."""
        config = PayPalConfig.from_env()
        
        assert config.client_id == "env_client_id"
        assert config.client_secret == "env_client_secret"
        assert config.sandbox is False
        assert config.return_url == "https://env.example.com/success"
        assert config.cancel_url == "https://env.example.com/cancel"
        assert config.brand_name == "Env Store"
        assert config.timeout == 120
    
    @patch.dict(os.environ, {}, clear=True)
    def test_from_env_with_missing_required(self):
        """Test from_env with missing required environment variables."""
        with pytest.raises(PayPalConfigError):
            PayPalConfig.from_env(load_dotenv=False)
    
    @patch.dict(os.environ, {
        'PAYPAL_CLIENT_ID': 'env_client_id',
        'PAYPAL_CLIENT_SECRET': 'env_client_secret',
        'PAYPAL_SANDBOX': 'invalid_boolean'
    })
    def test_from_env_with_invalid_boolean(self):
        """Test from_env with invalid boolean values."""
        with pytest.raises(PayPalConfigError):
            PayPalConfig.from_env()
    
    def test_to_dict_method(self):
        """Test converting config to dictionary."""
        config = PayPalConfig(
            client_id="test_client_id",
            client_secret="test_client_secret",
            sandbox=True,
            return_url="https://example.com/success",
            brand_name="Test Store"
        )
        
        config_dict = config.to_dict()
        
        assert config_dict["client_id"] == "test_client_id"
        assert config_dict["client_secret"] == "test_client_secret"
        assert config_dict["sandbox"] is True
        assert config_dict["return_url"] == "https://example.com/success"
        assert config_dict["brand_name"] == "Test Store"
        assert "base_url" in config_dict
    
    def test_to_dict_exclude_sensitive(self):
        """Test converting config to dictionary excluding sensitive data."""
        config = PayPalConfig(
            client_id="test_client_id",
            client_secret="test_client_secret",
            sandbox=True
        )
        
        config_dict = config.to_dict(include_sensitive=False)
        
        assert "client_id" not in config_dict
        assert "client_secret" not in config_dict
        assert config_dict["sandbox"] is True
        assert "base_url" in config_dict
    
    def test_mask_sensitive_data(self):
        """Test masking of sensitive configuration data."""
        config = PayPalConfig(
            client_id="very_long_client_id_12345",
            client_secret="super_secret_key_67890",
            sandbox=True
        )
        
        masked_dict = config.mask_sensitive_data()
        
        assert masked_dict["client_id"] == "very...2345"
        assert masked_dict["client_secret"] == "supe...7890"
        assert masked_dict["sandbox"] is True
    
    def test_validate_method(self):
        """Test explicit validation method."""
        # Valid config should pass validation
        config = PayPalConfig(
            client_id="test_client_id",
            client_secret="test_client_secret",
            sandbox=True,
            return_url="https://example.com/success"
        )
        
        # Should not raise exception
        config.validate()
    
    def test_validate_with_invalid_data(self):
        """Test validation with invalid configuration data."""
        # Create config with valid initial data
        config = PayPalConfig(
            client_id="test_client_id",
            client_secret="test_client_secret",
            sandbox=True
        )
        
        # Manually corrupt the data to test validation
        config.client_id = ""
        
        with pytest.raises(PayPalConfigError):
            config.validate()
    
    def test_custom_base_url(self):
        """Test custom base URL configuration."""
        custom_url = "https://custom-paypal-api.example.com"
        
        config = PayPalConfig(
            client_id="test_client_id",
            client_secret="test_client_secret",
            sandbox=True,
            base_url=custom_url
        )
        
        assert config.base_url == custom_url
    
    def test_webhook_url_validation(self):
        """Test webhook URL specific validation."""
        # Valid webhook URL
        config = PayPalConfig(
            client_id="test_client_id_1234567890",
            client_secret="test_client_secret_1234567890",
            webhook_url="https://api.example.com/webhook"
        )
        assert config.webhook_url == "https://api.example.com/webhook"
        
        # Invalid webhook URL (localhost not allowed)
        with pytest.raises(PayPalConfigError):
            PayPalConfig(
                client_id="test_client_id_1234567890",
                client_secret="test_client_secret_1234567890",
                webhook_url="https://localhost/webhook"
            )
    
    def test_brand_name_validation(self):
        """Test brand name validation."""
        # Valid brand name
        config = PayPalConfig(
            client_id="test_client_id",
            client_secret="test_client_secret",
            brand_name="Valid Store Name"
        )
        assert config.brand_name == "Valid Store Name"
        
        # Brand name too long
        with pytest.raises(PayPalConfigError):
            PayPalConfig(
                client_id="test_client_id",
                client_secret="test_client_secret",
                brand_name="A" * 30  # Too long
            )
    
    def test_locale_validation(self):
        """Test locale validation."""
        # Valid locale
        config = PayPalConfig(
            client_id="test_client_id_1234567890",
            client_secret="test_client_secret_1234567890",
            locale="en-US"
        )
        assert config.locale == "en-US"
        
        # Invalid locale format
        with pytest.raises(PayPalConfigError):
            PayPalConfig(
                client_id="test_client_id_1234567890",
                client_secret="test_client_secret_1234567890",
                locale="english"  # Invalid format
            )
    
    def test_timeout_validation(self):
        """Test timeout validation."""
        # Valid timeout
        config = PayPalConfig(
            client_id="test_client_id",
            client_secret="test_client_secret",
            timeout=60
        )
        assert config.timeout == 60
        
        # Invalid timeout (too small)
        with pytest.raises(PayPalConfigError):
            PayPalConfig(
                client_id="test_client_id",
                client_secret="test_client_secret",
                timeout=0
            )
        
        # Invalid timeout (too large)
        with pytest.raises(PayPalConfigError):
            PayPalConfig(
                client_id="test_client_id",
                client_secret="test_client_secret",
                timeout=1000
            )
    
    def test_max_retries_validation(self):
        """Test max retries validation."""
        # Valid max retries
        config = PayPalConfig(
            client_id="test_client_id",
            client_secret="test_client_secret",
            max_retries=5
        )
        assert config.max_retries == 5
        
        # Invalid max retries (negative)
        with pytest.raises(PayPalConfigError):
            PayPalConfig(
                client_id="test_client_id",
                client_secret="test_client_secret",
                max_retries=-1
            )
        
        # Invalid max retries (too large)
        with pytest.raises(PayPalConfigError):
            PayPalConfig(
                client_id="test_client_id",
                client_secret="test_client_secret",
                max_retries=20
            )


class TestPayPalConfigSecurity:
    """Test security features of PayPal configuration."""
    
    def test_no_credential_logging(self):
        """Test that credentials are not exposed in string representation."""
        config = PayPalConfig(
            client_id="secret_client_id_1234567890",
            client_secret="super_secret_key_1234567890",
            sandbox=True
        )
        
        config_str = str(config)
        
        # Credentials should not appear in string representation
        assert "secret_client_id_1234567890" not in config_str
        assert "super_secret_key_1234567890" not in config_str
        assert "masked" in config_str.lower() or "*" in config_str or "..." in config_str
    
    def test_repr_security(self):
        """Test that repr doesn't expose credentials."""
        config = PayPalConfig(
            client_id="secret_client_id_1234567890",
            client_secret="super_secret_key_1234567890",
            sandbox=True
        )
        
        config_repr = repr(config)
        
        # Credentials should not appear in repr
        assert "secret_client_id_1234567890" not in config_repr
        assert "super_secret_key_1234567890" not in config_repr
    
    def test_copy_security(self):
        """Test that copying config maintains security."""
        import copy
        
        original_config = PayPalConfig(
            client_id="secret_client_id",
            client_secret="super_secret_key",
            sandbox=True
        )
        
        copied_config = copy.deepcopy(original_config)
        
        # Copied config should have same credentials
        assert copied_config.client_id == original_config.client_id
        assert copied_config.client_secret == original_config.client_secret
        
        # But string representations should still be secure
        assert "secret_client_id" not in str(copied_config)
        assert "super_secret_key" not in str(copied_config)


class TestPayPalConfigEnvironmentHandling:
    """Test environment-specific configuration handling."""
    
    def test_sandbox_vs_production_urls(self):
        """Test correct URL selection for different environments."""
        sandbox_config = PayPalConfig(
            client_id="test_client_id_1234567890",
            client_secret="test_client_secret_1234567890",
            sandbox=True
        )
        
        production_config = PayPalConfig(
            client_id="test_client_id_1234567890",
            client_secret="test_client_secret_1234567890",
            sandbox=False
        )
        
        assert "sandbox" in sandbox_config.base_url
        assert "sandbox" not in production_config.base_url
        assert sandbox_config.base_url != production_config.base_url
    
    @patch.dict(os.environ, {
        'PAYPAL_CLIENT_ID': 'env_client_id_1234567890',
        'PAYPAL_CLIENT_SECRET': 'env_client_secret_1234567890'
    })
    def test_env_override(self):
        """Test that environment variables can override defaults."""
        config = PayPalConfig.from_env()
        
        assert config.client_id == "env_client_id_1234567890"
        assert config.client_secret == "env_client_secret_1234567890"
        # Should default to sandbox when not specified
        assert config.sandbox is True
    
    def test_mixed_configuration_sources(self):
        """Test mixing direct parameters with environment variables."""
        with patch.dict(os.environ, {'PAYPAL_CLIENT_ID': 'env_id_1234567890'}):
            # Should be able to provide some params directly and others from env
            config = PayPalConfig(
                client_id="direct_client_id_1234567890",  # This should override env
                client_secret="direct_client_secret_1234567890",
                sandbox=False
            )
            
            assert config.client_id == "direct_client_id_1234567890"  # Direct param wins
            assert config.client_secret == "direct_client_secret_1234567890"
            assert config.sandbox is False


class TestPayPalConfigValidationEdgeCases:
    """Test PayPal configuration validation edge cases."""

    def test_validate_with_edge_case_urls(self):
        """Test URL validation with edge cases."""
        config = PayPalConfig(
            client_id="test_client_id_1234567890",
            client_secret="test_client_secret_1234567890",
            return_url="http://localhost:8080/callback",  # localhost URL
            cancel_url="https://example.com:9090/cancel?param=value"  # URL with port and query
        )
        
        # Should not raise any exceptions
        config.validate()
        assert config.return_url == "http://localhost:8080/callback"

    def test_validate_with_very_long_brand_name(self):
        """Test validation with maximum length brand name."""
        config = PayPalConfig(
            client_id="test_client_id_1234567890",
            client_secret="test_client_secret_1234567890",
            brand_name="A" * 22  # Maximum allowed length (22 chars)
        )
        
        config.validate()
        assert len(config.brand_name) == 22

    def test_validate_timeout_edge_values(self):
        """Test timeout validation with edge values."""
        # Test minimum timeout
        config = PayPalConfig(
            client_id="test_client_id_1234567890",
            client_secret="test_client_secret_1234567890",
            timeout=1  # Minimum value
        )
        config.validate()
        assert config.timeout == 1
        
        # Test high timeout
        config = PayPalConfig(
            client_id="test_client_id_1234567890",
            client_secret="test_client_secret_1234567890",
            timeout=300  # High value
        )
        config.validate()
        assert config.timeout == 300

    def test_validate_max_retries_edge_values(self):
        """Test max_retries validation with edge values."""
        # Test zero retries
        config = PayPalConfig(
            client_id="test_client_id_1234567890",
            client_secret="test_client_secret_1234567890",
            max_retries=0  # No retries
        )
        config.validate()
        assert config.max_retries == 0
        
        # Test high retry count
        config = PayPalConfig(
            client_id="test_client_id_1234567890",
            client_secret="test_client_secret_1234567890",
            max_retries=10  # High retry count
        )
        config.validate()
        assert config.max_retries == 10


class TestPayPalConfigErrorHandling:
    """Test PayPal configuration error handling scenarios."""

    def test_from_dict_with_malformed_data(self):
        """Test from_dict with malformed data types."""
        with pytest.raises(TypeError):  # TypeError when trying len() on int
            PayPalConfig.from_dict({
                "client_id": 12345,  # Should be string
                "client_secret": "test_client_secret_1234567890"
            })

    def test_from_dict_with_none_values(self):
        """Test from_dict with None values."""
        with pytest.raises(PayPalConfigError, match="client_id and client_secret are required"):
            PayPalConfig.from_dict({
                "client_id": None,
                "client_secret": "test_client_secret_1234567890"
            })

    def test_custom_base_url_validation(self):
        """Test custom base URL validation."""
        with pytest.raises(PayPalConfigError, match="Invalid base_url"):
            PayPalConfig(
                client_id="test_client_id_1234567890",
                client_secret="test_client_secret_1234567890",
                base_url="invalid_url"  # Invalid URL format
            )

    def test_short_client_id_validation(self):
        """Test validation of too short client ID."""
        with pytest.raises(PayPalConfigError, match="client_id appears to be invalid"):
            PayPalConfig(
                client_id="short",  # Too short (< 10 chars)
                client_secret="test_client_secret_1234567890"
            )

    def test_short_client_secret_validation(self):
        """Test validation of too short client secret."""
        with pytest.raises(PayPalConfigError, match="client_secret appears to be invalid"):
            PayPalConfig(
                client_id="test_client_id_1234567890",
                client_secret="short"  # Too short (< 10 chars)
            )


class TestPayPalConfigCredentialMasking:
    """Test credential masking functionality."""

    def test_mask_sensitive_data_method(self):
        """Test mask_sensitive_data method works correctly."""
        config = PayPalConfig(
            client_id="test_client_id_1234567890",
            client_secret="test_client_secret_1234567890",
            sandbox=True
        )

        masked_data = config.mask_sensitive_data()
        
        # Check that sensitive data is masked properly
        assert "test...7890" in masked_data["client_id"]
        assert "test...7890" in masked_data["client_secret"]
        assert masked_data["sandbox"] is True  # Non-sensitive data unchanged

    def test_repr_includes_masked_credentials(self):
        """Test __repr__ includes masked credentials."""
        config = PayPalConfig(
            client_id="long_client_id_1234567890",
            client_secret="long_client_secret_1234567890",
            sandbox=True
        )

        repr_str = repr(config)
        
        # Should contain masked credentials
        assert "long...7890" in repr_str
        assert "PayPalConfig" in repr_str
        assert "sandbox" in repr_str


class TestPayPalConfigAdvancedFeatures:
    """Test advanced configuration features."""

    def test_to_dict_with_include_sensitive_false(self):
        """Test to_dict excludes sensitive data when requested."""
        config = PayPalConfig(
            client_id="test_client_id_1234567890",
            client_secret="test_client_secret_1234567890",
            sandbox=True,
            brand_name="Test Brand"
        )
        
        config_dict = config.to_dict(include_sensitive=False)
        
        # Should exclude sensitive data (keys won't exist due to None removal)
        assert "client_id" not in config_dict
        assert "client_secret" not in config_dict
        # Should include non-sensitive data
        assert config_dict["sandbox"] is True
        assert config_dict["brand_name"] == "Test Brand"

    def test_mask_sensitive_data_with_none_values(self):
        """Test mask_sensitive_data handles None values properly."""
        config = PayPalConfig(
            client_id="test_client_id_1234567890",
            client_secret="test_client_secret_1234567890"
        )
        
        # Test with config that has None values for optional fields
        masked_data = config.mask_sensitive_data()
        
        # Should handle None values gracefully
        assert "test...7890" in masked_data["client_id"]
        assert "test...7890" in masked_data["client_secret"]
        assert "return_url" not in masked_data or masked_data["return_url"] is None


class TestPayPalConfigValidationComprehensive:
    """Comprehensive validation tests to improve coverage."""
    
    def test_webhook_url_private_network_validation(self):
        """Test webhook URL validation rejects private network addresses."""
        # Test private network ranges that should be rejected
        private_networks = [
            "http://192.168.1.1/webhook",
            "https://10.0.0.1/webhook", 
            "https://172.16.0.1/webhook"
        ]
        
        for webhook_url in private_networks:
            with pytest.raises(PayPalConfigError, match="cannot use private network addresses"):
                PayPalConfig(
                    client_id="test_client_id_1234567890",
                    client_secret="test_client_secret_1234567890",
                    webhook_url=webhook_url
                )

    def test_webhook_url_localhost_validation(self):
        """Test webhook URL validation rejects localhost addresses."""
        localhost_urls = [
            "https://localhost/webhook",
            "https://127.0.0.1/webhook",
            "https://0.0.0.0/webhook"
        ]
        
        for webhook_url in localhost_urls:
            with pytest.raises(PayPalConfigError, match="cannot use localhost or local IP addresses"):
                PayPalConfig(
                    client_id="test_client_id_1234567890",
                    client_secret="test_client_secret_1234567890",
                    webhook_url=webhook_url
                )

    def test_url_validation_exception_handling(self):
        """Test URL validation handles malformed URLs with exception handling."""
        with pytest.raises(PayPalConfigError, match="Invalid return_url"):
            PayPalConfig(
                client_id="test_client_id_1234567890",
                client_secret="test_client_secret_1234567890",
                return_url="not-a-valid-url-format"
            )

    def test_https_enforcement_in_production(self):
        """Test HTTPS enforcement in production environment."""
        with pytest.raises(PayPalConfigError, match="must use HTTPS in production"):
            PayPalConfig(
                client_id="test_client_id_1234567890",
                client_secret="test_client_secret_1234567890",
                sandbox=False,  # Production mode
                return_url="http://example.com/return"  # HTTP not allowed in prod
            )

    def test_from_env_with_invalid_numeric_values(self):
        """Test from_env with invalid timeout and retry values."""
        import os
        
        # Store original values
        original_client_id = os.environ.get("PAYPAL_CLIENT_ID")
        original_client_secret = os.environ.get("PAYPAL_CLIENT_SECRET")
        original_timeout = os.environ.get("PAYPAL_TIMEOUT")
        
        try:
            os.environ["PAYPAL_CLIENT_ID"] = "test_client_id_1234567890"
            os.environ["PAYPAL_CLIENT_SECRET"] = "test_client_secret_1234567890"
            os.environ["PAYPAL_TIMEOUT"] = "invalid_number"
            
            with pytest.raises(PayPalConfigError, match="PAYPAL_TIMEOUT must be a valid integer"):
                PayPalConfig.from_env(load_dotenv=False)
                
        finally:
            # Restore original values
            if original_client_id is not None:
                os.environ["PAYPAL_CLIENT_ID"] = original_client_id
            elif "PAYPAL_CLIENT_ID" in os.environ:
                del os.environ["PAYPAL_CLIENT_ID"]
                
            if original_client_secret is not None:
                os.environ["PAYPAL_CLIENT_SECRET"] = original_client_secret
            elif "PAYPAL_CLIENT_SECRET" in os.environ:
                del os.environ["PAYPAL_CLIENT_SECRET"]
                
            if original_timeout is not None:
                os.environ["PAYPAL_TIMEOUT"] = original_timeout
            elif "PAYPAL_TIMEOUT" in os.environ:
                del os.environ["PAYPAL_TIMEOUT"]

    def test_from_env_with_invalid_amount_values(self):
        """Test from_env with invalid amount values."""
        import os
        
        # Store original values
        original_client_id = os.environ.get("PAYPAL_CLIENT_ID")
        original_client_secret = os.environ.get("PAYPAL_CLIENT_SECRET")
        original_min_amount = os.environ.get("PAYPAL_MIN_AMOUNT")
        
        try:
            os.environ["PAYPAL_CLIENT_ID"] = "test_client_id_1234567890"
            os.environ["PAYPAL_CLIENT_SECRET"] = "test_client_secret_1234567890"
            os.environ["PAYPAL_MIN_AMOUNT"] = "not_a_number"
            
            with pytest.raises(PayPalConfigError, match="PAYPAL_MIN_AMOUNT and PAYPAL_MAX_AMOUNT must be valid numbers"):
                PayPalConfig.from_env(load_dotenv=False)
                
        finally:
            # Restore original values
            if original_client_id is not None:
                os.environ["PAYPAL_CLIENT_ID"] = original_client_id
            elif "PAYPAL_CLIENT_ID" in os.environ:
                del os.environ["PAYPAL_CLIENT_ID"]
                
            if original_client_secret is not None:
                os.environ["PAYPAL_CLIENT_SECRET"] = original_client_secret
            elif "PAYPAL_CLIENT_SECRET" in os.environ:
                del os.environ["PAYPAL_CLIENT_SECRET"]
                
            if original_min_amount is not None:
                os.environ["PAYPAL_MIN_AMOUNT"] = original_min_amount
            elif "PAYPAL_MIN_AMOUNT" in os.environ:
                del os.environ["PAYPAL_MIN_AMOUNT"]

    def test_from_env_with_invalid_max_retries_value(self):
        """Test from_env with invalid max_retries value."""
        import os
        
        # Store original values
        original_client_id = os.environ.get("PAYPAL_CLIENT_ID")
        original_client_secret = os.environ.get("PAYPAL_CLIENT_SECRET")
        original_max_retries = os.environ.get("PAYPAL_MAX_RETRIES")
        
        try:
            os.environ["PAYPAL_CLIENT_ID"] = "test_client_id_1234567890"
            os.environ["PAYPAL_CLIENT_SECRET"] = "test_client_secret_1234567890"
            os.environ["PAYPAL_MAX_RETRIES"] = "not_a_number"
            
            with pytest.raises(PayPalConfigError, match="PAYPAL_MAX_RETRIES must be a valid integer"):
                PayPalConfig.from_env(load_dotenv=False)
                
        finally:
            # Restore original values
            if original_client_id is not None:
                os.environ["PAYPAL_CLIENT_ID"] = original_client_id
            elif "PAYPAL_CLIENT_ID" in os.environ:
                del os.environ["PAYPAL_CLIENT_ID"]
                
            if original_client_secret is not None:
                os.environ["PAYPAL_CLIENT_SECRET"] = original_client_secret
            elif "PAYPAL_CLIENT_SECRET" in os.environ:
                del os.environ["PAYPAL_CLIENT_SECRET"]
                
            if original_max_retries is not None:
                os.environ["PAYPAL_MAX_RETRIES"] = original_max_retries
            elif "PAYPAL_MAX_RETRIES" in os.environ:
                del os.environ["PAYPAL_MAX_RETRIES"]

    def test_invalid_url_schemes(self):
        """Test URL validation rejects invalid schemes."""
        with pytest.raises(PayPalConfigError, match="must use HTTP or HTTPS"):
            PayPalConfig(
                client_id="test_client_id_1234567890",
                client_secret="test_client_secret_1234567890",
                return_url="ftp://example.com/return"  # FTP not allowed
            )


if __name__ == "__main__":
    pytest.main([__file__])