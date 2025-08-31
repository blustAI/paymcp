"""
Unit tests for PayPal validator.

This module contains comprehensive unit tests for the PayPalValidator class,
covering all validation functionality including amounts, currencies, descriptions,
URLs, and business rules.
"""

import pytest
from decimal import Decimal

from paymcp.providers.paypal.validator import PayPalValidator, PayPalValidationError


class TestPayPalValidator:
    """Test the PayPal validator implementation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = PayPalValidator()
    
    def test_validate_amount_valid(self):
        """Test validation of valid amounts."""
        # Valid amounts
        valid_amounts = [0.01, 1.0, 10.50, 100.99, 999.99, 1000.0]
        
        for amount in valid_amounts:
            # Should not raise exception
            self.validator.validate_amount(amount, "USD")
    
    def test_validate_amount_invalid(self):
        """Test validation of invalid amounts."""
        # Invalid amounts
        invalid_amounts = [
            0.0,        # Zero
            -1.0,       # Negative
            0.001,      # Too small (less than 0.01)
            10000.01,   # Too large
            float('inf'),  # Infinity
            float('nan')   # NaN
        ]
        
        for amount in invalid_amounts:
            with pytest.raises(PayPalValidationError):
                self.validator.validate_amount(amount, "USD")
    
    def test_validate_amount_edge_cases(self):
        """Test amount validation edge cases."""
        # Boundary values
        self.validator.validate_amount(0.01, "USD")  # Minimum valid
        self.validator.validate_amount(10000.0, "USD")  # Maximum valid
        
        with pytest.raises(PayPalValidationError):
            self.validator.validate_amount(0.009, "USD")  # Just below minimum
        
        with pytest.raises(PayPalValidationError):
            self.validator.validate_amount(10000.01, "USD")  # Just above maximum
    
    def test_validate_currency_valid(self):
        """Test validation of valid currencies."""
        valid_currencies = [
            "USD", "EUR", "GBP", "CAD", "AUD", "JPY", "CHF", "SEK", "NOK", "DKK",
            "PLN", "CZK", "HUF", "ILS", "MXN", "BRL", "SGD", "HKD", "TWD", "THB",
            "MYR", "PHP", "INR", "NZD", "RUB"
        ]
        
        for currency in valid_currencies:
            # Should not raise exception
            self.validator.validate_currency(currency)
    
    def test_validate_currency_invalid(self):
        """Test validation of invalid currencies."""
        invalid_currencies = [
            "INVALID",  # Not supported
            "123",      # Numeric
            "",         # Empty
            None,       # None
            "US",       # Too short
            "USDD"      # Too long
        ]
        
        for currency in invalid_currencies:
            with pytest.raises(PayPalValidationError):
                self.validator.validate_currency(currency)
    
    def test_validate_description_valid(self):
        """Test validation of valid descriptions."""
        valid_descriptions = [
            "Test payment",
            "A" * 127,  # Maximum length
            "Payment with special chars: áéíóú",
            "Numbers 123 and symbols !@#",
            "   Trimmed spaces   "  # Should be trimmed
        ]
        
        for description in valid_descriptions:
            # Should not raise exception
            self.validator.validate_description(description)
    
    def test_validate_description_invalid(self):
        """Test validation of invalid descriptions."""
        invalid_descriptions = [
            "",           # Empty
            "   ",        # Whitespace only
            None,         # None
            "A" * 128,    # Too long
            "\n\t\r"      # Only control characters
        ]
        
        for description in invalid_descriptions:
            with pytest.raises(PayPalValidationError):
                self.validator.validate_description(description)
    
    def test_validate_url_valid(self):
        """Test validation of valid URLs."""
        valid_urls = [
            "https://example.com",
            "https://www.example.com/path",
            "https://example.com:8080/path?query=value",
            "https://sub.domain.example.com/complex/path?a=1&b=2#fragment"
        ]
        
        for url in valid_urls:
            # Should not raise exception
            self.validator.validate_url(url)
    
    def test_validate_url_invalid(self):
        """Test validation of invalid URLs."""
        invalid_urls = [
            "http://example.com",    # HTTP not allowed
            "ftp://example.com",     # Wrong scheme
            "example.com",           # Missing scheme
            "",                      # Empty
            None,                    # None
            "https://",              # Incomplete
            "not-a-url",            # Invalid format
            "https:// invalid.com"   # Spaces not allowed
        ]
        
        for url in invalid_urls:
            with pytest.raises(PayPalValidationError):
                self.validator.validate_url(url)
    
    def test_validate_payment_id_valid(self):
        """Test validation of valid payment IDs."""
        valid_payment_ids = [
            "PAYID-ABCD123",
            "12345678901234567890",
            "PAY-1AB23456CD789012E",
            "ORDER-ABC123DEF456"
        ]
        
        for payment_id in valid_payment_ids:
            # Should not raise exception
            self.validator.validate_payment_id(payment_id)
    
    def test_validate_payment_id_invalid(self):
        """Test validation of invalid payment IDs."""
        invalid_payment_ids = [
            "",           # Empty
            None,         # None
            "   ",        # Whitespace only
            "ABC",        # Too short
            "A" * 101,    # Too long
            "INVALID ID", # Contains spaces
            "123\n456"    # Contains newline
        ]
        
        for payment_id in invalid_payment_ids:
            with pytest.raises(PayPalValidationError):
                self.validator.validate_payment_id(payment_id)
    
    def test_validate_client_credentials_valid(self):
        """Test validation of valid client credentials."""
        valid_credentials = [
            ("client_123", "secret_456"),
            ("AVeryLongClientIdWith123Numbers", "ASecretKeyThatIsAlsoVeryLong"),
            ("ABC-123_DEF", "XYZ-789_GHI")
        ]
        
        for client_id, client_secret in valid_credentials:
            # Should not raise exception
            self.validator.validate_client_credentials(client_id, client_secret)
    
    def test_validate_client_credentials_invalid(self):
        """Test validation of invalid client credentials."""
        invalid_credentials = [
            ("", "secret"),           # Empty client ID
            ("client", ""),           # Empty secret
            (None, "secret"),         # None client ID
            ("client", None),         # None secret
            ("   ", "secret"),        # Whitespace only client ID
            ("client", "   "),        # Whitespace only secret
            ("cli", "secret"),        # Client ID too short
            ("client", "sec"),        # Secret too short
            ("A" * 201, "secret"),    # Client ID too long
            ("client", "A" * 201)     # Secret too long
        ]
        
        for client_id, client_secret in invalid_credentials:
            with pytest.raises(PayPalValidationError):
                self.validator.validate_client_credentials(client_id, client_secret)
    
    def test_validate_webhook_url(self):
        """Test webhook URL validation with specific requirements."""
        # Valid webhook URLs
        valid_webhook_urls = [
            "https://api.example.com/webhook",
            "https://secure-domain.com:443/paypal/webhook",
            "https://app.example.org/payments/paypal/notification"
        ]
        
        for url in valid_webhook_urls:
            self.validator.validate_webhook_url(url)
    
    def test_validate_webhook_url_invalid(self):
        """Test invalid webhook URLs."""
        invalid_webhook_urls = [
            "http://example.com/webhook",  # HTTP not allowed for webhooks
            "https://localhost/webhook",   # Localhost not allowed
            "https://127.0.0.1/webhook",  # IP address not allowed
            "https://192.168.1.1/webhook" # Private IP not allowed
        ]
        
        for url in invalid_webhook_urls:
            with pytest.raises(PayPalValidationError):
                self.validator.validate_webhook_url(url)
    
    def test_validate_brand_name(self):
        """Test brand name validation."""
        # Valid brand names
        valid_brands = [
            "My Store",
            "Example Corp",
            "Store-123",
            "A" * 22  # Maximum length
        ]
        
        for brand in valid_brands:
            self.validator.validate_brand_name(brand)
        
        # Invalid brand names
        invalid_brands = [
            "",           # Empty
            "   ",        # Whitespace only
            "A" * 23,     # Too long
            None          # None
        ]
        
        for brand in invalid_brands:
            with pytest.raises(PayPalValidationError):
                self.validator.validate_brand_name(brand)
    
    def test_validate_locale(self):
        """Test locale validation."""
        # Valid locales
        valid_locales = [
            "en-US", "en-GB", "fr-FR", "de-DE", "es-ES", "it-IT",
            "pt-BR", "zh-CN", "ja-JP", "ko-KR", "ru-RU"
        ]
        
        for locale in valid_locales:
            self.validator.validate_locale(locale)
        
        # Invalid locales
        invalid_locales = [
            "en",         # Missing country
            "EN-US",      # Wrong case
            "en_US",      # Wrong separator
            "english",    # Full name
            "invalid",    # Not a locale
            ""            # Empty
        ]
        
        for locale in invalid_locales:
            with pytest.raises(PayPalValidationError):
                self.validator.validate_locale(locale)


class TestPayPalValidatorBusinessRules:
    """Test business rule validations."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = PayPalValidator()
    
    def test_currency_amount_combinations(self):
        """Test currency-specific amount validations."""
        # JPY should not have decimal places
        with pytest.raises(PayPalValidationError):
            self.validator.validate_currency_amount_combination("JPY", 100.50)
        
        # JPY with whole number should be valid
        self.validator.validate_currency_amount_combination("JPY", 100.0)
        
        # USD with decimals should be valid
        self.validator.validate_currency_amount_combination("USD", 100.50)
    
    def test_amount_precision(self):
        """Test amount precision validation."""
        # Valid precision (2 decimal places max for most currencies)
        valid_amounts = [1.0, 1.1, 1.12]
        for amount in valid_amounts:
            self.validator.validate_amount_precision(amount, "USD")
        
        # Invalid precision (more than 2 decimal places)
        with pytest.raises(PayPalValidationError):
            self.validator.validate_amount_precision(1.123, "USD")
    
    def test_minimum_amounts_by_currency(self):
        """Test currency-specific minimum amounts."""
        # Different currencies have different minimums
        test_cases = [
            ("USD", 0.01, True),   # Valid minimum
            ("USD", 0.005, False), # Below minimum
            ("JPY", 1.0, True),    # Valid minimum for JPY
            ("JPY", 0.5, False)    # Below minimum for JPY
        ]
        
        for currency, amount, should_be_valid in test_cases:
            if should_be_valid:
                self.validator.validate_minimum_amount(amount, currency)
            else:
                with pytest.raises(PayPalValidationError):
                    self.validator.validate_minimum_amount(amount, currency)
    
    def test_description_content_rules(self):
        """Test description content validation."""
        # Valid descriptions
        valid_descriptions = [
            "Product purchase",
            "Service payment for consulting",
            "Invoice #12345 payment"
        ]
        
        for desc in valid_descriptions:
            self.validator.validate_description_content(desc)
        
        # Invalid descriptions (potentially problematic content)
        invalid_descriptions = [
            "Payment for illegal goods",  # Suspicious content
            "Drug purchase",              # Prohibited
            "Weapons sale"                # Prohibited
        ]
        
        for desc in invalid_descriptions:
            with pytest.raises(PayPalValidationError):
                self.validator.validate_description_content(desc)


class TestPayPalValidatorErrorMessages:
    """Test that error messages are informative."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = PayPalValidator()
    
    def test_amount_error_messages(self):
        """Test that amount validation errors have clear messages."""
        try:
            self.validator.validate_amount(-10.0, "USD")
        except PayPalValidationError as e:
            assert "negative" in str(e).lower() or "positive" in str(e).lower()
        
        try:
            self.validator.validate_amount(0.0, "USD")
        except PayPalValidationError as e:
            assert "zero" in str(e).lower() or "greater" in str(e).lower()
    
    def test_currency_error_messages(self):
        """Test that currency validation errors have clear messages."""
        try:
            self.validator.validate_currency("INVALID")
        except PayPalValidationError as e:
            assert "currency" in str(e).lower()
            assert "supported" in str(e).lower() or "valid" in str(e).lower()
    
    def test_url_error_messages(self):
        """Test that URL validation errors have clear messages."""
        try:
            self.validator.validate_url("http://example.com")
        except PayPalValidationError as e:
            assert "https" in str(e).lower()
    
    def test_description_error_messages(self):
        """Test that description validation errors have clear messages."""
        try:
            self.validator.validate_description("")
        except PayPalValidationError as e:
            assert "empty" in str(e).lower() or "required" in str(e).lower()
        
        try:
            self.validator.validate_description("A" * 200)
        except PayPalValidationError as e:
            assert "length" in str(e).lower() or "long" in str(e).lower()


class TestPayPalValidatorAdvancedScenarios:
    """Test advanced validation scenarios."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.validator = PayPalValidator()

    def test_validate_complex_currency_scenarios(self):
        """Test complex currency validation scenarios."""
        validator = PayPalValidator()
        
        # Test valid currencies (case insensitive)
        validator.validate_currency("USD")
        validator.validate_currency("EUR")
        validator.validate_currency("GBP")
        
        # Test invalid currencies  
        with pytest.raises(PayPalValidationError):
            validator.validate_currency("INVALID")

    def test_amount_precision_validation(self):
        """Test amount precision validation."""
        validator = PayPalValidator()
        
        # Test valid amounts within currency-specific limits
        validator.validate_amount(10.50, "USD")
        validator.validate_amount(0.01, "EUR") 
        validator.validate_amount(7999.99, "GBP")  # Within GBP limit of 8000
        
        # Test invalid amounts
        with pytest.raises(PayPalValidationError):
            validator.validate_amount(-1.0, "USD")  # Negative


class TestPayPalValidatorInitialization:
    """Test PayPal validator initialization and configuration."""

    def test_default_initialization(self):
        """Test default validator initialization."""
        validator = PayPalValidator()
        
        assert validator.min_amount == 0.01
        assert validator.max_amount == 10000.00
        assert len(validator.supported_currencies) > 20  # Should have many currencies
        assert "USD" in validator.supported_currencies
        assert "EUR" in validator.supported_currencies

    def test_custom_initialization(self):
        """Test validator with custom configuration."""
        validator = PayPalValidator(
            supported_currencies=["USD", "EUR", "GBP"],
            min_amount=1.00,
            max_amount=5000.00
        )
        
        assert validator.min_amount == 1.00
        assert validator.max_amount == 5000.00
        assert validator.supported_currencies == {"USD", "EUR", "GBP"}

    def test_invalid_configuration(self):
        """Test validator with invalid configuration."""
        # Test unsupported currency
        with pytest.raises(ValueError, match="Unsupported currencies"):
            PayPalValidator(supported_currencies=["INVALID", "USD"])
        
        # Test invalid min amount
        with pytest.raises(ValueError, match="min_amount must be positive"):
            PayPalValidator(min_amount=-1.0)
        
        # Test invalid max amount
        with pytest.raises(ValueError, match="max_amount must be greater than min_amount"):
            PayPalValidator(min_amount=100.0, max_amount=50.0)


class TestPayPalValidatorAmountValidation:
    """Test comprehensive amount validation."""

    def test_validate_amount_with_different_types(self):
        """Test amount validation with different input types."""
        validator = PayPalValidator()
        
        # Test different input types
        result = validator.validate_amount(10, "USD")
        assert result == Decimal("10")
        
        result = validator.validate_amount(10.50, "USD")
        assert result == Decimal("10.50")
        
        result = validator.validate_amount("15.99", "USD")
        assert result == Decimal("15.99")
        
        result = validator.validate_amount(Decimal("20.00"), "USD")
        assert result == Decimal("20.00")

    def test_validate_amount_zero_decimal_currencies(self):
        """Test amount validation for zero decimal currencies."""
        validator = PayPalValidator()
        
        # JPY should not allow decimals
        result = validator.validate_amount(100, "JPY")
        assert result == Decimal("100")
        
        # Should reject decimal amounts for JPY
        with pytest.raises(PayPalValidationError):
            validator.validate_amount(100.50, "JPY")

    def test_validate_amount_edge_cases(self):
        """Test amount validation edge cases."""
        validator = PayPalValidator()
        
        # Test minimum amount
        result = validator.validate_amount(0.01, "USD")
        assert result == Decimal("0.01")
        
        # Test near maximum amount
        result = validator.validate_amount(9999.99, "USD")  # Within USD limit of 10000
        assert result == Decimal("9999.99")
        
        # Test invalid string
        with pytest.raises(PayPalValidationError):
            validator.validate_amount("not_a_number", "USD")
        
        # Test None
        with pytest.raises(PayPalValidationError):
            validator.validate_amount(None, "USD")


class TestPayPalValidatorCurrencyValidation:
    """Test comprehensive currency validation."""

    def test_validate_currency_valid_codes(self):
        """Test validation of valid currency codes."""
        validator = PayPalValidator()
        
        valid_currencies = ["USD", "EUR", "GBP", "JPY", "CAD", "AUD"]
        for currency in valid_currencies:
            result = validator.validate_currency(currency)
            assert result == currency.upper()

    def test_validate_currency_case_insensitive(self):
        """Test currency validation is case insensitive."""
        validator = PayPalValidator()
        
        assert validator.validate_currency("usd") == "USD"
        assert validator.validate_currency("eur") == "EUR"
        assert validator.validate_currency("Gbp") == "GBP"

    def test_validate_currency_invalid_codes(self):
        """Test validation of invalid currency codes."""
        validator = PayPalValidator()
        
        invalid_currencies = ["", "US", "EURO", "BTC", "XYZ", None]
        for currency in invalid_currencies:
            with pytest.raises(PayPalValidationError):
                validator.validate_currency(currency)

    def test_get_currency_info(self):
        """Test getting currency information."""
        validator = PayPalValidator()
        
        usd_info = validator.get_currency_info("USD")
        assert usd_info["code"] == "USD"
        assert usd_info["min"] == 0.01
        assert usd_info["max"] == 10000.00
        assert usd_info["decimal_places"] == 2
        assert usd_info["supported"] is True

        jpy_info = validator.get_currency_info("JPY")
        assert jpy_info["code"] == "JPY"
        assert jpy_info["decimal_places"] == 0
        assert jpy_info["min"] == 1
        assert jpy_info["max"] == 1000000


class TestPayPalValidatorDescriptionValidation:
    """Test comprehensive description validation."""

    def test_validate_description_valid(self):
        """Test validation of valid descriptions."""
        validator = PayPalValidator()
        
        valid_descriptions = [
            "Payment for services",
            "Order #12345",
            "Subscription renewal",
            "A" * 127  # Maximum length
        ]
        
        for desc in valid_descriptions:
            result = validator.validate_description(desc)
            assert result == desc

    def test_validate_description_invalid(self):
        """Test validation of invalid descriptions."""
        validator = PayPalValidator()
        
        # Empty description
        with pytest.raises(PayPalValidationError):
            validator.validate_description("")
        
        # Too long description
        with pytest.raises(PayPalValidationError):
            validator.validate_description("A" * 128)
        
        # None description
        with pytest.raises(PayPalValidationError):
            validator.validate_description(None)
        
        # Whitespace only
        with pytest.raises(PayPalValidationError):
            validator.validate_description("   ")

    def test_validate_description_content_filtering(self):
        """Test description content filtering."""
        validator = PayPalValidator()
        
        # Test suspicious content detection - these should raise errors
        suspicious_descriptions = [
            "<script>alert('xss')</script>",  # Contains forbidden <, >
            "Test with \"quotes\" and 'apostrophes'",  # Contains forbidden quotes
            "Line\nbreak",  # Contains newline
            "Tab\there"  # Contains tab
        ]
        
        for desc in suspicious_descriptions:
            with pytest.raises(PayPalValidationError):
                validator.validate_description_content(desc)


class TestPayPalValidatorEmailValidation:
    """Test email validation."""

    def test_validate_email_valid(self):
        """Test validation of valid emails."""
        validator = PayPalValidator()
        
        valid_emails = [
            "user@example.com",
            "test.email@domain.co.uk",
            "user+tag@example.org",
            "123@numeric-domain.com"
        ]
        
        for email in valid_emails:
            result = validator.validate_email(email)
            assert result == email.lower()

    def test_validate_email_invalid(self):
        """Test validation of invalid emails."""
        validator = PayPalValidator()
        
        invalid_emails = [
            "",
            "invalid",
            "@domain.com",
            "user@",
            "user@domain",
            "user space@domain.com",
            None
        ]
        
        for email in invalid_emails:
            with pytest.raises(PayPalValidationError):
                validator.validate_email(email)


class TestPayPalValidatorURLValidation:
    """Test URL validation."""

    def test_validate_url_valid(self):
        """Test validation of valid URLs."""
        validator = PayPalValidator()
        
        # PayPal requires HTTPS URLs only
        valid_urls = [
            "https://example.com",
            "https://subdomain.example.co.uk/path?param=value",
            "https://example.com:9090/webhook",
            "https://api.mysite.com/callback"
        ]
        
        for url in valid_urls:
            result = validator.validate_url(url)
            assert result == url

    def test_validate_url_invalid(self):
        """Test validation of invalid URLs."""
        validator = PayPalValidator()
        
        invalid_urls = [
            "",
            "not-a-url",
            "ftp://example.com",  # Wrong protocol
            "https://",  # Incomplete
            None
        ]
        
        for url in invalid_urls:
            with pytest.raises(PayPalValidationError):
                validator.validate_url(url)


class TestPayPalValidatorPaymentIDValidation:
    """Test payment ID validation."""

    def test_validate_payment_id_valid(self):
        """Test validation of valid payment IDs."""
        validator = PayPalValidator()
        
        valid_ids = [
            "PAY-1AB23456CD789012E",
            "PAYID-L3T4ABC123456789",
            "4RR959492F879224N",
            "8FA78831EP1632230"
        ]
        
        for payment_id in valid_ids:
            result = validator.validate_payment_id(payment_id)
            assert result == payment_id

    def test_validate_payment_id_invalid(self):
        """Test validation of invalid payment IDs."""
        validator = PayPalValidator()
        
        # Only empty string and None should fail
        invalid_ids = [
            "",    # Empty string
            None   # None value
        ]
        
        for payment_id in invalid_ids:
            with pytest.raises(PayPalValidationError):
                validator.validate_payment_id(payment_id)


class TestPayPalValidatorClientCredentialsValidation:
    """Test client credentials validation."""

    def test_validate_client_credentials_valid(self):
        """Test validation of valid client credentials."""
        validator = PayPalValidator()
        
        client_id = "test_client_id_1234567890"
        client_secret = "test_client_secret_1234567890"
        
        result = validator.validate_client_credentials(client_id, client_secret)
        assert result == (client_id, client_secret)

    def test_validate_client_credentials_invalid(self):
        """Test validation of invalid client credentials."""
        validator = PayPalValidator()
        
        # Only empty/None credentials should fail
        
        # Empty credentials
        with pytest.raises(PayPalValidationError):
            validator.validate_client_credentials("", "valid_secret_1234567890")
        
        with pytest.raises(PayPalValidationError):
            validator.validate_client_credentials("valid_id_1234567890", "")
        
        # None credentials
        with pytest.raises(PayPalValidationError):
            validator.validate_client_credentials(None, "valid_secret")
        
        with pytest.raises(PayPalValidationError):
            validator.validate_client_credentials("valid_id", None)


class TestPayPalValidatorBrandNameValidation:
    """Test brand name validation."""

    def test_validate_brand_name_valid(self):
        """Test validation of valid brand names."""
        validator = PayPalValidator()
        
        valid_names = [
            "My Company",
            "Test-Store_123", 
            "Company & Co.",
            "A" * 22  # Maximum length
        ]
        
        for name in valid_names:
            result = validator.validate_brand_name(name)
            assert result == name

    def test_validate_brand_name_invalid(self):
        """Test validation of invalid brand names."""
        validator = PayPalValidator()
        
        # Empty name
        with pytest.raises(PayPalValidationError):
            validator.validate_brand_name("")
        
        # Too long name
        with pytest.raises(PayPalValidationError):
            validator.validate_brand_name("A" * 23)
        
        # None name
        with pytest.raises(PayPalValidationError):
            validator.validate_brand_name(None)


class TestPayPalValidatorLocaleValidation:
    """Test locale validation."""

    def test_validate_locale_valid(self):
        """Test validation of valid locales."""
        validator = PayPalValidator()
        
        # PayPal expects dash format (en-US), not underscore (en_US)
        valid_locales = [
            "en-US", "es-ES", "fr-FR", "de-DE",
            "it-IT", "pt-BR", "zh-CN", "ja-JP"
        ]
        
        for locale in valid_locales:
            result = validator.validate_locale(locale)
            assert result == locale

    def test_validate_locale_invalid(self):
        """Test validation of invalid locales."""
        validator = PayPalValidator()
        
        invalid_locales = [
            "",
            "en",  # Missing country
            "EN-US",  # Wrong case
            "en_US",  # Wrong separator (underscore instead of dash)
            "invalid",
            None
        ]
        
        for locale in invalid_locales:
            with pytest.raises(PayPalValidationError):
                validator.validate_locale(locale)


class TestPayPalValidatorCompletePaymentValidation:
    """Test complete payment validation."""

    def test_validate_complete_payment_basic(self):
        """Test basic complete payment validation."""
        validator = PayPalValidator()
        
        # Test minimal valid payment
        result = validator.validate_complete_payment(
            amount=25.99,
            currency="USD", 
            description="Test payment"
        )
        
        assert result["amount"] == Decimal("25.99")
        assert result["currency"] == "USD"
        assert result["description"] == "Test payment"

    def test_validate_complete_payment_invalid(self):
        """Test validation of complete invalid payment."""
        validator = PayPalValidator()
        
        # Invalid amount
        with pytest.raises(PayPalValidationError):
            validator.validate_complete_payment(
                amount=-10.00,
                currency="USD",
                description="Test payment"
            )
        
        # Invalid currency
        with pytest.raises(PayPalValidationError):
            validator.validate_complete_payment(
                amount=10.00,
                currency="INVALID",
                description="Test payment"
            )


class TestPayPalValidatorPhoneValidation:
    """Test phone number validation."""

    def test_validate_phone_valid(self):
        """Test validation of valid phone numbers."""
        validator = PayPalValidator()
        
        valid_phones = [
            "+1-555-123-4567",
            "555-123-4567",
            "+44-20-7123-4567",
            "+33-1-23-45-67-89"
        ]
        
        for phone in valid_phones:
            result = validator.validate_phone(phone)
            # Should return a cleaned version
            assert result is not None

    def test_validate_phone_invalid(self):
        """Test validation of invalid phone numbers."""
        validator = PayPalValidator()
        
        invalid_phones = [
            "",
            "123",  # Too short
            "invalid-phone",
            None
        ]
        
        for phone in invalid_phones:
            with pytest.raises(PayPalValidationError):
                validator.validate_phone(phone)


class TestPayPalValidatorOrderIDValidation:
    """Test order ID validation."""

    def test_validate_order_id_valid(self):
        """Test validation of valid order IDs."""
        validator = PayPalValidator()
        
        # PayPal expects specific formats: 17 chars or UUID format
        valid_order_ids = [
            "1AB2C3D4E5F6G7H8I",  # 17 characters alphanumeric
            "9JK0L1M2N3O4P5Q6R",  # 17 characters alphanumeric  
            "12345678-1234-1234-1234-123456789012"  # UUID format
        ]
        
        for order_id in valid_order_ids:
            result = validator.validate_order_id(order_id)
            assert result == order_id

    def test_validate_order_id_invalid(self):
        """Test validation of invalid order IDs."""
        validator = PayPalValidator()
        
        invalid_order_ids = [
            "",
            "x",  # Too short
            None,
            "ORDER_" + "A" * 200  # Too long
        ]
        
        for order_id in invalid_order_ids:
            with pytest.raises(PayPalValidationError):
                validator.validate_order_id(order_id)


class TestPayPalValidatorReferenceIDValidation:
    """Test reference ID validation."""

    def test_validate_reference_id_valid(self):
        """Test validation of valid reference IDs."""
        validator = PayPalValidator()
        
        valid_ref_ids = [
            "REF-123456789",
            "INVOICE-ABC123",
            "12345-REF-67890"
        ]
        
        for ref_id in valid_ref_ids:
            result = validator.validate_reference_id(ref_id)
            assert result == ref_id

    def test_validate_reference_id_invalid(self):
        """Test validation of invalid reference IDs."""
        validator = PayPalValidator()
        
        # Only empty/None should fail
        invalid_ref_ids = [
            "",    # Empty string
            None   # None value
        ]
        
        for ref_id in invalid_ref_ids:
            with pytest.raises(PayPalValidationError):
                validator.validate_reference_id(ref_id)


class TestPayPalValidatorMetadataValidation:
    """Test metadata validation."""

    def test_validate_metadata_valid(self):
        """Test validation of valid metadata."""
        validator = PayPalValidator()
        
        valid_metadata = [
            {"source": "web", "user_id": "123"},
            {"order_type": "subscription", "plan_id": "premium"},
            {"custom_field_1": "value1", "custom_field_2": "value2"}
        ]
        
        for metadata in valid_metadata:
            result = validator.validate_metadata(metadata)
            assert result == metadata

    def test_validate_metadata_invalid(self):
        """Test validation of invalid metadata."""
        validator = PayPalValidator()
        
        # Test with non-dict
        with pytest.raises(PayPalValidationError):
            validator.validate_metadata("not_a_dict")
        
        # Test with None
        result = validator.validate_metadata(None)
        assert result == {}  # Should return empty dict for None


class TestPayPalValidatorWebhookURLValidation:
    """Test webhook URL validation."""

    def test_validate_webhook_url_valid(self):
        """Test validation of valid webhook URLs."""
        validator = PayPalValidator()
        
        valid_urls = [
            "https://example.com/webhook",
            "https://api.mysite.com/paypal/webhook",
            "https://secure.domain.co.uk/callbacks/paypal"
        ]
        
        for url in valid_urls:
            result = validator.validate_webhook_url(url)
            assert result == url

    def test_validate_webhook_url_invalid(self):
        """Test validation of invalid webhook URLs."""
        validator = PayPalValidator()
        
        invalid_urls = [
            "http://insecure.com/webhook",  # HTTP not allowed
            "",
            "not-a-url",
            None
        ]
        
        for url in invalid_urls:
            with pytest.raises(PayPalValidationError):
                validator.validate_webhook_url(url)


class TestPayPalValidatorUtilityMethods:
    """Test utility methods."""

    def test_get_supported_currencies(self):
        """Test getting supported currencies."""
        validator = PayPalValidator()
        
        currencies = validator.get_supported_currencies()
        assert isinstance(currencies, set)
        assert len(currencies) > 20
        assert "USD" in currencies
        assert "EUR" in currencies

    def test_repr_method(self):
        """Test string representation."""
        validator = PayPalValidator()
        
        repr_str = repr(validator)
        assert "PayPalValidator" in repr_str
        assert str(len(validator.supported_currencies)) in repr_str


class TestPayPalValidatorEdgeCases:
    """Test edge cases to improve coverage."""

    def test_validate_amount_below_global_minimum(self):
        """Test amount validation when below global minimum."""
        validator = PayPalValidator(min_amount=5.0)  # Higher than default 0.01
        
        with pytest.raises(PayPalValidationError, match="below minimum 5.0"):
            validator.validate_amount(1.0, "USD")  # Below global min

    def test_validate_amount_below_currency_minimum(self):
        """Test amount validation when below currency-specific minimum."""
        validator = PayPalValidator(min_amount=0.001)  # Set global min very low
        
        # Test amount below currency-specific minimum for SEK (1.00 SEK minimum)
        with pytest.raises(PayPalValidationError, match="below PayPal minimum 1.0 SEK"):
            validator.validate_amount(0.50, "SEK")  # Below SEK minimum of 1.00

    def test_validate_currency_limit_check(self):
        """Test currency-specific limit validation."""
        validator = PayPalValidator()
        
        # Test exceeding currency-specific maximum for GBP (8000)
        with pytest.raises(PayPalValidationError, match="exceeds PayPal maximum 8000.0 GBP"):
            validator.validate_amount(9000.0, "GBP")

    def test_validate_description_empty_string(self):
        """Test description validation with empty string."""
        validator = PayPalValidator()
        
        # Should raise error for empty string
        with pytest.raises(PayPalValidationError, match="Description cannot be empty"):
            validator.validate_description("")

    def test_validate_order_id_empty_string(self):
        """Test order ID validation with empty string."""
        validator = PayPalValidator()
        
        # Should raise error for empty string
        with pytest.raises(PayPalValidationError, match="Order ID cannot be empty"):
            validator.validate_order_id("")

    def test_validate_metadata_none_value(self):
        """Test metadata validation with None value."""
        validator = PayPalValidator()
        
        # Should return empty dict for None
        result = validator.validate_metadata(None)
        assert result == {}

    def test_validate_currency_non_string_type(self):
        """Test currency validation with non-string type."""
        validator = PayPalValidator()
        
        # Test with integer instead of string
        with pytest.raises(PayPalValidationError, match="Currency must be a string, got int"):
            validator.validate_currency(123)

    def test_validate_currency_non_alpha(self):
        """Test currency validation with non-alphabetic characters."""
        validator = PayPalValidator()
        
        # Test with numeric characters
        with pytest.raises(PayPalValidationError, match="Currency code must contain only letters"):
            validator.validate_currency("US1")

    def test_validate_unsupported_currency(self):
        """Test currency validation with unsupported currency."""
        validator = PayPalValidator()
        
        # Test with unsupported but valid format currency
        with pytest.raises(PayPalValidationError, match="Currency 'XYZ' not supported by PayPal"):
            validator.validate_currency("XYZ")

    def test_validate_currency_configured_subset(self):
        """Test currency validation with configured currency subset."""
        # Create validator with only specific currencies configured
        validator = PayPalValidator(supported_currencies=["USD", "EUR"])
        
        # This should trigger the 'not configured' path since GBP isn't in the configured subset
        with pytest.raises(PayPalValidationError, match="Currency 'GBP' not configured for this provider"):
            validator.validate_currency("GBP")

    def test_validate_description_non_string_type(self):
        """Test description validation with non-string type."""
        validator = PayPalValidator()
        
        # Test with integer instead of string
        with pytest.raises(PayPalValidationError, match="Description must be a string, got int"):
            validator.validate_description(123)

    def test_validate_description_suspicious_content(self):
        """Test description validation rejects suspicious content."""
        validator = PayPalValidator()
        
        # Test with JavaScript scheme (no forbidden chars)
        with pytest.raises(PayPalValidationError, match="Description contains potentially unsafe content"):
            validator.validate_description("Payment javascript:alert")
        
        # Test with eval function call
        with pytest.raises(PayPalValidationError, match="Description contains potentially unsafe content"):
            validator.validate_description("Payment with eval(data)")

    def test_validate_order_id_non_string_type(self):
        """Test order ID validation with non-string type."""
        validator = PayPalValidator()
        
        # Test with integer instead of string
        with pytest.raises(PayPalValidationError, match="Order ID must be a string, got int"):
            validator.validate_order_id(12345)


if __name__ == "__main__":
    pytest.main([__file__])