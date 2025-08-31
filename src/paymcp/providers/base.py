from abc import ABC, abstractmethod
from typing import Tuple, Optional
import logging
import requests


class BasePaymentProvider(ABC):
    """
    Base payment provider interface for backward compatibility.

    This class is maintained for compatibility with existing Stripe provider.
    """

    def __init__(self, api_key: str = None, apiKey: str = None, logger: logging.Logger = None):
        self.api_key = api_key if api_key is not None else apiKey
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    def _build_headers(self) -> dict:
        """Build headers for legacy providers."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

    def _request(self, method: str, url: str, data: dict = None):
        """Make HTTP request for legacy providers."""
        headers = self._build_headers()
        try:
            if method.upper() == "GET":
                resp = requests.get(url, headers=headers, params=data, timeout=30)
            elif method.upper() == "POST":
                if headers.get("Content-Type") == "application/json":
                    resp = requests.post(url, headers=headers, json=data, timeout=30)
                else:
                    resp = requests.post(url, headers=headers, data=data, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            resp.raise_for_status()
            self.logger.debug(f"HTTP {method} {url} succeeded with status {resp.status_code}")
            return resp.json()
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"HTTP error occurred: {e}")
            raise RuntimeError(f"HTTP error: {e}") from e
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request exception occurred: {e}")
            raise RuntimeError(f"Request error: {e}") from e
        except ValueError as e:
            self.logger.error(f"Value error occurred: {e}")
            raise RuntimeError(f"Value error: {e}") from e

    @abstractmethod
    def create_payment(
        self, amount: float, currency: str, description: str
    ) -> Tuple[str, str]:
        """
        Return (payment_id, payment_url) that the user should visit.
        """

    @abstractmethod
    def get_payment_status(self, payment_id: str) -> str:
        """
        Return payment status.
        """
