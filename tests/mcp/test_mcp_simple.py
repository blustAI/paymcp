#!/usr/bin/env python3
"""
Simple MCP Server Test

A simplified test script for quickly testing PayMCP MCP server functionality.
"""

import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from paymcp import PayMCP, PaymentFlow
from paymcp.utils.env import load_env_file


class MockMCP:
    """Mock MCP server for testing."""
    
    def __init__(self):
        self.tools = {}
    
    def tool(self, **kwargs):
        """Mock tool decorator."""
        def decorator(func):
            self.tools[func.__name__] = func
            return func
        return decorator


def main():
    print("🚀 PayMCP Simple MCP Server Test")
    print("="*40)
    
    try:
        # Load environment variables
        load_env_file()
        print("✅ Environment loaded")
        
        # Setup providers
        providers = {}
        
        # PayPal
        if os.getenv("PAYPAL_CLIENT_ID") and os.getenv("PAYPAL_CLIENT_SECRET"):
            providers["paypal"] = {
                "client_id": os.getenv("PAYPAL_CLIENT_ID"),
                "client_secret": os.getenv("PAYPAL_CLIENT_SECRET"),
                "sandbox": True,
                "return_url": "https://example.com/success",
                "cancel_url": "https://example.com/cancel"
            }
            print("✅ PayPal provider configured")
        else:
            print("⚠️  PayPal credentials not found")
        
        # Stripe
        stripe_api_key = os.getenv("STRIPE_API_KEY")
        if stripe_api_key:
            providers["stripe"] = {
                "api_key": stripe_api_key,
                "success_url": "https://example.com/success?session_id={CHECKOUT_SESSION_ID}",
                "cancel_url": "https://example.com/cancel"
            }
            print("✅ Stripe provider configured")
        else:
            print("⚠️  Stripe credentials not found")
        
        if not providers:
            print("❌ No providers configured")
            return
        
        # Initialize PayMCP
        mcp = MockMCP()
        paymcp = PayMCP(
            mcp_instance=mcp,
            providers=providers,
            payment_flow=PaymentFlow.TWO_STEP
        )
        print(f"✅ PayMCP initialized with {len(paymcp.providers)} providers")
        
        # Test payment creation
        if "paypal" in paymcp.providers:
            print("\n🧪 Testing PayPal payment...")
            provider = paymcp.providers["paypal"]
            payment_id, payment_url = provider.create_payment(
                amount=9.99,
                currency="USD", 
                description="Test payment via MCP"
            )
            print(f"   Payment ID: {payment_id}")
            print(f"   Payment URL: {payment_url[:50]}...")
            
            # Check status
            status = provider.get_payment_status(payment_id)
            print(f"   Status: {status}")
        
        if "stripe" in paymcp.providers:
            print("\n🧪 Testing Stripe payment...")
            provider = paymcp.providers["stripe"]
            session_id, session_url = provider.create_payment(
                amount=19.99,
                currency="USD",
                description="Test Stripe payment via MCP"
            )
            print(f"   Session ID: {session_id}")
            print(f"   Session URL: {session_url[:50]}...")
            
            # Check status
            status = provider.get_payment_status(session_id)
            print(f"   Status: {status}")
        
        print("\n🎉 MCP server test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()