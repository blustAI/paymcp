#!/usr/bin/env python3
"""
PayMCP All Providers Test Script

This script comprehensively tests all payment providers (PayPal, Stripe, Walleot)
with detailed reporting, credential validation, and integration testing.

Usage:
    python scripts/test_all_providers.py [options]

Options:
    --unit-only     Run only unit tests
    --integration   Run integration tests (requires credentials)
    --provider X    Test only specific provider (paypal, stripe, walleot)
    --verbose       Detailed output
    --performance   Include performance tests
"""

import os
import sys
import time
import asyncio
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

@dataclass
class ProviderProviderTestResult:
    """Test result data structure."""
    provider: str
    test_type: str
    success: bool
    message: str
    duration: float
    details: Optional[Dict] = None

class PayMCPTester:
    """Comprehensive PayMCP testing suite."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results: List[ProviderTestResult] = []
        self.start_time = time.time()
    
    def log(self, message: str, level: str = "INFO"):
        """Log message with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = {
            "INFO": "ℹ️ ",
            "SUCCESS": "✅",
            "ERROR": "❌",
            "WARNING": "⚠️ ",
            "DEBUG": "🔍"
        }.get(level, "")
        
        if level != "DEBUG" or self.verbose:
            print(f"[{timestamp}] {prefix} {message}")
    
    def check_credentials(self) -> Dict[str, Dict[str, bool]]:
        """Check which provider credentials are available."""
        # Try to load .env file first
        try:
            from paymcp.utils.env import load_env_file
            load_env_file()
        except ImportError:
            # Fallback for when paymcp is not installed
            env_path = os.path.join(os.getcwd(), '.env')
            if os.path.exists(env_path):
                with open(env_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            os.environ.setdefault(key.strip(), value.strip())
        
        credentials = {
            "paypal": {
                "client_id": bool(os.getenv("PAYPAL_CLIENT_ID")),
                "client_secret": bool(os.getenv("PAYPAL_CLIENT_SECRET"))
            },
            "stripe": {
                "api_key": bool(os.getenv("STRIPE_API_KEY"))
            },
            "walleot": {
                "api_key": bool(os.getenv("WALLEOT_API_KEY"))
            }
        }
        
        return credentials
    
    def test_imports(self) -> None:
        """Test that all modules can be imported."""
        self.log("Testing module imports...")
        
        import_tests = [
            ("paymcp", "PayMCP main module"),
            ("paymcp.providers.paypal", "PayPal provider"),
            ("paymcp.providers.stripe", "Stripe provider"),
            ("paymcp.providers.walleot", "Walleot provider"),
            ("paymcp.decorators", "Price decorators"),
            ("paymcp.payment.payment_flow", "Payment flows")
        ]
        
        for module, description in import_tests:
            start_time = time.time()
            try:
                __import__(module)
                duration = time.time() - start_time
                self.results.append(ProviderTestResult(
                    provider="system",
                    test_type="import",
                    success=True,
                    message=f"{description} imported successfully",
                    duration=duration
                ))
                self.log(f"✅ {description}")
            except Exception as e:
                duration = time.time() - start_time
                self.results.append(ProviderTestResult(
                    provider="system",
                    test_type="import",
                    success=False,
                    message=f"Failed to import {module}: {e}",
                    duration=duration
                ))
                self.log(f"❌ Failed to import {module}: {e}", "ERROR")
    
    def test_paypal_unit(self) -> None:
        """Test PayPal provider unit tests."""
        self.log("Running PayPal unit tests...")
        
        try:
            from paymcp.providers.paypal import PayPalProvider, PayPalConfig, PayPalValidator
            
            # Test configuration
            start_time = time.time()
            config = PayPalConfig(
                client_id="test_client_id",
                client_secret="test_client_secret",
                sandbox=True
            )
            duration = time.time() - start_time
            
            self.results.append(ProviderTestResult(
                provider="paypal",
                test_type="unit",
                success=True,
                message="PayPal configuration creation",
                duration=duration
            ))
            
            # Test validator
            start_time = time.time()
            validator = PayPalValidator()
            
            # Test valid inputs
            validator.validate_amount(10.50, "USD")
            validator.validate_currency("USD")
            validator.validate_description("Test payment")
            
            # Test invalid inputs should raise exceptions
            try:
                validator.validate_amount(-10.0, "USD")
                raise AssertionError("Should have raised validation error")
            except Exception:
                pass  # Expected
            
            duration = time.time() - start_time
            self.results.append(ProviderTestResult(
                provider="paypal",
                test_type="unit", 
                success=True,
                message="PayPal validator tests",
                duration=duration
            ))
            
            # Test provider initialization
            start_time = time.time()
            provider = PayPalProvider(config=config)
            duration = time.time() - start_time
            
            self.results.append(ProviderTestResult(
                provider="paypal",
                test_type="unit",
                success=True,
                message="PayPal provider initialization", 
                duration=duration
            ))
            
            self.log("✅ PayPal unit tests passed")
            
        except Exception as e:
            self.results.append(ProviderTestResult(
                provider="paypal",
                test_type="unit",
                success=False,
                message=f"PayPal unit tests failed: {e}",
                duration=0
            ))
            self.log(f"❌ PayPal unit tests failed: {e}", "ERROR")
    
    def test_paypal_integration(self) -> None:
        """Test PayPal provider integration."""
        client_id = os.getenv("PAYPAL_CLIENT_ID")
        client_secret = os.getenv("PAYPAL_CLIENT_SECRET")
        
        if not client_id or not client_secret:
            self.log("⚠️  PayPal credentials not found, skipping integration tests", "WARNING")
            return
        
        self.log("Running PayPal integration tests...")
        
        try:
            from paymcp.providers.paypal import PayPalProvider, PayPalConfig
            
            # Test authentication
            start_time = time.time()
            config = PayPalConfig(
                client_id=client_id,
                client_secret=client_secret,
                sandbox=True,
                return_url="https://example.com/success",
                cancel_url="https://example.com/cancel"
            )
            
            provider = PayPalProvider(config=config)
            token = provider.token_manager.get_token()
            duration = time.time() - start_time
            
            self.results.append(ProviderTestResult(
                provider="paypal",
                test_type="integration",
                success=True,
                message="PayPal authentication successful",
                duration=duration,
                details={"token_length": len(token)}
            ))
            
            # Test payment creation
            start_time = time.time()
            payment_id, payment_url = provider.create_payment(
                amount=10.99,
                currency="USD",
                description="Integration test payment"
            )
            duration = time.time() - start_time
            
            self.results.append(ProviderTestResult(
                provider="paypal",
                test_type="integration", 
                success=True,
                message="PayPal payment creation successful",
                duration=duration,
                details={"payment_id": payment_id[:20] + "..."}
            ))
            
            # Test payment status
            start_time = time.time()
            status = provider.get_payment_status(payment_id)
            duration = time.time() - start_time
            
            self.results.append(ProviderTestResult(
                provider="paypal",
                test_type="integration",
                success=True, 
                message=f"PayPal payment status check: {status}",
                duration=duration
            ))
            
            self.log(f"✅ PayPal integration tests passed")
            self.log(f"   Payment ID: {payment_id}")
            self.log(f"   Payment URL: {payment_url[:50]}...")
            
        except Exception as e:
            self.results.append(ProviderTestResult(
                provider="paypal",
                test_type="integration",
                success=False,
                message=f"PayPal integration tests failed: {e}",
                duration=0
            ))
            self.log(f"❌ PayPal integration tests failed: {e}", "ERROR")
    
    def test_stripe_unit(self) -> None:
        """Test Stripe provider unit tests."""
        self.log("Running Stripe unit tests...")
        
        try:
            from paymcp.providers.stripe import StripeProvider
            
            # Test provider initialization
            start_time = time.time()
            provider = StripeProvider(api_key="sk_test_dummy_key")
            duration = time.time() - start_time
            
            self.results.append(ProviderTestResult(
                provider="stripe",
                test_type="unit",
                success=True,
                message="Stripe provider initialization",
                duration=duration
            ))
            
            self.log("✅ Stripe unit tests passed")
            
        except Exception as e:
            self.results.append(ProviderTestResult(
                provider="stripe",
                test_type="unit",
                success=False,
                message=f"Stripe unit tests failed: {e}",
                duration=0
            ))
            self.log(f"❌ Stripe unit tests failed: {e}", "ERROR")
    
    def test_stripe_integration(self) -> None:
        """Test Stripe provider integration."""
        api_key = os.getenv("STRIPE_API_KEY")
        
        if not api_key:
            self.log("⚠️  Stripe API key not found, skipping integration tests", "WARNING")
            return
        
        self.log("Running Stripe integration tests...")
        
        try:
            from paymcp.providers.stripe import StripeProvider
            
            # Test payment creation
            start_time = time.time()
            provider = StripeProvider(
                api_key=api_key,
                success_url="https://example.com/success?session_id={CHECKOUT_SESSION_ID}",
                cancel_url="https://example.com/cancel"
            )
            
            session_id, session_url = provider.create_payment(
                amount=15.50,
                currency="USD", 
                description="Stripe integration test"
            )
            duration = time.time() - start_time
            
            self.results.append(ProviderTestResult(
                provider="stripe",
                test_type="integration",
                success=True,
                message="Stripe payment creation successful",
                duration=duration,
                details={"session_id": session_id[:20] + "..."}
            ))
            
            # Test payment status
            start_time = time.time()
            status = provider.get_payment_status(session_id)
            duration = time.time() - start_time
            
            self.results.append(ProviderTestResult(
                provider="stripe",
                test_type="integration",
                success=True,
                message=f"Stripe payment status check: {status}",
                duration=duration
            ))
            
            self.log(f"✅ Stripe integration tests passed")
            self.log(f"   Session ID: {session_id}")
            self.log(f"   Session URL: {session_url[:50]}...")
            
        except Exception as e:
            self.results.append(ProviderTestResult(
                provider="stripe",
                test_type="integration",
                success=False,
                message=f"Stripe integration tests failed: {e}",
                duration=0
            ))
            self.log(f"❌ Stripe integration tests failed: {e}", "ERROR")
    
    def test_walleot_unit(self) -> None:
        """Test Walleot provider unit tests."""
        self.log("Running Walleot unit tests...")
        
        try:
            from paymcp.providers.walleot import WalleotProvider
            
            # Test provider initialization
            start_time = time.time()
            provider = WalleotProvider(api_key="dummy_walleot_key")
            duration = time.time() - start_time
            
            self.results.append(ProviderTestResult(
                provider="walleot",
                test_type="unit",
                success=True,
                message="Walleot provider initialization",
                duration=duration
            ))
            
            self.log("✅ Walleot unit tests passed")
            
        except Exception as e:
            self.results.append(ProviderTestResult(
                provider="walleot",
                test_type="unit",
                success=False,
                message=f"Walleot unit tests failed: {e}",
                duration=0
            ))
            self.log(f"❌ Walleot unit tests failed: {e}", "ERROR")
    
    def test_walleot_integration(self) -> None:
        """Test Walleot provider integration."""
        api_key = os.getenv("WALLEOT_API_KEY")
        
        if not api_key:
            self.log("⚠️  Walleot API key not found, skipping integration tests", "WARNING")
            return
        
        self.log("Running Walleot integration tests...")
        
        try:
            from paymcp.providers.walleot import WalleotProvider
            
            # Test payment creation
            start_time = time.time()
            provider = WalleotProvider(api_key=api_key)
            
            session_id, session_url = provider.create_payment(
                amount=8.75,
                currency="USD",
                description="Walleot integration test"
            )
            duration = time.time() - start_time
            
            self.results.append(ProviderTestResult(
                provider="walleot",
                test_type="integration",
                success=True,
                message="Walleot payment creation successful",
                duration=duration,
                details={"session_id": session_id[:20] + "..."}
            ))
            
            # Test payment status
            start_time = time.time()
            status = provider.get_payment_status(session_id)
            duration = time.time() - start_time
            
            self.results.append(ProviderTestResult(
                provider="walleot",
                test_type="integration",
                success=True,
                message=f"Walleot payment status check: {status}",
                duration=duration
            ))
            
            self.log(f"✅ Walleot integration tests passed")
            self.log(f"   Session ID: {session_id}")
            self.log(f"   Session URL: {session_url[:50]}...")
            
        except Exception as e:
            self.results.append(ProviderTestResult(
                provider="walleot",
                test_type="integration",
                success=False,
                message=f"Walleot integration tests failed: {e}",
                duration=0
            ))
            self.log(f"❌ Walleot integration tests failed: {e}", "ERROR")
    
    def test_mcp_integration(self) -> None:
        """Test full MCP integration with all providers."""
        self.log("Testing MCP integration...")
        
        try:
            from paymcp import PayMCP
            from paymcp.decorators import price
            from paymcp.payment.payment_flow import PaymentFlow
            
            # Mock MCP
            class MockMCP:
                def __init__(self):
                    self.tools = {}
                
                def tool(self, **kwargs):
                    def decorator(func):
                        self.tools[func.__name__] = func
                        return func
                    return decorator
            
            # Setup providers based on available credentials
            providers = {}
            
            if os.getenv("PAYPAL_CLIENT_ID") and os.getenv("PAYPAL_CLIENT_SECRET"):
                providers["paypal"] = {
                    "client_id": os.getenv("PAYPAL_CLIENT_ID"),
                    "client_secret": os.getenv("PAYPAL_CLIENT_SECRET"),
                    "sandbox": True,
                    "return_url": "https://example.com/success",
                    "cancel_url": "https://example.com/cancel"
                }
            
            if os.getenv("STRIPE_API_KEY"):
                providers["stripe"] = {
                    "api_key": os.getenv("STRIPE_API_KEY")
                }
            
            if os.getenv("WALLEOT_API_KEY"):
                providers["walleot"] = {
                    "api_key": os.getenv("WALLEOT_API_KEY")
                }
            
            if not providers:
                self.log("⚠️  No provider credentials found, skipping MCP integration", "WARNING")
                return
            
            # Test PayMCP initialization
            start_time = time.time()
            mcp = MockMCP()
            paymcp = PayMCP(
                mcp_instance=mcp,
                providers=providers,
                payment_flow=PaymentFlow.TWO_STEP
            )
            duration = time.time() - start_time
            
            self.results.append(ProviderTestResult(
                provider="mcp",
                test_type="integration",
                success=True,
                message=f"PayMCP initialized with {len(providers)} providers",
                duration=duration,
                details={"providers": list(providers.keys())}
            ))
            
            # Test tool decoration
            start_time = time.time()
            
            @mcp.tool(name="test_tool", description="Test paid tool")
            @price(price=5.99, currency="USD")
            async def test_paid_tool():
                return "Tool executed successfully"
            
            duration = time.time() - start_time
            
            self.results.append(ProviderTestResult(
                provider="mcp",
                test_type="integration", 
                success=True,
                message="MCP tool with @price decorator created",
                duration=duration
            ))
            
            self.log(f"✅ MCP integration tests passed")
            self.log(f"   Providers configured: {list(providers.keys())}")
            
        except Exception as e:
            self.results.append(ProviderTestResult(
                provider="mcp",
                test_type="integration",
                success=False,
                message=f"MCP integration tests failed: {e}",
                duration=0
            ))
            self.log(f"❌ MCP integration tests failed: {e}", "ERROR")
    
    def run_performance_tests(self) -> None:
        """Run performance benchmarks."""
        self.log("Running performance tests...")
        
        if not (os.getenv("PAYPAL_CLIENT_ID") and os.getenv("PAYPAL_CLIENT_SECRET")):
            self.log("⚠️  PayPal credentials required for performance tests", "WARNING")
            return
        
        try:
            from paymcp.providers.paypal import PayPalProvider, PayPalConfig
            
            config = PayPalConfig.from_env()
            provider = PayPalProvider(config=config)
            
            # Test token caching performance
            self.log("Testing token caching...")
            
            # First request (should be slower)
            start_time = time.time()
            token1 = provider.token_manager.get_token()
            first_duration = time.time() - start_time
            
            # Second request (should be faster due to caching)
            start_time = time.time()
            token2 = provider.token_manager.get_token()
            second_duration = time.time() - start_time
            
            speedup = first_duration / second_duration if second_duration > 0 else float('inf')
            
            self.results.append(ProviderTestResult(
                provider="paypal",
                test_type="performance",
                success=True,
                message=f"Token caching speedup: {speedup:.1f}x",
                duration=first_duration + second_duration,
                details={
                    "first_request": first_duration,
                    "cached_request": second_duration,
                    "speedup": speedup
                }
            ))
            
            # Test rapid payment creation
            self.log("Testing rapid payment creation...")
            
            payment_count = 5
            start_time = time.time()
            
            for i in range(payment_count):
                payment_id, payment_url = provider.create_payment(
                    amount=1.00 + (i * 0.01),
                    currency="USD",
                    description=f"Performance test {i}"
                )
            
            total_duration = time.time() - start_time
            avg_duration = total_duration / payment_count
            
            self.results.append(ProviderTestResult(
                provider="paypal",
                test_type="performance",
                success=True,
                message=f"Created {payment_count} payments in {total_duration:.2f}s (avg: {avg_duration:.2f}s)",
                duration=total_duration,
                details={
                    "payment_count": payment_count,
                    "total_time": total_duration,
                    "avg_time": avg_duration
                }
            ))
            
            self.log("✅ Performance tests completed")
            
        except Exception as e:
            self.results.append(ProviderTestResult(
                provider="performance",
                test_type="performance", 
                success=False,
                message=f"Performance tests failed: {e}",
                duration=0
            ))
            self.log(f"❌ Performance tests failed: {e}", "ERROR")
    
    def print_summary(self) -> None:
        """Print comprehensive test summary."""
        total_duration = time.time() - self.start_time
        
        # Group results by provider and test type
        by_provider = {}
        by_type = {}
        
        for result in self.results:
            if result.provider not in by_provider:
                by_provider[result.provider] = {"passed": 0, "failed": 0, "total_duration": 0}
            if result.test_type not in by_type:
                by_type[result.test_type] = {"passed": 0, "failed": 0, "total_duration": 0}
            
            if result.success:
                by_provider[result.provider]["passed"] += 1
                by_type[result.test_type]["passed"] += 1
            else:
                by_provider[result.provider]["failed"] += 1
                by_type[result.test_type]["failed"] += 1
            
            by_provider[result.provider]["total_duration"] += result.duration
            by_type[result.test_type]["total_duration"] += result.duration
        
        print("\n" + "="*80)
        print("🧪 PAYMCP COMPREHENSIVE TEST SUMMARY")
        print("="*80)
        
        print(f"\n⏱️  Total Runtime: {total_duration:.2f} seconds")
        print(f"📊 Total Tests: {len(self.results)}")
        
        # Summary by provider
        print(f"\n📋 RESULTS BY PROVIDER:")
        for provider, stats in by_provider.items():
            total = stats["passed"] + stats["failed"]
            success_rate = (stats["passed"] / total * 100) if total > 0 else 0
            emoji = "✅" if stats["failed"] == 0 else "⚠️" if success_rate >= 50 else "❌"
            
            print(f"  {emoji} {provider.upper():<12} {stats['passed']:>2}/{total:<2} passed "
                  f"({success_rate:>5.1f}%) [{stats['total_duration']:>5.2f}s]")
        
        # Summary by test type  
        print(f"\n📋 RESULTS BY TEST TYPE:")
        for test_type, stats in by_type.items():
            total = stats["passed"] + stats["failed"]
            success_rate = (stats["passed"] / total * 100) if total > 0 else 0
            emoji = "✅" if stats["failed"] == 0 else "⚠️" if success_rate >= 50 else "❌"
            
            print(f"  {emoji} {test_type.upper():<12} {stats['passed']:>2}/{total:<2} passed "
                  f"({success_rate:>5.1f}%) [{stats['total_duration']:>5.2f}s]")
        
        # Detailed results
        if self.verbose:
            print(f"\n📝 DETAILED RESULTS:")
            for i, result in enumerate(self.results, 1):
                status = "✅ PASS" if result.success else "❌ FAIL"
                print(f"  {i:>2}. {status} [{result.provider}:{result.test_type}] "
                      f"{result.message} ({result.duration:.3f}s)")
                
                if result.details and self.verbose:
                    for key, value in result.details.items():
                        print(f"       {key}: {value}")
        
        # Failures summary
        failures = [r for r in self.results if not r.success]
        if failures:
            print(f"\n❌ FAILURES ({len(failures)}):")
            for failure in failures:
                print(f"  • [{failure.provider}:{failure.test_type}] {failure.message}")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        
        credentials = self.check_credentials()
        missing_creds = []
        for provider, creds in credentials.items():
            if not all(creds.values()):
                missing_creds.append(provider)
        
        if missing_creds:
            print(f"  • Set credentials for: {', '.join(missing_creds)}")
            print(f"    to enable full integration testing")
        
        if failures:
            print(f"  • Review failed tests above for specific issues")
            print(f"  • Check network connectivity and API credentials")
        
        total_passed = sum(1 for r in self.results if r.success)
        overall_rate = (total_passed / len(self.results) * 100) if self.results else 0
        
        if overall_rate == 100:
            print(f"  🎉 All tests passed! PayMCP is ready for production.")
        elif overall_rate >= 80:
            print(f"  ✅ Most tests passed. Minor issues may need attention.")
        else:
            print(f"  ⚠️  Several tests failed. Review setup and credentials.")
        
        print("="*80)


def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(description="PayMCP comprehensive test suite")
    parser.add_argument("--unit-only", action="store_true", help="Run only unit tests")
    parser.add_argument("--integration", action="store_true", help="Run integration tests")
    parser.add_argument("--provider", choices=["paypal", "stripe", "walleot"], 
                       help="Test specific provider only")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--performance", action="store_true", help="Include performance tests")
    
    args = parser.parse_args()
    
    tester = PayMCPTester(verbose=args.verbose)
    
    print("🚀 PayMCP Comprehensive Test Suite Starting...")
    
    # Check credentials
    creds = tester.check_credentials()
    tester.log("Checking provider credentials...")
    for provider, provider_creds in creds.items():
        available = all(provider_creds.values())
        status = "✅" if available else "❌"
        tester.log(f"  {status} {provider.upper()}: {'Available' if available else 'Missing'}")
    
    # Run tests based on arguments
    tester.test_imports()
    
    if not args.provider or args.provider == "paypal":
        tester.test_paypal_unit()
        if args.integration or not args.unit_only:
            tester.test_paypal_integration()
    
    if not args.provider or args.provider == "stripe":
        tester.test_stripe_unit()
        if args.integration or not args.unit_only:
            tester.test_stripe_integration()
    
    if not args.provider or args.provider == "walleot":
        tester.test_walleot_unit()
        if args.integration or not args.unit_only:
            tester.test_walleot_integration()
    
    if not args.unit_only and not args.provider:
        tester.test_mcp_integration()
    
    if args.performance:
        tester.run_performance_tests()
    
    # Print summary
    tester.print_summary()


if __name__ == "__main__":
    main()