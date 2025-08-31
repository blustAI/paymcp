"""
PayPal Provider Configuration

This module provides PayPal-specific configuration management with validation,
environment handling, and security best practices.
"""

import os
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import urlparse


class PayPalConfigError(Exception):
    """PayPal configuration error."""
    pass


@dataclass(repr=False)
class PayPalConfig:
    """PayPal-specific configuration with validation."""

    # Credentials
    client_id: str
    client_secret: str

    # Environment
    sandbox: bool = True

    # URLs
    return_url: Optional[str] = None
    cancel_url: Optional[str] = None
    webhook_url: Optional[str] = None
    base_url: Optional[str] = None

    # Branding
    brand_name: Optional[str] = None
    locale: str = "en-US"

    # Currencies and amounts
    currencies: List[str] = None
    min_amount: float = 0.01
    max_amount: float = 10000.00

    # Network settings
    timeout: int = 30
    max_retries: int = 3

    def __post_init__(self):
        """Validate configuration after initialization."""
        # Set defaults
        if self.currencies is None:
            self.currencies = ["USD"]

        # Set base URL based on environment
        if self.base_url is None:
            self.base_url = ("https://api-m.sandbox.paypal.com"
                             if self.sandbox
                             else "https://api-m.paypal.com")

        # Validate configuration
        self._validate_credentials()
        self._validate_urls()
        self._validate_amounts()
        self._validate_currencies()
        self._validate_locale()
        self._validate_network_settings()

    def _validate_credentials(self):
        """Validate PayPal credentials."""
        if not self.client_id or not self.client_secret:
            raise PayPalConfigError("Both client_id and client_secret are required")

        if len(self.client_id) < 10:
            raise PayPalConfigError("client_id appears to be invalid (too short)")

        if len(self.client_secret) < 10:
            raise PayPalConfigError("client_secret appears to be invalid (too short)")

    def _validate_urls(self):
        """Validate URL configurations."""
        urls_to_check = [
            ("return_url", self.return_url),
            ("cancel_url", self.cancel_url),
            ("webhook_url", self.webhook_url),
            ("base_url", self.base_url)
        ]

        for url_name, url_value in urls_to_check:
            if not url_value:
                continue  # Optional URLs can be None

            try:
                parsed = urlparse(url_value)
                if not parsed.scheme or not parsed.netloc:
                    raise PayPalConfigError(f"Invalid {url_name}: {url_value}")

                if parsed.scheme not in ('http', 'https'):
                    raise PayPalConfigError(f"{url_name} must use HTTP or HTTPS")

                # Enforce HTTPS in production
                if not self.sandbox and parsed.scheme != 'https':
                    raise PayPalConfigError(f"{url_name} must use HTTPS in production")

                # Special validation for webhook URLs
                if url_name == "webhook_url":
                    if parsed.hostname in ('localhost', '127.0.0.1', '0.0.0.0'):
                        raise PayPalConfigError("Webhook URLs cannot use localhost or local IP addresses")
                    if parsed.hostname and parsed.hostname.startswith(
                            '192.168.') or parsed.hostname.startswith('10.') or parsed.hostname.startswith('172.'):
                        raise PayPalConfigError("Webhook URLs cannot use private network addresses")

            except PayPalConfigError:
                raise
            except Exception as e:
                raise PayPalConfigError(f"Invalid {url_name}: {e}") from e

    def _validate_amounts(self):
        """Validate amount configurations."""
        if self.min_amount <= 0:
            raise PayPalConfigError("min_amount must be positive")

        if self.max_amount <= self.min_amount:
            raise PayPalConfigError("max_amount must be greater than min_amount")

        # PayPal-specific limits
        if self.min_amount < 0.01:
            raise PayPalConfigError("PayPal minimum amount is $0.01")

        if self.max_amount > 10000.00:
            raise PayPalConfigError("PayPal maximum amount is $10,000")

    def _validate_currencies(self):
        """Validate currency configurations."""
        if not self.currencies:
            raise PayPalConfigError("At least one currency must be specified")

        # PayPal supported currencies
        supported_currencies = {
            "AUD", "BRL", "CAD", "CZK", "DKK", "EUR", "HKD", "HUF", "ILS", "JPY",
            "MXN", "NOK", "NZD", "PHP", "PLN", "GBP", "RUB", "SGD", "SEK", "CHF",
            "TWD", "THB", "USD", "INR", "MYR"
        }

        for currency in self.currencies:
            if not isinstance(currency, str) or len(currency) != 3:
                raise PayPalConfigError(f"Invalid currency code: {currency}")

            if currency.upper() not in supported_currencies:
                raise PayPalConfigError(f"Unsupported PayPal currency: {currency}")

        # Ensure currencies are uppercase
        self.currencies = [c.upper() for c in self.currencies]

    def _validate_locale(self):
        """Validate locale format."""
        if not self.locale:
            return

        # Check basic locale format (language-Country)
        import re
        if not re.match(r'^[a-z]{2}-[A-Z]{2}$', self.locale):
            raise PayPalConfigError(f"Invalid locale format '{self.locale}'. Expected format: 'en-US'")

        # List of supported PayPal locales
        supported_locales = {
            'en-US', 'en-GB', 'en-AU', 'en-CA', 'fr-FR', 'fr-CA', 'de-DE',
            'es-ES', 'es-MX', 'it-IT', 'pt-BR', 'pt-PT', 'nl-NL', 'da-DK',
            'no-NO', 'sv-SE', 'fi-FI', 'pl-PL', 'ru-RU', 'ja-JP', 'ko-KR',
            'zh-CN', 'zh-TW', 'zh-HK'
        }

        if self.locale not in supported_locales:
            raise PayPalConfigError(
                f"Unsupported locale '{
                    self.locale}'. Supported locales: {
                    ', '.join(
                        sorted(supported_locales))}")

    def _validate_network_settings(self):
        """Validate network settings."""
        if self.timeout <= 0 or self.timeout > 300:
            raise PayPalConfigError("timeout must be between 1 and 300 seconds")

        if self.max_retries < 0 or self.max_retries > 10:
            raise PayPalConfigError("max_retries must be between 0 and 10")

        if self.brand_name and len(self.brand_name) > 22:
            raise PayPalConfigError("brand_name must be 22 characters or less")

    def validate(self):
        """Explicitly validate configuration."""
        self.__post_init__()

    def __repr__(self):
        """Return a string representation with masked credentials."""
        masked_client_id = f"{self.client_id[:4]}***{self.client_id[-4:]}" if len(self.client_id) > 8 else "****"
        masked_client_secret = f"{
            self.client_secret[:4]}***{self.client_secret[-4:]}" if len(self.client_secret) > 8 else "****"

        return (f"PayPalConfig("
                f"client_id='{masked_client_id}', "
                f"client_secret='{masked_client_secret}', "
                f"sandbox={self.sandbox}, "
                f"base_url='{self.base_url}', "
                f"locale='{self.locale}', "
                f"currencies={self.currencies}, "
                f"min_amount={self.min_amount}, "
                f"max_amount={self.max_amount}, "
                f"timeout={self.timeout}, "
                f"max_retries={self.max_retries}"
                f")")

    def __str__(self):
        """Return a string representation with masked credentials."""
        return self.__repr__()

    @classmethod
    def from_dict(cls, config_dict: dict) -> 'PayPalConfig':
        """Create configuration from dictionary."""
        # Check required fields
        required_fields = {'client_id', 'client_secret'}
        missing_fields = required_fields - set(config_dict.keys())
        if missing_fields:
            raise PayPalConfigError(f"Missing required fields: {', '.join(missing_fields)}")

        # Filter out unknown keys
        valid_keys = {
            'client_id', 'client_secret', 'sandbox', 'return_url', 'cancel_url',
            'webhook_url', 'base_url', 'brand_name', 'locale', 'currencies',
            'min_amount', 'max_amount', 'timeout', 'max_retries'
        }

        filtered_config = {k: v for k, v in config_dict.items() if k in valid_keys}

        # Convert string boolean values
        if 'sandbox' in filtered_config and isinstance(filtered_config['sandbox'], str):
            filtered_config['sandbox'] = filtered_config['sandbox'].lower() in ('true', '1', 'yes')

        return cls(**filtered_config)

    @classmethod
    def from_env(cls, load_dotenv: bool = True) -> 'PayPalConfig':
        """Create configuration from environment variables.

        Args:
            load_dotenv: Whether to load .env file if python-dotenv is available
        """
        # Try to load .env file if requested
        if load_dotenv:
            from ...utils.env import load_env_file
            load_env_file()

        client_id = os.getenv("PAYPAL_CLIENT_ID")
        client_secret = os.getenv("PAYPAL_CLIENT_SECRET")

        if not client_id or not client_secret:
            raise PayPalConfigError(
                "PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET environment variables are required"
            )

        # Parse sandbox setting
        sandbox_str = os.getenv("PAYPAL_SANDBOX", "true").lower()
        if sandbox_str not in ('true', '1', 'yes', 'false', '0', 'no'):
            raise PayPalConfigError(f"PAYPAL_SANDBOX must be a valid boolean value, got: {sandbox_str}")
        sandbox = sandbox_str in ('true', '1', 'yes')

        # Parse timeout and retries
        try:
            timeout = int(os.getenv("PAYPAL_TIMEOUT", "30"))
        except ValueError:
            raise PayPalConfigError("PAYPAL_TIMEOUT must be a valid integer")

        try:
            max_retries = int(os.getenv("PAYPAL_MAX_RETRIES", "3"))
        except ValueError:
            raise PayPalConfigError("PAYPAL_MAX_RETRIES must be a valid integer")

        # Parse amounts
        try:
            min_amount = float(os.getenv("PAYPAL_MIN_AMOUNT", "0.01"))
            max_amount = float(os.getenv("PAYPAL_MAX_AMOUNT", "10000.00"))
        except ValueError:
            raise PayPalConfigError("PAYPAL_MIN_AMOUNT and PAYPAL_MAX_AMOUNT must be valid numbers")

        # Parse currencies
        currencies_str = os.getenv("PAYPAL_CURRENCIES", "USD")
        currencies = [c.strip() for c in currencies_str.split(",")]

        return cls(
            client_id=client_id,
            client_secret=client_secret,
            sandbox=sandbox,
            return_url=os.getenv("PAYPAL_RETURN_URL"),
            cancel_url=os.getenv("PAYPAL_CANCEL_URL"),
            webhook_url=os.getenv("PAYPAL_WEBHOOK_URL"),
            base_url=os.getenv("PAYPAL_BASE_URL"),
            brand_name=os.getenv("PAYPAL_BRAND_NAME"),
            locale=os.getenv("PAYPAL_LOCALE", "en-US"),
            currencies=currencies,
            min_amount=min_amount,
            max_amount=max_amount,
            timeout=timeout,
            max_retries=max_retries
        )

    def to_dict(self, include_sensitive: bool = True) -> dict:
        """Convert configuration to dictionary."""
        config_dict = {
            "client_id": self.client_id if include_sensitive else None,
            "client_secret": self.client_secret if include_sensitive else None,
            "sandbox": self.sandbox,
            "return_url": self.return_url,
            "cancel_url": self.cancel_url,
            "webhook_url": self.webhook_url,
            "base_url": self.base_url,
            "brand_name": self.brand_name,
            "locale": self.locale,
            "currencies": self.currencies,
            "min_amount": self.min_amount,
            "max_amount": self.max_amount,
            "timeout": self.timeout,
            "max_retries": self.max_retries
        }

        # Remove None values
        return {k: v for k, v in config_dict.items() if v is not None}

    def mask_sensitive_data(self) -> dict:
        """Return configuration with masked sensitive data."""
        config_dict = self.to_dict(include_sensitive=True)

        # Mask credentials
        if self.client_id:
            config_dict["client_id"] = f"{self.client_id[:4]}...{self.client_id[-4:]}"
        if self.client_secret:
            config_dict["client_secret"] = f"{self.client_secret[:4]}...{self.client_secret[-4:]}"

        return config_dict

    def __str__(self) -> str:
        """String representation with masked sensitive data."""
        masked_data = self.mask_sensitive_data()
        return f"PayPalConfig({masked_data})"

    def __repr__(self) -> str:
        """Repr with masked sensitive data."""
        return self.__str__()
