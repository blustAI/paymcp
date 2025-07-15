# PayMCP

**Provider-agnostic payment layer for MCP (Model Context Protocol) tools and agents.**

`paymcp` is a lightweight SDK that helps you add monetization to your MCP-based tools, servers, or agents. It supports multiple payment providers and integrates seamlessly with MCP's tool/resource interface.

---

## 🔧 Features

- ✅ Add `@price(...)` decorators to your MCP tools to enable payments
- 🔁 Choose between different payment flows (elicit, confirm, etc.)
- 🔌 Pluggable support for providers like Walleot, Stripe, and more
- ⚙️ Easy integration with `FastMCP` or other MCP servers

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

Install the SDK from PyPI:
```bash
pip install paymcp
```

Initialize `PayMCP`:

```python
from paymcp import PayMCP, price, PaymentFlow

PayMCP(
    mcp,  # your FastMCP instance
    providers={
        "provider_name": {"api_key": "your-api-key-here"},
    },
    payment_flow=PaymentFlow.ELICITATION
)
```

Use the `@price` decorator on any tool:

```python
@mcp.tool()
@price(amount=0.19, currency="USD")
def add(a: int, b: int) -> int:
    return a + b
```

---

## 🧩 Supported Providers

- ✅ [Walleot](https://walleot.com/developers)
- ✅ Stripe
- 🔜 Want another provider? Open an issue or submit a pull request!

---

## 📄 License

MIT License