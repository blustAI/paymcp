import requests
from .base import BasePaymentProvider
import logging
import time
import random
import string

SANDBOX_URL = "https://connect.squareupsandbox.com"
PRODUCTION_URL = "https://connect.squareup.com"

class SquareProvider(BasePaymentProvider):
    def __init__(self, 
                access_token: str,
                location_id: str,
                logger: logging.Logger = None,
                redirect_url: str = 'https://example.com/success',
                sandbox: bool = True):
        self.access_token = access_token
        self.location_id = location_id
        self.redirect_url = redirect_url
        self.base_url = SANDBOX_URL if sandbox else PRODUCTION_URL
        super().__init__(logger=logger)
        self.logger.debug("Square ready")

    def _build_headers(self) -> dict:
        """Square uses Bearer token authentication."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Square-Version": "2024-01-18",  # Latest stable API version
        }

    def _generate_idempotency_key(self) -> str:
        """Generate unique idempotency key for Square API calls."""
        timestamp = str(int(time.time() * 1000))
        random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        return f"{timestamp}-{random_str}"

    def create_payment(self, amount: float, currency: str, description: str):
        """Creates a Square Checkout and returns (checkout_id, checkout_url)."""
        self.logger.debug(f"Creating Square payment: {amount} {currency} for '{description}'")
        
        # Convert to cents
        amount_cents = int(amount * 100)
        
        idempotency_key = self._generate_idempotency_key()
        
        payload = {
            "idempotency_key": idempotency_key,
            "checkout": {
                "order": {
                    "order": {
                        "location_id": self.location_id,
                        "line_items": [
                            {
                                "name": description,
                                "quantity": "1",
                                "base_price_money": {
                                    "amount": amount_cents,
                                    "currency": currency.upper()
                                }
                            }
                        ]
                    },
                    "idempotency_key": idempotency_key
                },
                "redirect_url": self.redirect_url
            }
        }
        
        resp = requests.post(
            f"{self.base_url}/v2/locations/{self.location_id}/checkouts",
            headers=self._build_headers(),
            json=payload
        )
        resp.raise_for_status()
        data = resp.json()
        
        checkout = data.get("checkout", {})
        checkout_id = checkout.get("id")
        checkout_url = checkout.get("checkout_page_url")
        
        if not checkout_id or not checkout_url:
            raise ValueError("Invalid response from Square API")
        
        return checkout_id, checkout_url

    def get_payment_status(self, payment_id: str) -> str:
        """Returns payment status for the given checkout_id."""
        self.logger.debug(f"Checking Square payment status for: {payment_id}")
        
        try:
            # First get the checkout to find the order
            resp = requests.get(
                f"{self.base_url}/v2/locations/{self.location_id}/checkouts/{payment_id}",
                headers=self._build_headers()
            )
            resp.raise_for_status()
            checkout_data = resp.json()
            
            order = checkout_data.get("checkout", {}).get("order", {})
            order_id = order.get("id")
            
            if not order_id:
                return "pending"
            
            # Now check the order status
            order_resp = requests.get(
                f"{self.base_url}/v2/orders/{order_id}?location_id={self.location_id}",
                headers=self._build_headers()
            )
            order_resp.raise_for_status()
            order_data = order_resp.json()
            
            order_state = order_data.get("order", {}).get("state", "")
            
            # Map Square order state to standard status
            if order_state == "COMPLETED":
                return "paid"
            elif order_state == "CANCELED":
                return "canceled"
            else:
                return "pending"
                
        except Exception as e:
            self.logger.error(f"Error checking Square payment status: {e}")
            return "pending"