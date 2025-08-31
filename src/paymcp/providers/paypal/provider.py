"""
PayPal Payment Provider - The Best Implementation

This is the definitive PayPal payment provider for PayMCP, featuring:
- MCP compatibility with legacy interface
- Professional implementation with best practices
- PayPal-specific validation and configuration
- No hardcoded values - fully configurable
- Comprehensive error handling and security
"""

import base64
import time
import threading
from datetime import datetime, timezone
from typing import Tuple, Optional, Dict, Any, List
from urllib.parse import urljoin
import requests
import logging
from enum import Enum
from dataclasses import dataclass
from decimal import Decimal

from ..base import BasePaymentProvider
from .config import PayPalConfig
from .validator import PayPalValidator, PayPalValidationError


class PaymentStatus(Enum):
    """Standardized payment status."""
    CREATED = "created"
    PENDING = "pending"
    APPROVED = "approved"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Money:
    """Immutable money value with currency."""
    amount: float
    currency: str

    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("Amount cannot be negative")
        if len(self.currency) != 3:
            raise ValueError("Currency must be 3-character code")

    def format(self, include_symbol: bool = True) -> str:
        """Format money for display."""
        symbols = {'USD': '$', 'EUR': '€', 'GBP': '£', 'JPY': '¥'}
        if include_symbol and self.currency in symbols:
            return f"{symbols[self.currency]}{self.amount:.2f}"
        return f"{self.amount:.2f} {self.currency}"


@dataclass(frozen=True)
class PaymentRequest:
    """Payment request data."""
    money: Money
    description: str
    reference_id: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None


@dataclass
class PaymentResult:
    """Payment operation result."""
    payment_id: str
    status: PaymentStatus
    money: Money
    approval_url: Optional[str] = None
    created_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class PaymentError(Exception):
    """Payment processing error."""
    pass


class AuthenticationError(Exception):
    """Authentication error."""
    pass


class PayPalStatusMapper:
    """Maps PayPal API statuses to standardized payment statuses."""

    STATUS_MAP = {
        "CREATED": PaymentStatus.CREATED,
        "SAVED": PaymentStatus.PENDING,
        "APPROVED": PaymentStatus.APPROVED,
        "VOIDED": PaymentStatus.CANCELLED,
        "COMPLETED": PaymentStatus.COMPLETED,
        "PAYER_ACTION_REQUIRED": PaymentStatus.PENDING,
        "FAILED": PaymentStatus.FAILED,
        "CANCELLED": PaymentStatus.CANCELLED,
        "DENIED": PaymentStatus.FAILED,
        "EXPIRED": PaymentStatus.EXPIRED,
    }

    MCP_STATUS_MAP = {
        PaymentStatus.COMPLETED: "paid",
        PaymentStatus.APPROVED: "approved",
        PaymentStatus.CREATED: "created",
        PaymentStatus.PENDING: "pending",
        PaymentStatus.FAILED: "failed",
        PaymentStatus.CANCELLED: "cancelled",
        PaymentStatus.EXPIRED: "expired",
        PaymentStatus.UNKNOWN: "unknown"
    }

    def map_status(self, provider_status: str) -> PaymentStatus:
        """Map PayPal status to standardized status."""
        return self.STATUS_MAP.get(provider_status.upper(), PaymentStatus.UNKNOWN)

    def map_to_mcp(self, standard_status: PaymentStatus) -> str:
        """Map standardized status to MCP-expected status."""
        return self.MCP_STATUS_MAP.get(standard_status, "unknown")


class PayPalTokenManager:
    """Thread-safe PayPal OAuth 2.0 token manager."""

    def __init__(self, config: PayPalConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__class__.__name__}")
        self._token: Optional[str] = None
        self._expires_at: float = 0
        self._lock = threading.RLock()
        self._expires_buffer = 300  # 5 minutes buffer

    def get_token(self) -> str:
        """Get valid access token (thread-safe)."""
        with self._lock:
            if not self._is_token_valid():
                self._token = self._fetch_token()
            return self._token

    def _is_token_valid(self) -> bool:
        """Check if current token is valid."""
        return (
            self._token is not None and
            time.time() < (self._expires_at - self._expires_buffer)
        )

    def _fetch_token(self) -> str:
        """Fetch new OAuth access token from PayPal."""
        self.logger.debug("Requesting new PayPal access token")

        auth_url = urljoin(self.config.base_url, "/v1/oauth2/token")

        # Prepare Basic authentication
        auth_string = f"{self.config.client_id}:{self.config.client_secret}"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')

        headers = {
            "Accept": "application/json",
            "Accept-Language": "en_US",
            "Authorization": f"Basic {auth_b64}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        data = "grant_type=client_credentials"

        try:
            response = requests.post(
                auth_url,
                headers=headers,
                data=data,
                timeout=self.config.timeout
            )
            response.raise_for_status()

            token_data = response.json()
            access_token = token_data["access_token"]
            expires_in = token_data.get("expires_in", 3600)

            # Set token expiration
            self._expires_at = time.time() + expires_in

            self.logger.debug(f"PayPal access token obtained, expires in {expires_in} seconds")
            return access_token

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to get PayPal access token: {e}")
            raise AuthenticationError(f"PayPal authentication failed: {e}") from e
        except KeyError as e:
            self.logger.error(f"Invalid token response format: {e}")
            raise AuthenticationError(f"Invalid PayPal authentication response: {e}") from e


class PayPalHTTPClient:
    """PayPal-specific HTTP client with resilience."""

    def __init__(self, config: PayPalConfig, token_manager: PayPalTokenManager):
        self.config = config
        self.token_manager = token_manager
        self.logger = logging.getLogger(f"{__class__.__name__}")
        self._session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create configured requests session."""
        session = requests.Session()

        # Configure retry strategy
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry

        retry_strategy = Retry(
            total=self.config.max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"],
            backoff_factor=1
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        return session

    def request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make authenticated request to PayPal API."""
        url = urljoin(self.config.base_url, endpoint.lstrip('/'))

        token = self.token_manager.get_token()
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "PayPal-Request-Id": f"paymcp-{int(time.time() * 1000)}",
            "User-Agent": f"PayMCP-PayPal/{self.config.brand_name}",
        }

        try:
            if method.upper() == "GET":
                response = self._session.get(url, headers=headers, params=data, timeout=self.config.timeout)
            elif method.upper() == "POST":
                response = self._session.post(url, headers=headers, json=data, timeout=self.config.timeout)
            elif method.upper() == "PATCH":
                response = self._session.patch(url, headers=headers, json=data, timeout=self.config.timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            self.logger.debug(f"PayPal API {method} {endpoint} succeeded with status {response.status_code}")

            # Handle empty responses
            if response.status_code == 204:
                return {}

            return response.json()

        except requests.exceptions.HTTPError as e:
            error_details = self._extract_error_details(e.response)
            self.logger.error(f"PayPal API error: {e} - {error_details}")
            raise PaymentError(f"PayPal API error: {e} - {error_details}") from e

        except requests.exceptions.RequestException as e:
            self.logger.error(f"PayPal request error: {e}")
            raise PaymentError(f"PayPal request error: {e}") from e

    def _extract_error_details(self, response) -> str:
        """Extract detailed error information from PayPal response."""
        if not response:
            return "Unknown error"

        try:
            error_data = response.json()
            message = error_data.get('message', 'Unknown error')

            if 'details' in error_data:
                details = [detail.get('description', '') for detail in error_data['details']]
                if details:
                    message += f" Details: {', '.join(details)}"

            return message
        except ValueError:
            return response.text or "Unknown error"


class PaymentFactory:
    """Factory for creating payment objects."""

    @staticmethod
    def create_payment_request(amount, currency: str, description: str,
                               reference_id: Optional[str] = None,
                               metadata: Optional[Dict[str, str]] = None) -> PaymentRequest:
        """Create validated payment request."""
        money = Money(float(amount), currency.upper())
        return PaymentRequest(
            money=money,
            description=description.strip(),
            reference_id=reference_id,
            metadata=metadata or {}
        )


class PayPalOrderBuilder:
    """Builder for PayPal order payloads."""

    def __init__(self, config: PayPalConfig):
        self.config = config
        self._order_data = {
            "intent": "CAPTURE",
            "purchase_units": [],
            "application_context": {}
        }

    def with_payment_request(self, request: PaymentRequest) -> 'PayPalOrderBuilder':
        """Add payment request to order."""
        purchase_unit = {
            "amount": {
                "currency_code": request.money.currency,
                "value": f"{request.money.amount:.2f}"
            },
            "description": request.description
        }

        if request.reference_id:
            purchase_unit["reference_id"] = request.reference_id

        if request.metadata:
            # PayPal supports custom_id for metadata
            custom_data = []
            for key, value in request.metadata.items():
                custom_data.append(f"{key}:{value}")
            if custom_data:
                purchase_unit["custom_id"] = ";".join(custom_data)[:127]  # PayPal limit

        self._order_data["purchase_units"] = [purchase_unit]
        return self

    def with_application_context(self) -> 'PayPalOrderBuilder':
        """Add application context from configuration."""
        self._order_data["application_context"] = {
            "return_url": self.config.return_url,
            "cancel_url": self.config.cancel_url,
            "brand_name": self.config.brand_name,
            "locale": self.config.locale,
            "landing_page": "BILLING",
            "shipping_preference": "NO_SHIPPING",
            "user_action": "PAY_NOW"
        }
        return self

    def build(self) -> Dict[str, Any]:
        """Build the final order payload."""
        if not self._order_data["purchase_units"]:
            raise ValueError("Order must have at least one purchase unit")

        return self._order_data.copy()


class PayPalProvider(BasePaymentProvider):
    """
    The definitive PayPal payment provider for PayMCP.

    This provider combines:
    - MCP compatibility (same interface as StripeProvider)
    - Professional implementation with best practices
    - PayPal-specific validation and configuration
    - No hardcoded values - fully configurable
    - Comprehensive error handling and security
    """

    def __init__(self,
                 config: PayPalConfig = None,
                 client_id: str = None,
                 client_secret: str = None,
                 api_key: str = None,
                 apiKey: str = None,
                 sandbox: bool = True,
                 return_url: str = "https://yourapp.com/payment/success",
                 cancel_url: str = "https://yourapp.com/payment/cancel",
                 webhook_url: Optional[str] = None,
                 brand_name: str = "PayMCP",
                 locale: str = "en-US",
                 currencies: Optional[List[str]] = None,
                 min_amount: float = 0.01,
                 max_amount: float = 10000.00,
                 timeout: int = 30,
                 retry_attempts: int = 3,
                 logger: logging.Logger = None,
                 **kwargs):
        """
        Initialize PayPal provider with comprehensive configuration.

        Args:
            config: Pre-configured PayPalConfig object (preferred)
            client_id: PayPal client ID (alternative to config)
            client_secret: PayPal client secret (alternative to config)
            ... other parameters for backward compatibility
        """
        # Use provided config or create from parameters
        if config:
            if not isinstance(config, PayPalConfig):
                raise ValueError("config must be a PayPalConfig instance")
            self.config = config
        else:
            # Handle alternative parameter names for MCP compatibility
            resolved_client_id = client_id or api_key or apiKey

            # Create PayPal-specific configuration
            config_kwargs = {
                "client_id": resolved_client_id,
                "client_secret": client_secret,
                "sandbox": sandbox,
                "return_url": return_url,
                "cancel_url": cancel_url,
                "webhook_url": webhook_url,
                "brand_name": brand_name,
                "locale": locale,
                "min_amount": min_amount,
                "max_amount": max_amount,
                "timeout": timeout,
                "max_retries": retry_attempts
            }

            if currencies:
                config_kwargs["currencies"] = currencies

            # Filter None values
            config_kwargs = {k: v for k, v in config_kwargs.items() if v is not None}

            try:
                self.config = PayPalConfig(**config_kwargs)
            except Exception as e:
                raise ValueError(f"Invalid PayPal configuration: {e}") from e

        # Initialize base provider
        super().__init__(api_key=self.config.client_id, logger=logger)

        # Initialize PayPal-specific components
        self.validator = PayPalValidator(
            supported_currencies=self.config.currencies,
            min_amount=self.config.min_amount,
            max_amount=self.config.max_amount
        )

        self.token_manager = PayPalTokenManager(self.config)
        self.http_client = PayPalHTTPClient(self.config, self.token_manager)
        self.status_mapper = PayPalStatusMapper()
        self.order_builder = PayPalOrderBuilder(self.config)

        env_name = "Sandbox" if self.config.sandbox else "Production"
        self.logger.info(f"PayPal provider initialized ({env_name})")

    # MCP-Compatible Interface Methods

    def create_payment(self, amount: float, currency: str, description: str) -> Tuple[str, str]:
        """
        Create a PayPal payment (MCP-compatible interface).

        Args:
            amount: Payment amount
            currency: Currency code
            description: Payment description

        Returns:
            Tuple of (payment_id, approval_url)

        Raises:
            RuntimeError: If payment creation fails (MCP-expected exception)
        """
        try:
            # Validate using PayPal-specific validator
            validated = self.validator.validate_complete_payment(amount, currency, description)

            # Create payment request
            request = PaymentFactory.create_payment_request(
                amount=float(validated['amount']),
                currency=validated['currency'],
                description=validated['description']
            )

            # Create payment using internal logic
            result = self._create_payment_internal(request)

            self.logger.info(f"PayPal payment created: {result.payment_id}")
            return result.payment_id, result.approval_url

        except Exception as e:
            self.logger.error(f"PayPal payment creation failed: {e}")
            # MCP expects RuntimeError for payment failures
            raise RuntimeError(f"PayPal payment creation failed: {e}") from e

    def get_payment_status(self, payment_id: str) -> str:
        """
        Get payment status (MCP-compatible interface).

        Args:
            payment_id: PayPal order ID

        Returns:
            Payment status string (MCP-compatible values)
        """
        try:
            # Validate order ID
            validated_id = self.validator.validate_order_id(payment_id)

            # Get status using internal logic
            result = self._get_payment_status_internal(validated_id)

            # Map to MCP-compatible status
            mcp_status = self.status_mapper.map_to_mcp(result.status)

            self.logger.debug(f"PayPal payment {payment_id} status: {mcp_status}")
            return mcp_status

        except Exception as e:
            self.logger.error(f"PayPal status check failed: {e}")
            raise RuntimeError(f"PayPal status check failed: {e}") from e

    # Enhanced Interface Methods (for advanced usage)

    def create_payment_enhanced(self, request: PaymentRequest) -> PaymentResult:
        """Create payment using enhanced PaymentRequest object."""
        return self._create_payment_internal(request)

    def get_payment_status_enhanced(self, payment_id: str) -> PaymentResult:
        """Get payment status returning enhanced PaymentResult object."""
        return self._get_payment_status_internal(payment_id)

    def capture_payment(self, payment_id: str) -> PaymentResult:
        """Capture an approved PayPal payment."""
        try:
            validated_id = self.validator.validate_order_id(payment_id)

            endpoint = f"/v2/checkout/orders/{validated_id}/capture"
            response = self.http_client.request("POST", endpoint, {})

            return self._create_payment_result(response)

        except Exception as e:
            self.logger.error(f"PayPal capture failed for {payment_id}: {e}")
            raise PaymentError(f"PayPal capture failed: {e}") from e

    def refund_payment(self, capture_id: str, amount: Optional[float] = None,
                       currency: Optional[str] = None, reason: Optional[str] = None) -> Dict[str, Any]:
        """Refund a captured PayPal payment."""
        try:
            refund_data = {}

            if amount is not None:
                if currency is None:
                    raise ValueError("Currency is required when amount is specified")

                validated_amount = self.validator.validate_amount(amount, currency)
                validated_currency = self.validator.validate_currency(currency)

                refund_data["amount"] = {
                    "currency_code": validated_currency,
                    "value": f"{validated_amount:.2f}"
                }

            if reason:
                validated_reason = self.validator.validate_description(reason, max_length=255)
                refund_data["note_to_payer"] = validated_reason

            endpoint = f"/v2/payments/captures/{capture_id}/refund"
            response = self.http_client.request("POST", endpoint, refund_data)

            return response

        except Exception as e:
            self.logger.error(f"PayPal refund failed for {capture_id}: {e}")
            raise PaymentError(f"PayPal refund failed: {e}") from e

    # Internal Implementation Methods

    def _create_payment_internal(self, request: PaymentRequest) -> PaymentResult:
        """Internal payment creation logic."""
        try:
            # Build PayPal order
            order_data = (self.order_builder
                          .with_payment_request(request)
                          .with_application_context()
                          .build())

            # Make API call
            response = self.http_client.request("POST", "/v2/checkout/orders", order_data)

            # Process response
            return self._create_payment_result(response, request.money)

        except Exception as e:
            raise PaymentError(f"Payment creation failed: {e}") from e

    def _get_payment_status_internal(self, payment_id: str) -> PaymentResult:
        """Internal payment status logic."""
        try:
            endpoint = f"/v2/checkout/orders/{payment_id}"
            response = self.http_client.request("GET", endpoint)

            return self._create_payment_result(response)

        except requests.exceptions.HTTPError as e:
            if e.response and e.response.status_code == 404:
                # Return unknown status for not found orders
                return PaymentResult(
                    payment_id=payment_id,
                    status=PaymentStatus.UNKNOWN,
                    money=Money(0.0, "USD")
                )
            raise

    def _create_payment_result(self, response: Dict[str, Any],
                               original_money: Optional[Money] = None) -> PaymentResult:
        """Create PaymentResult from PayPal API response."""
        order_id = response["id"]
        status = self.status_mapper.map_status(response.get("status", "UNKNOWN"))

        # Extract money information
        money = original_money
        if not money:
            purchase_units = response.get("purchase_units", [])
            if purchase_units:
                amount_info = purchase_units[0]["amount"]
                money = Money(
                    amount=float(amount_info["value"]),
                    currency=amount_info["currency_code"]
                )
            else:
                money = Money(0.0, "USD")  # Fallback

        # Extract approval URL
        approval_url = None
        for link in response.get("links", []):
            if link.get("rel") == "approve":
                approval_url = link.get("href")
                break

        return PaymentResult(
            payment_id=order_id,
            status=status,
            money=money,
            approval_url=approval_url,
            created_at=datetime.now(timezone.utc),
            metadata=response
        )

    # Utility Methods

    def get_configuration(self) -> Dict[str, Any]:
        """Get provider configuration (without sensitive data)."""
        return self.config.mask_sensitive_data()

    def get_order_details(self, order_id: str) -> Dict[str, Any]:
        """Get detailed order information from PayPal."""
        validated_id = self.validator.validate_order_id(order_id)
        return self.http_client.request("GET", f"/v2/checkout/orders/{validated_id}")

    def health_check(self) -> Dict[str, Any]:
        """Perform health check on PayPal integration."""
        try:
            token = self.token_manager.get_token()
            return {
                "status": "healthy",
                "paypal_connected": bool(token),
                "environment": "Sandbox" if self.config.sandbox else "Production",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "environment": "Sandbox" if self.config.sandbox else "Production",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    def __str__(self) -> str:
        """String representation."""
        env_name = "Sandbox" if self.config.sandbox else "Production"
        return f"PayPalProvider(environment={env_name}, brand={self.config.brand_name})"

    def __repr__(self) -> str:
        """Developer representation."""
        return (f"PayPalProvider(client_id='{self.config.client_id[:8]}...', "
                f"environment={'Sandbox' if self.config.sandbox else 'Production'})")


# Export the main provider
__all__ = ['PayPalProvider']
