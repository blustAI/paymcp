# PayMCP Server Testing Guide

This guide explains how to test the PayMCP MCP (Model Context Protocol) server functionality using the provided test scripts.

## Prerequisites

1. **Environment Setup**
   ```bash
   # Make sure you're in the project root
   cd paymcp
   
   # Install dependencies (if not already done)
   pip install -e ".[test,dev]"
   ```

2. **Credentials Configuration**
   Ensure your `.env` file contains valid credentials:
   ```bash
   # PayPal Configuration
   PAYPAL_CLIENT_ID=your_paypal_client_id
   PAYPAL_CLIENT_SECRET=your_paypal_client_secret
   PAYPAL_SANDBOX=true
   
   # Stripe Configuration  
   STRIPE_API_KEY=your_stripe_api_key
   STRIPE_SUCCESS_URL=https://yourapp.com/success?session_id={CHECKOUT_SESSION_ID}
   STRIPE_CANCEL_URL=https://yourapp.com/cancel
   ```

## Test Scripts Overview

> 📚 **For detailed technical analysis**: See [MCP_TEST_SCRIPTS_DEEP_DIVE.md](./MCP_TEST_SCRIPTS_DEEP_DIVE.md) for comprehensive documentation including architecture, internal flow, and advanced usage patterns.

| Script | Purpose | Complexity | Test Coverage | Best For |
|--------|---------|------------|---------------|----------|
| `test_mcp_server.py` | Production testing | High | Complete | Pre-production validation |
| `test_mcp_simple.py` | Quick validation | Low | Basic | Development cycles |
| `test_mcp_protocol.py` | Protocol testing | Medium-High | Protocol-focused | MCP compliance |
| `test_mcp_workflow.py` | Workflow demo | Medium | Workflow-focused | Understanding concepts |

### 1. `test_mcp_server.py` - Comprehensive MCP Server Test

**Purpose**: Production-grade comprehensive testing with enterprise reporting

**Key Features**:
- ✅ **6-Phase Testing**: Initialization → Availability → Tools → Payments → Status → Integration
- ✅ **Real API Testing**: Creates actual payments in sandbox mode
- ✅ **Detailed Metrics**: Runtime, success rates, provider-specific results
- ✅ **Enterprise Reporting**: Structured results with actionable recommendations
- ✅ **Error Tracking**: Detailed error messages with troubleshooting guidance

**Usage & Output**:
```bash
python tests/mcp/test_mcp_server.py

# Sample Output:
🚀 PayMCP MCP Server Test Suite
==================================================
[22:09:30] ℹ️  ✅ MCP server initialized with 2 providers
[22:09:30] ℹ️     Available providers: paypal, stripe
[22:09:31] ℹ️  ✅ Paypal payment created: 9UT69499R4530783F
[22:09:33] ℹ️  ✅ Stripe payment created: cs_test_a1IuX...

📊 Total Tests: 11 | ✅ Success Rate: 100.0%
⏱️  Runtime: 2.11 seconds
```

### 2. `test_mcp_simple.py` - Quick MCP Test  

**Purpose**: Rapid validation for development cycles with minimal setup

**Key Features**:
- ✅ **Linear Flow**: Simple start-to-finish execution
- ✅ **Fast Execution**: ~1-2 seconds total runtime
- ✅ **Development-Focused**: Clear output for debugging
- ✅ **Fail-Fast**: Early exit on critical failures

**Usage & Output**:
```bash  
python tests/mcp/test_mcp_simple.py

# Sample Output:
🚀 PayMCP Simple MCP Server Test
========================================
✅ PayPal provider configured
✅ Stripe provider configured  
✅ PayMCP initialized with 2 providers

🧪 Testing PayPal payment...
   Payment ID: 6TU60382P8420183R
   Status: created
🎉 MCP server test completed successfully!
```

### 3. `test_mcp_protocol.py` - MCP Protocol Simulation

**Purpose**: Deep MCP protocol interaction simulation with enhanced MockMCP

**Key Features**:
- ✅ **Enhanced MockMCP**: Automatic schema generation, call history tracking
- ✅ **Tool Discovery**: MCP `list_tools` protocol simulation  
- ✅ **Parameter Validation**: JSON Schema generation from function signatures
- ✅ **Payment Differentiation**: Paid vs free tool behavior testing
- ✅ **Protocol Compliance**: MCP standard interaction patterns

**Usage & Output**:
```bash
python tests/mcp/test_mcp_protocol.py

# Sample Output:
🤖 Simulating MCP Client Interaction
==================================================
1️⃣ Listing available tools...
Found 7 tools:
   • premium_report: Generate a premium report
   • consultation: Book a consultation session  
   • free_summary: Generate a free summary

2️⃣ Calling free tool...
Result: {'result': 'Summary: This is a sample text...'}

5️⃣ Call History:
   1. ✅ free_summary: Summary of content
   2. ✅ premium_report: <coroutine object>
```

### 4. `test_mcp_workflow.py` - Complete Workflow Test

**Purpose**: End-to-end workflow demonstration showing complete integration lifecycle

**Key Features**:
- ✅ **Workflow Simulation**: Complete payment lifecycle demonstration
- ✅ **Real-World Scenarios**: Practical use case examples (AI analysis, consultations)
- ✅ **Two-Step Flow**: Request → Payment → Confirmation → Execution
- ✅ **Provider Capabilities**: Multi-provider simultaneous testing
- ✅ **Async Support**: Non-blocking operation demonstration

**Usage & Output**:
```bash
python tests/mcp/test_mcp_workflow.py

# Sample Output:
🚀 PayMCP Complete Workflow Test
==================================================
✅ Tools registered: 3

📋 Available Tools:
   • confirm_ai_analysis_payment
   • ai_analysis  
   • basic_info

1️⃣ Testing free tool...
Result: Basic information about machine learning...

2️⃣ Testing paid tool workflow...
This would typically involve:
   a) User calls 'ai_analysis'
   b) System generates payment request
   c) User completes payment
   d) System calls 'confirm_ai_analysis_payment'
   e) Original function executes

3️⃣ Provider Capabilities:
   • Paypal: Payment creation and status checking
     Test Payment ID: 37L11960WP699180N
     Status: created
```

## Understanding MCP Integration

### How PayMCP Works with MCP

1. **Tool Registration**: Functions decorated with `@price()` are automatically registered as MCP tools
2. **Payment Flow**: PayMCP creates two tools for each paid function:
   - Original tool (triggers payment request)
   - Confirmation tool (executes after payment)
3. **Provider Integration**: Multiple payment providers supported simultaneously
4. **Async Support**: Full async/await support for non-blocking operations

### Example Paid Tool

```python
from paymcp.decorators import price

@mcp.tool(name="premium_analysis", description="Perform premium data analysis")
@price(price=15.99, currency="USD")  
def premium_analysis(dataset: str, analysis_type: str):
    """Perform premium analysis on dataset."""
    return f"Premium {analysis_type} analysis completed for {dataset}"
```

### Environment Loading

The test scripts automatically load `.env` files using:
```python
from paymcp.utils.env import load_env_file
load_env_file()  # Loads .env file from current directory
```

Then providers can be used normally:
```python
# PayPal - uses from_env() method
from paymcp.providers.paypal import PayPalConfig, PayPalProvider
config = PayPalConfig.from_env()
paypal_provider = PayPalProvider(config=config)

# Stripe - uses original constructor with loaded env vars
import os
from paymcp.providers.stripe import StripeProvider  
stripe_provider = StripeProvider(api_key=os.getenv('STRIPE_API_KEY'))
```

This creates two MCP tools:
- `premium_analysis` - Initiates payment request
- `confirm_premium_analysis_payment` - Executes after payment confirmation

### Payment Flow Process

1. **Client calls paid tool** → PayMCP creates payment with configured provider
2. **Payment URL returned** → Client redirected to payment page  
3. **User completes payment** → Provider processes payment
4. **Payment confirmed** → Client calls confirmation tool
5. **Original function executes** → Results returned to client

## Troubleshooting

### Common Issues

1. **Missing credentials**
   ```
   ⚠️ PayPal credentials not found
   ```
   **Solution**: Check `.env` file has valid `PAYPAL_CLIENT_ID` and `PAYPAL_CLIENT_SECRET`

2. **Import errors**
   ```
   ModuleNotFoundError: No module named 'paymcp'
   ```
   **Solution**: Run from project root and ensure `pip install -e .` was successful

3. **Payment creation fails**
   ```
   ❌ PayPal payment creation failed
   ```
   **Solution**: Verify credentials are valid and network connectivity is available

### Debug Mode

For verbose debugging, modify test scripts to include:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Production Considerations

### Security
- ✅ All credentials loaded from environment variables
- ✅ Sensitive data masked in logs
- ✅ HTTPS-only payment URLs
- ✅ Sandbox mode for testing

### Performance  
- ✅ Async operations for non-blocking payment processing
- ✅ Connection pooling for API requests
- ✅ Token caching for improved performance
- ✅ Configurable timeouts and retries

### Monitoring
- ✅ Comprehensive logging
- ✅ Error tracking and reporting
- ✅ Payment status monitoring
- ✅ Provider health checking

## Next Steps

1. **Custom Provider**: Add your own payment provider by extending the base provider class
2. **Advanced Tools**: Create more complex paid tools with custom validation
3. **Webhook Integration**: Implement webhook handlers for real-time payment updates  
4. **Production Deployment**: Configure for production with proper credentials and monitoring

## Quick Reference

### Script Selection Guide
```bash
# During development
python tests/mcp/test_mcp_simple.py      # Quick validation (1-2s)

# Before deployment  
python tests/mcp/test_mcp_server.py      # Full testing (2-3s)

# Understanding workflows
python tests/mcp/test_mcp_workflow.py    # Concept demonstration

# Protocol compliance
python tests/mcp/test_mcp_protocol.py    # MCP standard testing
```

### Common Test Patterns
```bash
# Test specific provider only
# (Modify script to comment out unwanted providers)

# Test without credentials
# (Scripts gracefully handle missing credentials)

# Test with verbose debugging
# (Add logging.basicConfig(level=logging.DEBUG) to scripts)

# Test performance
# (Scripts include runtime metrics)
```

### Expected Test Results
- **All providers configured**: 100% success rate
- **Partial providers**: Warnings but no failures  
- **No providers**: Initialization success, payment tests skipped
- **Invalid credentials**: Clear error messages with guidance

## Support

- 📋 Check test output for specific error details
- 🔍 Review logs for debugging information  
- 📖 Refer to provider documentation for API-specific issues
- 🧪 Use test scripts to validate configuration changes
- 📚 See [MCP_TEST_SCRIPTS_DEEP_DIVE.md](./MCP_TEST_SCRIPTS_DEEP_DIVE.md) for technical details