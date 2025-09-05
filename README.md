# PayMCP

**Provider-agnostic payment layer for MCP (Model Context Protocol) tools and agents.**

`paymcp` is a lightweight SDK that helps you add monetization to your MCP-based tools, servers, or agents. It supports multiple payment providers and integrates seamlessly with MCP's tool/resource interface.

---

## 🔧 Features

- ✅ Add `@price(...)` decorators to your MCP tools to enable payments
- 🔁 Choose between different payment flows (elicit, confirm, etc.)
- 🔌 Pluggable support for providers like Walleot, Stripe, and more
- ⚙️ Easy integration with `FastMCP` or other MCP servers
- 🎯 **MCP Context Integration**: Seamless integration with MCP's built-in Context system

---

## 🧭 Payment Flows

The `payment_flow` parameter controls how the user is guided through the payment process. Choose the strategy that fits your use case:

 - **`PaymentFlow.TWO_STEP`** (default)  
  Splits the tool into two separate MCP methods.  
  The first step returns a `payment_url` and a `next_step` method for confirmation.  
  The second method (e.g. `confirm_add_payment`) verifies payment and runs the original logic.  
  Supported in most clients.

- **`PaymentFlow.ELICITATION`** 
  Sends the user a payment link when the tool is invoked. If the client supports it, a payment UI is displayed immediately. Once the user completes payment, the tool proceeds.


- **`PaymentFlow.PROGRESS`**  
  Shows payment link and a progress indicator while the system waits for payment confirmation in the background. The result is returned automatically once payment is completed. 

- **`PaymentFlow.OOB`** *(Out-of-Band)*  
Not yet implemented.

All flows require the MCP client to support the corresponding interaction pattern. When in doubt, start with `TWO_STEP`.

---

## 🚀 Quickstart

**Production Installation:**
```bash
pip install mcp paymcp
```

**Development Setup:**
For detailed setup with all providers, see our [Complete Setup Guide](docs/SETUP_AND_TESTING_GUIDE.md).

```bash
git clone https://github.com/blustAI/paymcp.git
cd paymcp
pip install -e ".[test,dev]"
```

Initialize `PayMCP`:

```python
from mcp.server.fastmcp import FastMCP
from paymcp import PayMCP, price
from paymcp.payment.payment_flow import PaymentFlow

mcp = FastMCP("AI agent name")

# Configure providers
providers = {
    "paypal": {
        "client_id": "your_paypal_client_id",
        "client_secret": "your_paypal_client_secret", 
        "sandbox": True,
        "return_url": "https://yourapp.com/success",
        "cancel_url": "https://yourapp.com/cancel"
    },
    "stripe": {
        "api_key": "sk_test_your_stripe_key"
    }
}

PayMCP(
    mcp,  # your FastMCP instance
    providers=providers,
    payment_flow=PaymentFlow.TWO_STEP  # Recommended default
)
```

Use the `@price` decorator on any tool:

```python
@mcp.tool()
@price(price=0.19, currency="USD")
def add(a: int, b: int, ctx: Context) -> int:
    # `ctx` is automatically injected by MCP's built-in Context system
    # Access payment, user, and execution information
    return a + b
```

**MCP Context Integration:** PayMCP seamlessly integrates with MCP's built-in Context system. Simply add a `ctx: Context` parameter to any paid function, and MCP will automatically inject payment and execution data.

> **Demo server:** For a complete setup, see the example repo: [python-paymcp-server-demo](https://github.com/blustAI/python-paymcp-server-demo).

---

## 📖 Documentation

- 📚 **[Documentation Index](docs/README.md)** - Complete documentation overview
- 🚀 **[Setup & Testing Guide](docs/SETUP_AND_TESTING_GUIDE.md)** - Comprehensive instructions for all providers
- 🧪 **[MCP Server Testing](docs/MCP_TESTING_README.md)** - MCP server validation and testing
- 💳 **[PayPal Provider Guide](src/paymcp/providers/paypal/README.md)** - Detailed PayPal integration docs

### Quick Setup

For development and testing, use our automated setup:

```bash
# Clone and setup
git clone https://github.com/blustAI/paymcp.git
cd paymcp

# Interactive environment setup
python scripts/setup_test_env.py --interactive

# Run comprehensive tests
python scripts/test_all_providers.py --verbose
```

---

## 🧩 Supported Providers

- ✅ **PayPal** - Professional PayPal integration with sandbox/production support
- ✅ **Stripe** - Popular payment processing with comprehensive features  
- ✅ **Walleot** - [Walleot](https://walleot.com/developers) payment provider
- 🔜 Want another provider? Open an issue or submit a pull request!

---

## 📄 License

MIT License