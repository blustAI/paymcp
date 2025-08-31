"""
PayPal Payment Validator

This module provides comprehensive validation for PayPal payments,
including business rules, security checks, and PayPal-specific constraints.
"""

import re
from decimal import Decimal, InvalidOperation
from typing import Optional, List, Set
from datetime import datetime

# Define ValidationError locally since we removed abstractions


class PayPalValidationError(Exception):
    """PayPal validation error."""
    pass


# For backward compatibility
ValidationError = PayPalValidationError


class PayPalValidator:
    """
    Comprehensive PayPal payment validator.

    This class provides validation for all PayPal-specific payment parameters,
    business rules, and security constraints.
    """

    # PayPal supported currencies (as of 2024)
    SUPPORTED_CURRENCIES = {
        "AUD", "BRL", "CAD", "CHF", "CNY", "CZK", "DKK", "EUR", "GBP", "HKD",
        "HUF", "ILS", "INR", "JPY", "MXN", "MYR", "NOK", "NZD", "PHP", "PLN",
        "RUB", "SEK", "SGD", "THB", "TWD", "USD"
    }

    # Currencies with special decimal handling (no decimal places)
    ZERO_DECIMAL_CURRENCIES = {"JPY", "KRW", "TWD", "HUF", "CLP"}

    # PayPal amount limits (in USD equivalent)
    ABSOLUTE_MIN_AMOUNT = 0.01
    ABSOLUTE_MAX_AMOUNT = 10000.00

    # Currency-specific limits (in local currency)
    CURRENCY_LIMITS = {
        "USD": {"min": 0.01, "max": 10000.00},
        "EUR": {"min": 0.01, "max": 8500.00},
        "GBP": {"min": 0.01, "max": 8000.00},
        "CAD": {"min": 0.01, "max": 12000.00},
        "AUD": {"min": 0.01, "max": 12000.00},
        "JPY": {"min": 1, "max": 1000000},  # No decimal places
        "CHF": {"min": 0.01, "max": 9000.00},
        "SEK": {"min": 1.00, "max": 85000.00},
        "NOK": {"min": 1.00, "max": 85000.00},
        "DKK": {"min": 1.00, "max": 60000.00},
    }

    # Forbidden characters in descriptions
    FORBIDDEN_DESCRIPTION_CHARS = {'<', '>', '"', "'", '&', '\n', '\r', '\t'}

    # PayPal order ID pattern
    ORDER_ID_PATTERN = re.compile(r'^[A-Z0-9]{17}$|^[0-9A-Z]{8}-[0-9A-Z]{4}-[0-9A-Z]{4}-[0-9A-Z]{4}-[0-9A-Z]{12}$')

    def __init__(self, supported_currencies: Optional[List[str]] = None,
                 min_amount: float = ABSOLUTE_MIN_AMOUNT,
                 max_amount: float = ABSOLUTE_MAX_AMOUNT):
        """
        Initialize PayPal validator.

        Args:
            supported_currencies: List of supported currencies (defaults to all PayPal currencies)
            min_amount: Minimum allowed amount
            max_amount: Maximum allowed amount
        """
        self.supported_currencies = set(supported_currencies or self.SUPPORTED_CURRENCIES)
        self.min_amount = min_amount
        self.max_amount = max_amount

        # Validate configuration
        self._validate_configuration()

    def _validate_configuration(self):
        """Validate validator configuration."""
        unsupported = self.supported_currencies - self.SUPPORTED_CURRENCIES
        if unsupported:
            raise ValueError(f"Unsupported currencies: {unsupported}")

        if self.min_amount <= 0:
            raise ValueError("min_amount must be positive")

        if self.max_amount <= self.min_amount:
            raise ValueError("max_amount must be greater than min_amount")

    def validate_amount(self, amount, currency: str) -> Decimal:
        """
        Validate payment amount with PayPal-specific rules.

        Args:
            amount: Payment amount (int, float, str, or Decimal)
            currency: Currency code

        Returns:
            Validated amount as Decimal

        Raises:
            ValidationError: If amount is invalid
        """
        # Check for special float values first
        if isinstance(amount, float):
            import math
            if math.isnan(amount):
                raise ValidationError("Amount cannot be NaN")
            if math.isinf(amount):
                raise ValidationError("Amount cannot be infinity")

        # Convert to Decimal for precise handling
        try:
            if isinstance(amount, str):
                # Remove common formatting
                amount = amount.replace(',', '').replace(' ', '').strip()

            decimal_amount = Decimal(str(amount))
        except (InvalidOperation, ValueError) as e:
            raise ValidationError(f"Invalid amount format: {amount}") from e

        # Check if amount is positive
        if decimal_amount <= 0:
            raise ValidationError("Amount must be positive (greater than 0)")

        # Validate currency first
        currency = self.validate_currency(currency)

        # Check decimal places based on currency
        if currency in self.ZERO_DECIMAL_CURRENCIES:
            if decimal_amount % 1 != 0:
                raise ValidationError(f"Currency {currency} does not support decimal places")
        else:
            # Most currencies support up to 2 decimal places
            if decimal_amount.as_tuple().exponent < -2:
                raise ValidationError("Amount cannot have more than 2 decimal places")

        # Check against global limits
        float_amount = float(decimal_amount)
        if float_amount < self.min_amount:
            raise ValidationError(f"Amount {decimal_amount} below minimum {self.min_amount}")

        if float_amount > self.max_amount:
            raise ValidationError(f"Amount {decimal_amount} exceeds maximum {self.max_amount}")

        # Check against currency-specific limits
        currency_limit = self.CURRENCY_LIMITS.get(currency)
        if currency_limit:
            if float_amount < currency_limit["min"]:
                raise ValidationError(
                    f"Amount {decimal_amount} {currency} below PayPal minimum {currency_limit['min']} {currency}"
                )

            if float_amount > currency_limit["max"]:
                raise ValidationError(
                    f"Amount {decimal_amount} {currency} exceeds PayPal maximum {currency_limit['max']} {currency}"
                )

        return decimal_amount

    def validate_currency(self, currency: str) -> str:
        """
        Validate currency code.

        Args:
            currency: Currency code to validate

        Returns:
            Normalized currency code (uppercase)

        Raises:
            ValidationError: If currency is invalid
        """
        if not currency:
            raise ValidationError("Currency code cannot be empty")

        if not isinstance(currency, str):
            raise ValidationError(f"Currency must be a string, got {type(currency).__name__}")

        currency = currency.strip().upper()

        if len(currency) != 3:
            raise ValidationError(f"Currency code must be 3 characters, got: '{currency}'")

        if not currency.isalpha():
            raise ValidationError(f"Currency code must contain only letters: '{currency}'")

        if currency not in self.SUPPORTED_CURRENCIES:
            supported_list = ", ".join(sorted(self.SUPPORTED_CURRENCIES))
            raise ValidationError(
                f"Currency '{currency}' not supported by PayPal. "
                f"Supported currencies: {supported_list}"
            )

        if currency not in self.supported_currencies:
            configured_list = ", ".join(sorted(self.supported_currencies))
            raise ValidationError(
                f"Currency '{currency}' not configured for this provider. "
                f"Configured currencies: {configured_list}"
            )

        return currency

    def validate_description(self, description: str, max_length: int = 127) -> str:
        """
        Validate payment description with PayPal-specific rules.

        Args:
            description: Payment description
            max_length: Maximum allowed length

        Returns:
            Validated and sanitized description

        Raises:
            ValidationError: If description is invalid
        """
        if not description:
            raise ValidationError("Description cannot be empty")

        if not isinstance(description, str):
            raise ValidationError(f"Description must be a string, got {type(description).__name__}")

        description = description.strip()

        if not description:
            raise ValidationError("Description cannot be empty or whitespace only")

        if len(description) > max_length:
            raise ValidationError(f"Description too long: {len(description)} > {max_length} characters")

        # Check for forbidden characters
        forbidden_found = self.FORBIDDEN_DESCRIPTION_CHARS & set(description)
        if forbidden_found:
            raise ValidationError(f"Description contains forbidden characters: {', '.join(forbidden_found)}")

        # Check for potential security issues
        if self._contains_suspicious_content(description):
            raise ValidationError("Description contains potentially unsafe content")

        return description

    def validate_order_id(self, order_id: str) -> str:
        """
        Validate PayPal order ID format.

        Args:
            order_id: PayPal order ID to validate

        Returns:
            Validated order ID

        Raises:
            ValidationError: If order ID is invalid
        """
        if not order_id:
            raise ValidationError("Order ID cannot be empty")

        if not isinstance(order_id, str):
            raise ValidationError(f"Order ID must be a string, got {type(order_id).__name__}")

        order_id = order_id.strip()

        if not self.ORDER_ID_PATTERN.match(order_id):
            raise ValidationError(f"Invalid PayPal order ID format: '{order_id}'")

        return order_id

    def validate_email(self, email: str) -> str:
        """
        Validate email address for PayPal.

        Args:
            email: Email address to validate

        Returns:
            Validated email address

        Raises:
            ValidationError: If email is invalid
        """
        if not email:
            raise ValidationError("Email cannot be empty")

        if not isinstance(email, str):
            raise ValidationError(f"Email must be a string, got {type(email).__name__}")

        email = email.strip().lower()

        # Basic email validation
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        if not email_pattern.match(email):
            raise ValidationError(f"Invalid email format: '{email}'")

        # PayPal-specific email length limit
        if len(email) > 254:
            raise ValidationError("Email address too long (max 254 characters)")

        return email

    def validate_phone(self, phone: str, country_code: str = "US") -> str:
        """
        Validate phone number for PayPal.

        Args:
            phone: Phone number to validate
            country_code: Country code for validation context

        Returns:
            Validated and normalized phone number

        Raises:
            ValidationError: If phone number is invalid
        """
        if not phone:
            raise ValidationError("Phone number cannot be empty")

        if not isinstance(phone, str):
            raise ValidationError(f"Phone must be a string, got {type(phone).__name__}")

        # Remove common formatting
        cleaned_phone = re.sub(r'[^\d+]', '', phone)

        if not cleaned_phone:
            raise ValidationError("Phone number must contain digits")

        # Basic validation (7-15 digits, optional + prefix)
        if not re.match(r'^\+?[\d]{7,15}$', cleaned_phone):
            raise ValidationError(f"Invalid phone number format: '{phone}'")

        return cleaned_phone

    def validate_reference_id(self, reference_id: str) -> str:
        """
        Validate reference/invoice ID.

        Args:
            reference_id: Reference ID to validate

        Returns:
            Validated reference ID

        Raises:
            ValidationError: If reference ID is invalid
        """
        if not reference_id:
            raise ValidationError("Reference ID cannot be empty")

        if not isinstance(reference_id, str):
            raise ValidationError(f"Reference ID must be a string, got {type(reference_id).__name__}")

        reference_id = reference_id.strip()

        if len(reference_id) > 127:
            raise ValidationError("Reference ID too long (max 127 characters)")

        # Allow alphanumeric, hyphens, underscores
        if not re.match(r'^[a-zA-Z0-9_-]+$', reference_id):
            raise ValidationError("Reference ID can only contain letters, numbers, hyphens, and underscores")

        return reference_id

    def validate_metadata(self, metadata: dict) -> dict:
        """
        Validate metadata dictionary.

        Args:
            metadata: Metadata dictionary to validate

        Returns:
            Validated metadata

        Raises:
            ValidationError: If metadata is invalid
        """
        if not metadata:
            return {}

        if not isinstance(metadata, dict):
            raise ValidationError(f"Metadata must be a dictionary, got {type(metadata).__name__}")

        if len(metadata) > 10:
            raise ValidationError("Metadata cannot have more than 10 key-value pairs")

        validated_metadata = {}

        for key, value in metadata.items():
            # Validate key
            if not isinstance(key, str):
                raise ValidationError(f"Metadata key must be a string, got {type(key).__name__}")

            if len(key) > 50:
                raise ValidationError(f"Metadata key too long: '{key}' (max 50 characters)")

            if not re.match(r'^[a-zA-Z0-9_-]+$', key):
                raise ValidationError(f"Invalid metadata key: '{key}' (alphanumeric, hyphens, underscores only)")

            # Validate value
            if not isinstance(value, (str, int, float, bool)):
                raise ValidationError(f"Metadata value must be string, number, or boolean, got {type(value).__name__}")

            str_value = str(value)
            if len(str_value) > 255:
                raise ValidationError(f"Metadata value too long for key '{key}' (max 255 characters)")

            validated_metadata[key] = str_value

        return validated_metadata

    def _contains_suspicious_content(self, text: str) -> bool:
        """Check for potentially suspicious content in text."""
        suspicious_patterns = [
            r'<script', r'javascript:', r'data:', r'vbscript:',
            r'onclick', r'onerror', r'onload', r'eval\(',
            r'document\.', r'window\.', r'alert\(', r'prompt\('
        ]

        text_lower = text.lower()
        return any(re.search(pattern, text_lower) for pattern in suspicious_patterns)

    def validate_complete_payment(self, amount, currency: str, description: str,
                                  reference_id: Optional[str] = None,
                                  metadata: Optional[dict] = None) -> dict:
        """
        Validate a complete payment request.

        Args:
            amount: Payment amount
            currency: Currency code
            description: Payment description
            reference_id: Optional reference ID
            metadata: Optional metadata

        Returns:
            Dictionary with validated parameters

        Raises:
            ValidationError: If any parameter is invalid
        """
        validated = {
            'amount': self.validate_amount(amount, currency),
            'currency': self.validate_currency(currency),
            'description': self.validate_description(description),
        }

        if reference_id:
            validated['reference_id'] = self.validate_reference_id(reference_id)

        if metadata:
            validated['metadata'] = self.validate_metadata(metadata)

        return validated

    def get_currency_info(self, currency: str) -> dict:
        """
        Get information about a specific currency.

        Args:
            currency: Currency code

        Returns:
            Dictionary with currency information
        """
        currency = self.validate_currency(currency)

        info = {
            'code': currency,
            'decimal_places': 0 if currency in self.ZERO_DECIMAL_CURRENCIES else 2,
            'supported': currency in self.SUPPORTED_CURRENCIES,
            'configured': currency in self.supported_currencies,
        }

        if currency in self.CURRENCY_LIMITS:
            info.update(self.CURRENCY_LIMITS[currency])
        else:
            info.update({'min': self.min_amount, 'max': self.max_amount})

        return info

    def validate_url(self, url: str) -> str:
        """
        Validate URL with HTTPS requirement.

        Args:
            url: URL to validate

        Returns:
            Validated URL

        Raises:
            ValidationError: If URL is invalid
        """
        if not url:
            raise ValidationError("URL cannot be empty")

        if not isinstance(url, str):
            raise ValidationError(f"URL must be a string, got {type(url).__name__}")

        url = url.strip()

        if not url.startswith('https://'):
            raise ValidationError("URL must use HTTPS protocol")

        # Basic URL validation
        url_pattern = re.compile(
            r'^https://(?:[a-zA-Z0-9-]+\.)*[a-zA-Z0-9-]+(?:\:[0-9]+)?(?:/[^\s]*)?$'
        )
        if not url_pattern.match(url):
            raise ValidationError(f"Invalid URL format: '{url}'")

        return url

    def validate_payment_id(self, payment_id: str) -> str:
        """
        Validate payment ID format.

        Args:
            payment_id: Payment ID to validate

        Returns:
            Validated payment ID

        Raises:
            ValidationError: If payment ID is invalid
        """
        if not payment_id:
            raise ValidationError("Payment ID cannot be empty")

        if not isinstance(payment_id, str):
            raise ValidationError(f"Payment ID must be a string, got {type(payment_id).__name__}")

        payment_id = payment_id.strip()

        if not payment_id:
            raise ValidationError("Payment ID cannot be empty or whitespace only")

        if len(payment_id) < 4:
            raise ValidationError("Payment ID too short (minimum 4 characters)")

        if len(payment_id) > 100:
            raise ValidationError("Payment ID too long (maximum 100 characters)")

        # Check for invalid characters
        if ' ' in payment_id or '\n' in payment_id or '\t' in payment_id:
            raise ValidationError("Payment ID cannot contain spaces or control characters")

        return payment_id

    def validate_client_credentials(self, client_id: str, client_secret: str) -> tuple:
        """
        Validate PayPal client credentials.

        Args:
            client_id: PayPal client ID
            client_secret: PayPal client secret

        Returns:
            Tuple of validated credentials

        Raises:
            ValidationError: If credentials are invalid
        """
        if not client_id:
            raise ValidationError("Client ID cannot be empty")

        if not client_secret:
            raise ValidationError("Client secret cannot be empty")

        if not isinstance(client_id, str):
            raise ValidationError(f"Client ID must be a string, got {type(client_id).__name__}")

        if not isinstance(client_secret, str):
            raise ValidationError(f"Client secret must be a string, got {type(client_secret).__name__}")

        client_id = client_id.strip()
        client_secret = client_secret.strip()

        if not client_id:
            raise ValidationError("Client ID cannot be empty or whitespace only")

        if not client_secret:
            raise ValidationError("Client secret cannot be empty or whitespace only")

        if len(client_id) < 4:
            raise ValidationError("Client ID too short (minimum 4 characters)")

        if len(client_secret) < 4:
            raise ValidationError("Client secret too short (minimum 4 characters)")

        if len(client_id) > 200:
            raise ValidationError("Client ID too long (maximum 200 characters)")

        if len(client_secret) > 200:
            raise ValidationError("Client secret too long (maximum 200 characters)")

        return client_id, client_secret

    def validate_webhook_url(self, url: str) -> str:
        """
        Validate webhook URL with additional restrictions.

        Args:
            url: Webhook URL to validate

        Returns:
            Validated webhook URL

        Raises:
            ValidationError: If webhook URL is invalid
        """
        # First validate as regular URL
        url = self.validate_url(url)

        # Additional webhook-specific restrictions
        if 'localhost' in url.lower():
            raise ValidationError("Webhook URL cannot use localhost")

        # Check for private IP addresses
        import socket
        import urllib.parse

        parsed = urllib.parse.urlparse(url)
        hostname = parsed.hostname

        if hostname:
            try:
                # Check if it's an IP address
                ip = socket.inet_aton(hostname)
                ip_int = int.from_bytes(ip, byteorder='big')

                # Check for private IP ranges
                private_ranges = [
                    (0x7F000000, 0x7FFFFFFF),  # 127.0.0.0/8 (loopback)
                    (0x0A000000, 0x0AFFFFFF),  # 10.0.0.0/8
                    (0xAC100000, 0xAC1FFFFF),  # 172.16.0.0/12
                    (0xC0A80000, 0xC0A8FFFF),  # 192.168.0.0/16
                ]

                for start, end in private_ranges:
                    if start <= ip_int <= end:
                        raise ValidationError("Webhook URL cannot use private IP addresses")

            except (socket.error, ValueError):
                # Not an IP address, which is fine
                pass

        return url

    def validate_brand_name(self, brand_name: str) -> str:
        """
        Validate brand name.

        Args:
            brand_name: Brand name to validate

        Returns:
            Validated brand name

        Raises:
            ValidationError: If brand name is invalid
        """
        if not brand_name:
            raise ValidationError("Brand name cannot be empty")

        if not isinstance(brand_name, str):
            raise ValidationError(f"Brand name must be a string, got {type(brand_name).__name__}")

        brand_name = brand_name.strip()

        if not brand_name:
            raise ValidationError("Brand name cannot be empty or whitespace only")

        if len(brand_name) > 22:
            raise ValidationError("Brand name too long (maximum 22 characters)")

        return brand_name

    def validate_locale(self, locale: str) -> str:
        """
        Validate locale format.

        Args:
            locale: Locale to validate (e.g., 'en-US')

        Returns:
            Validated locale

        Raises:
            ValidationError: If locale is invalid
        """
        if not locale:
            raise ValidationError("Locale cannot be empty")

        if not isinstance(locale, str):
            raise ValidationError(f"Locale must be a string, got {type(locale).__name__}")

        locale = locale.strip()

        # Valid locale pattern: language-COUNTRY
        locale_pattern = re.compile(r'^[a-z]{2}-[A-Z]{2}$')
        if not locale_pattern.match(locale):
            raise ValidationError(f"Invalid locale format: '{locale}' (expected format: en-US)")

        # List of supported locales
        supported_locales = {
            'en-US', 'en-GB', 'fr-FR', 'de-DE', 'es-ES', 'it-IT',
            'pt-BR', 'zh-CN', 'ja-JP', 'ko-KR', 'ru-RU'
        }

        if locale not in supported_locales:
            supported_list = ', '.join(sorted(supported_locales))
            raise ValidationError(f"Locale '{locale}' not supported. Supported locales: {supported_list}")

        return locale

    def validate_currency_amount_combination(self, currency: str, amount) -> bool:
        """
        Validate currency and amount combination for special rules.

        Args:
            currency: Currency code
            amount: Amount value

        Returns:
            True if valid

        Raises:
            ValidationError: If combination is invalid
        """
        currency = self.validate_currency(currency)
        amount = self.validate_amount(amount, currency)

        # Check for zero-decimal currencies
        if currency in self.ZERO_DECIMAL_CURRENCIES:
            if float(amount) % 1 != 0:
                raise ValidationError(f"Currency {currency} does not support decimal places")

        return True

    def validate_amount_precision(self, amount, currency: str) -> bool:
        """
        Validate amount precision for currency.

        Args:
            amount: Amount to validate
            currency: Currency code

        Returns:
            True if precision is valid

        Raises:
            ValidationError: If precision is invalid
        """
        try:
            if isinstance(amount, str):
                amount = amount.replace(',', '').replace(' ', '').strip()

            decimal_amount = Decimal(str(amount))
        except (InvalidOperation, ValueError):
            raise ValidationError(f"Invalid amount format: {amount}")

        # Check decimal places
        if currency in self.ZERO_DECIMAL_CURRENCIES:
            if decimal_amount % 1 != 0:
                raise ValidationError(f"Currency {currency} does not support decimal places")
        else:
            # Most currencies support up to 2 decimal places
            if decimal_amount.as_tuple().exponent < -2:
                raise ValidationError("Amount cannot have more than 2 decimal places")

        return True

    def validate_minimum_amount(self, amount, currency: str) -> bool:
        """
        Validate minimum amount for currency.

        Args:
            amount: Amount to validate
            currency: Currency code

        Returns:
            True if amount meets minimum

        Raises:
            ValidationError: If amount is below minimum
        """
        currency = self.validate_currency(currency)

        try:
            if isinstance(amount, str):
                amount = amount.replace(',', '').replace(' ', '').strip()

            decimal_amount = Decimal(str(amount))
        except (InvalidOperation, ValueError):
            raise ValidationError(f"Invalid amount format: {amount}")

        float_amount = float(decimal_amount)

        # Check currency-specific minimum
        currency_limit = self.CURRENCY_LIMITS.get(currency)
        if currency_limit:
            min_amount = currency_limit["min"]
        else:
            min_amount = self.min_amount

        if float_amount < min_amount:
            raise ValidationError(f"Amount {decimal_amount} {currency} below minimum {min_amount} {currency}")

        return True

    def validate_description_content(self, description: str) -> str:
        """
        Validate description content for prohibited terms.

        Args:
            description: Description to validate

        Returns:
            Validated description

        Raises:
            ValidationError: If description contains prohibited content
        """
        description = self.validate_description(description)

        # Check for prohibited content
        prohibited_terms = [
            'illegal', 'drug', 'weapon', 'firearms', 'ammunition',
            'tobacco', 'prescription', 'counterfeit', 'stolen'
        ]

        description_lower = description.lower()
        for term in prohibited_terms:
            if term in description_lower:
                raise ValidationError(f"Description contains prohibited content: {term}")

        return description

    def get_supported_currencies(self) -> Set[str]:
        """Get set of supported currencies."""
        return self.supported_currencies.copy()

    def __repr__(self) -> str:
        """String representation of validator."""
        return (f"PayPalValidator(currencies={len(self.supported_currencies)}, "
                f"amount_range={self.min_amount}-{self.max_amount})")
