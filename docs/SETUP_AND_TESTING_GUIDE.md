# PayMCP Complete Setup and Testing Guide

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Provider Setup](#provider-setup)
   - [PayPal Setup](#paypal-setup)
   - [Stripe Setup](#stripe-setup)
   - [Walleot Setup](#walleot-setup)
4. [MCP Integration](#mcp-integration)
5. [Testing Guide](#testing-guide)
6. [Automated Testing Scripts](#automated-testing-scripts)
7. [Troubleshooting](#troubleshooting)

---

## 🔧 Prerequisites

### System Requirements
- **Python 3.10+** (required, tested with Python 3.12.7)
- **pip** package manager
- **Git** for cloning repositories
- **Internet connection** for API testing
- **Terminal/Command Line** access

### Account Requirements
You'll need accounts with payment providers for full testing:

- **PayPal Developer Account** → [developer.paypal.com](https://developer.paypal.com)
- **Stripe Account** → [stripe.com](https://stripe.com)
- **Walleot Account** → [walleot.com](https://walleot.com) *(if using Walleot)*

---

## 📦 Installation

### Step 1: Clone Repository
```bash
git clone https://github.com/blustAI/paymcp.git
cd paymcp
```

### Step 2: Create Virtual Environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

### Step 3: Install Dependencies

**For Production Use:**
```bash
# Install from PyPI (when available)
pip install mcp paymcp
```

**For Development/Testing:**
```bash
# Install the package in development mode
pip install -e .

# Install testing dependencies (choose one method):
# Method 1: Quoted (recommended)
pip install -e ".[test,dev]"

# Method 2: Alternative for shell compatibility
pip install -e .\[test,dev\]

# Method 3: Separate commands if above fail
pip install -e .
pip install pytest pytest-cov pytest-mock requests-mock black mypy

# Verify installation
python -c "from paymcp import PayMCP; print('PayMCP installed successfully')"
```

---

## 🏪 Provider Setup

## PayPal Setup

### 1. Create PayPal Developer Account
1. Visit [developer.paypal.com](https://developer.paypal.com)
2. Sign in or create account
3. Go to **Dashboard** → **My Apps & Credentials**

### 2. Create Sandbox Application
1. Click **"Create App"**
2. Choose **"Default Application"** or create new
3. Select **"Sandbox"** environment
4. Note down:
   - **Client ID** (starts with `A...`)
   - **Client Secret** (long string)

### 3. Set Environment Variables
```bash
# PayPal Sandbox Credentials
export PAYPAL_CLIENT_ID="your_sandbox_client_id_here"
export PAYPAL_CLIENT_SECRET="your_sandbox_client_secret_here"

# Optional PayPal Configuration
export PAYPAL_RETURN_URL="https://yourapp.com/success"
export PAYPAL_CANCEL_URL="https://yourapp.com/cancel"
export PAYPAL_BRAND_NAME="Your App Name"
```

### 4. Test PayPal Configuration
```bash
python -c "
import os
from paymcp.providers.paypal import PayPalProvider, PayPalConfig
config = PayPalConfig.from_env()
provider = PayPalProvider(config=config)
print('PayPal configured successfully!')
print(f'Environment: {\"Sandbox\" if config.sandbox else \"Production\"}')
"
```

## Stripe Setup

### 1. Create Stripe Account
1. Visit [stripe.com](https://stripe.com)
2. Create account and verify email
3. Go to **Developers** → **API keys**

### 2. Get API Keys
1. Copy **Publishable key** (starts with `pk_test_...`)
2. Copy **Secret key** (starts with `sk_test_...`)
3. **Use test keys for development!**

### 3. Set Environment Variables
```bash
# Stripe Test Credentials
export STRIPE_API_KEY="sk_test_your_stripe_secret_key_here"
export STRIPE_PUBLISHABLE_KEY="pk_test_your_stripe_publishable_key_here"

# Optional Stripe Configuration  
export STRIPE_SUCCESS_URL="https://yourapp.com/success?session_id={CHECKOUT_SESSION_ID}"
export STRIPE_CANCEL_URL="https://yourapp.com/cancel"
```

### 4. Test Stripe Configuration
```bash
python -c "
import os
from paymcp.providers.stripe import StripeProvider
api_key = os.getenv('STRIPE_API_KEY')
if api_key:
    provider = StripeProvider(api_key=api_key)
    print('Stripe configured successfully!')
else:
    print('STRIPE_API_KEY not set')
"
```

## Walleot Setup

### 1. Create Walleot Account
1. Visit [walleot.com](https://walleot.com)
2. Create account and complete verification
3. Go to **API** section in dashboard

### 2. Generate API Key
1. Create new API key
2. Copy the generated key
3. Note any webhook URLs if needed

### 3. Set Environment Variables
```bash
# Walleot Credentials
export WALLEOT_API_KEY="your_walleot_api_key_here"
```

### 4. Test Walleot Configuration
```bash
python -c "
import os
from paymcp.providers.walleot import WalleotProvider
api_key = os.getenv('WALLEOT_API_KEY')
if api_key:
    provider = WalleotProvider(api_key=api_key)
    print('Walleot configured successfully!')
else:
    print('WALLEOT_API_KEY not set')
"
```

---

## 🔗 MCP Integration

### Basic MCP Setup with All Providers

Create a test MCP server with multiple payment providers:

```python
# test_mcp_server.py
import os
from mcp.server.fastmcp import FastMCP, Context
from paymcp import PayMCP
from paymcp.decorators import price
from paymcp.payment.payment_flow import PaymentFlow

# Initialize MCP instance (use FastMCP for production)
mcp = FastMCP("PayMCP Test Server")

# For testing without FastMCP, you can use a mock:
# class MockMCP:
#     def __init__(self):
#         self.tools = {}
#     def tool(self, **kwargs):
#         def decorator(func):
#             self.tools[func.__name__] = func
#             return func
#         return decorator
# mcp = MockMCP()

# Configure all providers
providers = {}

# PayPal Provider (if credentials available)
if os.getenv("PAYPAL_CLIENT_ID") and os.getenv("PAYPAL_CLIENT_SECRET"):
    providers["paypal"] = {
        "client_id": os.getenv("PAYPAL_CLIENT_ID"),
        "client_secret": os.getenv("PAYPAL_CLIENT_SECRET"),
        "sandbox": True,
        "return_url": "https://yourapp.com/success",
        "cancel_url": "https://yourapp.com/cancel"
    }

# Stripe Provider (if credentials available)  
if os.getenv("STRIPE_API_KEY"):
    providers["stripe"] = {
        "api_key": os.getenv("STRIPE_API_KEY"),
        "success_url": "https://yourapp.com/success?session_id={CHECKOUT_SESSION_ID}",
        "cancel_url": "https://yourapp.com/cancel"
    }

# Walleot Provider (if credentials available)
if os.getenv("WALLEOT_API_KEY"):
    providers["walleot"] = {
        "api_key": os.getenv("WALLEOT_API_KEY")
    }

# Initialize PayMCP
if providers:
    paymcp = PayMCP(
        mcp_instance=mcp,
        providers=providers,
        payment_flow=PaymentFlow.TWO_STEP  # Recommended default
    )
    print(f"PayMCP initialized with providers: {list(providers.keys())}")
else:
    print("No payment providers configured. Set environment variables.")

# Define paid tools
@mcp.tool(name="premium_analysis", description="Run premium data analysis")
@price(price=19.99, currency="USD", provider="paypal")  # Use specific provider
async def premium_analysis(dataset: str, ctx: Context):
    """Expensive computation that costs money."""
    # ctx is required by PayMCP tool signature — include it even if unused
    return f"Premium analysis results for {dataset}"

@mcp.tool(name="ai_consultation", description="Get AI expert consultation")  
@price(price=49.99, currency="USD")  # Will use default provider
async def ai_consultation(topic: str, ctx: Context):
    """AI consultation service."""
    # ctx is required by PayMCP tool signature — include it even if unused
    return f"Expert consultation on {topic}"

if __name__ == "__main__":
    print("MCP Server with PayMCP is ready!")
    print("Available paid tools:", list(mcp.tools.keys()))
```

### Test the MCP Integration

```bash
python test_mcp_server.py
```

---

## 🧪 Testing Guide

### Current Test Coverage Status

**✅ Excellent Coverage Achieved:**
- **195 tests passing** with 80% overall coverage
- **Context System**: 100% coverage (perfect)
- **PayPal Config**: 90% coverage (target reached)
- **PayPal Validator**: 90% coverage (target reached) 
- **PayPal Provider**: 85% coverage (very good)

### Unit Tests

#### Run All Unit Tests
```bash
# Run all tests (includes unit and integration tests)  
pytest -v

# Run all unit tests only (faster, no API calls)
pytest tests/unit/ -v

# Run with coverage
pytest --cov=src/paymcp --cov-report=term
pytest --cov=src/paymcp --cov-report=html

# Run specific provider tests
pytest tests/unit/paypal/test_paypal_provider.py -v
```

#### Run PayPal Unit Tests
```bash
# All PayPal unit tests
pytest tests/unit/paypal/ -v

# Specific test files
pytest tests/unit/paypal/test_validator.py -v
pytest tests/unit/paypal/test_config.py -v
pytest tests/unit/paypal/test_paypal_provider.py -v
```

### Integration Tests

#### PayPal Integration Tests
```bash
# Set credentials first
export PAYPAL_CLIENT_ID="your_sandbox_client_id"
export PAYPAL_CLIENT_SECRET="your_sandbox_client_secret"

# Run PayPal integration tests
pytest tests/unit/paypal/test_integration.py -v -m integration

# Run all integration tests (may include skipped tests if credentials not set)
pytest tests/unit/paypal/test_integration.py -v
```

#### Test All Providers Integration
```bash
# Set all credentials
export PAYPAL_CLIENT_ID="your_paypal_client_id"
export PAYPAL_CLIENT_SECRET="your_paypal_client_secret"
export STRIPE_API_KEY="sk_test_your_stripe_key"
export WALLEOT_API_KEY="your_walleot_key"

# Run comprehensive integration tests (see automated script below)
python scripts/test_all_providers.py
```

### Manual Testing

#### Test Payment Creation
```bash
python -c "
import os
from paymcp.providers.paypal import PayPalProvider, PayPalConfig

# Test payment creation
config = PayPalConfig.from_env()  
provider = PayPalProvider(config=config)

payment_id, payment_url = provider.create_payment(
    amount=10.00,
    currency='USD', 
    description='Manual test payment'
)

print(f'Payment ID: {payment_id}')
print(f'Payment URL: {payment_url}')
print('Visit the URL to complete payment in sandbox')
"
```

#### Test Payment Status
```bash
python -c "
import os
from paymcp.providers.paypal import PayPalProvider, PayPalConfig

config = PayPalConfig.from_env()
provider = PayPalProvider(config=config)

# Replace with actual payment ID from previous test
payment_id = 'PAYID-EXAMPLE123'
status = provider.get_payment_status(payment_id)
print(f'Payment Status: {status}')
"
```

---

## 🤖 Automated Testing Scripts

### Setup Script

First, run the automated setup script to configure your environment:

```bash
# Interactive setup with credential input
python scripts/setup_test_env.py --interactive

# Non-interactive setup (just validation)
python scripts/setup_test_env.py

# Setup specific provider only
python scripts/setup_test_env.py --provider paypal --interactive
```

**What the setup script does:**
- ✅ Checks Python version (3.10+ required)
- 📦 Installs missing dependencies  
- 🔐 Guides credential setup
- 📝 Creates `.env.example` file
- 🧪 Validates configuration
- 📋 Provides next steps

### Main Test Script

Run comprehensive tests across all providers:

```bash
# Run all tests (unit + integration + MCP integration)
python scripts/test_all_providers.py --verbose

# Unit tests only (no API calls)
python scripts/test_all_providers.py --unit-only

# Integration tests only (requires credentials)
python scripts/test_all_providers.py --integration

# Test specific provider
python scripts/test_all_providers.py --provider paypal --verbose

# Include performance benchmarks  
python scripts/test_all_providers.py --performance --verbose

# Quick validation
python scripts/test_all_providers.py --unit-only --provider paypal
```

**Test Script Features:**
- 🔍 **Comprehensive Coverage**: Tests all providers, MCP integration, and edge cases
- ⚡ **Performance Benchmarks**: Token caching, rapid payment creation
- 📊 **Detailed Reporting**: Success rates, timing, recommendations
- 🎯 **Targeted Testing**: Test specific providers or test types
- 🔐 **Credential Validation**: Automatic detection of available credentials

**Sample Output:**
```
🚀 PayMCP Comprehensive Test Suite Starting...
ℹ️  Checking provider credentials...
  ✅ PAYPAL: Available
  ❌ STRIPE: Missing
  ❌ WALLEOT: Missing

ℹ️  Testing module imports...
✅ PayMCP main module
✅ PayPal provider
✅ Stripe provider

ℹ️  Running PayPal unit tests...
✅ PayPal unit tests passed

ℹ️  Running PayPal integration tests...
✅ PayPal integration tests passed
   Payment ID: PAYID-TEST123456789
   Payment URL: https://www.sandbox.paypal.com/checkoutnow...

================================================================================
🧪 PAYMCP COMPREHENSIVE TEST SUMMARY
================================================================================

⏱️  Total Runtime: 12.34 seconds
📊 Total Tests: 15

📋 RESULTS BY PROVIDER:
  ✅ PAYPAL        8/8 passed (100.0%) [ 8.45s]
  ✅ STRIPE        3/3 passed (100.0%) [ 1.23s]
  ✅ SYSTEM        4/4 passed (100.0%) [ 2.66s]

💡 RECOMMENDATIONS:
  🎉 All tests passed! PayMCP is ready for production.
================================================================================
```

### Quick Start Scripts

Create these helper scripts for common tasks:

```bash
# scripts/quick_test.sh
#!/bin/bash
echo "🚀 PayMCP Quick Test"
python scripts/setup_test_env.py
python scripts/test_all_providers.py --unit-only --verbose
```

```bash  
# scripts/full_test.sh
#!/bin/bash
echo "🧪 PayMCP Full Test Suite"
python scripts/setup_test_env.py
python scripts/test_all_providers.py --verbose --performance
```

Make scripts executable:
```bash
chmod +x scripts/quick_test.sh scripts/full_test.sh

# Run quick test
./scripts/quick_test.sh

# Run full test suite  
./scripts/full_test.sh
```

---

## 🔧 Troubleshooting

### Common Issues

#### 1. Installation Errors
```bash
# Error: Invalid requirement, can't find closing bracket
pip install -e .[test,dev]
```
**Solution:**
```bash
# Use quotes around the extras requirement
pip install -e ".[test,dev]"

# Or escape the brackets (bash/zsh)
pip install -e .\[test,dev\]

# Or install dependencies separately
pip install -e .
pip install pytest pytest-cov pytest-mock requests-mock black mypy
```

#### 2. Import Errors
```bash
ModuleNotFoundError: No module named 'paymcp'
```
**Solution:**
```bash
# Install in development mode
pip install -e .
# Or add to Python path
export PYTHONPATH="${PYTHONPATH}:/path/to/paymcp-main/src"
```

#### 3. PayPal Authentication Errors
```bash
PayPalAuthError: Client authentication failed
```
**Solutions:**
- ✅ Check credentials are correct (no extra spaces)
- ✅ Verify using **sandbox** credentials for testing
- ✅ Ensure credentials are properly set in environment
- ✅ Check PayPal Developer Dashboard for app status

#### 4. Network/API Errors
```bash
PayPalAPIError: Request timeout
```
**Solutions:**
- ✅ Check internet connection
- ✅ Verify PayPal API status: [status.paypal.com](https://status.paypal.com)
- ✅ Try increasing timeout in config
- ✅ Check firewall/proxy settings

#### 5. Validation Errors
```bash
PayPalValidationError: Invalid currency code
```
**Solutions:**
- ✅ Use uppercase currency codes (USD, EUR, GBP)
- ✅ Check amount is within limits (0.01 - 10,000.00)
- ✅ Ensure description is not empty
- ✅ Verify URLs use HTTPS

#### 6. Environment Variable Issues
```bash
PayPalConfigError: PAYPAL_CLIENT_ID not found
```
**Solutions:**
```bash
# Check current environment variables
env | grep PAYPAL

# Set temporarily
export PAYPAL_CLIENT_ID="your_client_id"
export PAYPAL_CLIENT_SECRET="your_client_secret"

# Set permanently (add to ~/.bashrc or ~/.zshrc)
echo 'export PAYPAL_CLIENT_ID="your_client_id"' >> ~/.bashrc
```

### Debugging Tips

#### Enable Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Or for specific modules
logging.getLogger('paymcp.providers.paypal').setLevel(logging.DEBUG)
```

#### Test with Minimal Script
```python
# minimal_test.py
import os
from paymcp.providers.paypal import PayPalProvider, PayPalConfig

try:
    config = PayPalConfig.from_env()
    provider = PayPalProvider(config=config)
    
    print("✅ Configuration loaded successfully")
    print(f"Environment: {'Sandbox' if config.sandbox else 'Production'}")
    
    # Test authentication
    token = provider._get_access_token()
    print("✅ Authentication successful")
    print(f"Token length: {len(token)}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print(f"Error type: {type(e).__name__}")
```

#### Check Provider Status
```python
# check_providers.py  
import os

providers_status = {
    "PayPal": {
        "CLIENT_ID": bool(os.getenv("PAYPAL_CLIENT_ID")),
        "CLIENT_SECRET": bool(os.getenv("PAYPAL_CLIENT_SECRET"))
    },
    "Stripe": {
        "API_KEY": bool(os.getenv("STRIPE_API_KEY"))
    },
    "Walleot": {
        "API_KEY": bool(os.getenv("WALLEOT_API_KEY"))
    }
}

for provider, credentials in providers_status.items():
    print(f"{provider}:")
    for cred, available in credentials.items():
        status = "✅" if available else "❌"
        print(f"  {status} {cred}")
```

### Getting Help

#### Check Logs
```bash
# Run with maximum verbosity
python scripts/test_all_providers.py --verbose --provider paypal

# Check specific test output
pytest src/paymcp/providers/paypal/tests/ -v -s --tb=long
```

#### Documentation Links
- 📚 **PayPal Developer Docs**: [developer.paypal.com/docs](https://developer.paypal.com/docs)
- 🔧 **Stripe API Docs**: [stripe.com/docs/api](https://stripe.com/docs/api)  
- 💬 **PayMCP GitHub Issues**: Create issue with error details
- 🐛 **Bug Reports**: Include full error trace and environment info

#### Environment Info Script
```python
# debug_info.py
import sys
import os
import platform
from pathlib import Path

print("🔍 PayMCP Debug Information")
print("=" * 50)
print(f"Python Version: {sys.version}")
print(f"Platform: {platform.system()} {platform.release()}")
print(f"Working Directory: {os.getcwd()}")
print(f"Python Path: {sys.path[:3]}...")

print("\nEnvironment Variables:")
paypal_vars = [k for k in os.environ.keys() if k.startswith('PAYPAL')]
stripe_vars = [k for k in os.environ.keys() if k.startswith('STRIPE')]
walleot_vars = [k for k in os.environ.keys() if k.startswith('WALLEOT')]

for var in paypal_vars + stripe_vars + walleot_vars:
    value = os.environ[var]
    masked = f"{value[:4]}...{value[-4:]}" if len(value) > 8 else "***"
    print(f"  {var}={masked}")

print("\nInstalled Packages:")
try:
    import pkg_resources
    packages = ['paymcp', 'requests', 'pydantic', 'pytest']
    for pkg in packages:
        try:
            version = pkg_resources.get_distribution(pkg).version
            print(f"  {pkg}: {version}")
        except:
            print(f"  {pkg}: Not installed")
except ImportError:
    print("  pkg_resources not available")
```

Run with: `python debug_info.py`

---

## 🎯 Quick Reference

### Essential Commands

```bash
# 🚀 Complete setup and test
python scripts/setup_test_env.py --interactive
python scripts/test_all_providers.py --verbose

# 🧪 Test specific scenarios  
python scripts/test_all_providers.py --unit-only                    # Unit tests only
python scripts/test_all_providers.py --integration --provider paypal # PayPal integration
python scripts/test_all_providers.py --performance                 # Performance tests

# 🔧 Manual testing
python -c "from paymcp.providers.paypal import PayPalConfig; print(PayPalConfig.from_env())"

# 📊 Run pytest directly
pytest tests/unit/paypal/ -v --cov=src/paymcp/providers/paypal
```
