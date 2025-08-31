# PayPal Payment Provider

**The definitive PayPal implementation for PayMCP with professional-grade features and best practices.**

## 🌟 **Why This Is The Best PayPal Provider**

### ✅ **MCP Compatible**
- **Same interface as StripeProvider** - Drop-in replacement
- **Works with existing MCP tools** and `@price` decorators  
- **Seamless AI model integration** for paid capabilities

### ✅ **Zero Hardcoded Values**
- **Fully configurable** - URLs, timeouts, currencies, limits
- **Environment-driven** - Load from env vars or config files
- **Sandbox/Production** - Easy environment switching

### ✅ **Professional Implementation**
- **SOLID principles** - Clean architecture, dependency injection
- **Comprehensive validation** - PayPal-specific business rules
- **Thread-safe operations** - Safe for concurrent usage
- **Resilient HTTP client** - Retry logic, connection pooling

### ✅ **Production Ready**
- **Detailed error handling** - Specific exception types
- **Security best practices** - HTTPS enforcement, input sanitization
- **Comprehensive logging** - Full audit trail
- **Health checks** - Monitor PayPal connectivity

## 🚀 **Quick Start**

### **Basic MCP Usage**
```python
from paymcp import PayMCP
from paymcp.decorators import price

# Configure PayPal provider  
providers = {
    "paypal": {
        "client_id": "your_paypal_client_id",
        "client_secret": "your_paypal_client_secret", 
        "sandbox": True,
        "return_url": "https://yourapp.com/success",
        "cancel_url": "https://yourapp.com/cancel"
    }
}

# Initialize PayMCP
paymcp = PayMCP(mcp_instance, providers=providers)

# Define paid AI tool
@mcp.tool(description="Premium AI analysis")
@price(price=19.99, currency="USD")
async def ai_analysis(data: str):
    """Perform advanced AI analysis."""
    return {"analysis": "AI results here"}
```

### **Direct Provider Usage**
```python
from paymcp.providers.paypal import PayPalProvider

# Create provider
provider = PayPalProvider(
    client_id="your_client_id",
    client_secret="your_client_secret",
    sandbox=True,
    brand_name="My AI Platform",
    currencies=["USD", "EUR", "GBP"],
    min_amount=0.99,
    max_amount=999.99
)

# Create payment (MCP interface)
payment_id, approval_url = provider.create_payment(29.99, "USD", "AI Service")
print(f"Pay here: {approval_url}")

# Check status (MCP interface)
status = provider.get_payment_status(payment_id)
print(f"Payment status: {status}")  # Returns "paid", "pending", etc.
```

## ⚙️ **Configuration Options**

### **Complete Configuration**
```python
from paymcp.providers.paypal import PayPalProvider

provider = PayPalProvider(
    # Required credentials
    client_id="your_paypal_client_id",
    client_secret="your_paypal_client_secret",
    
    # Environment
    sandbox=True,  # False for production
    
    # Payment URLs
    return_url="https://yourapp.com/payment/success",
    cancel_url="https://yourapp.com/payment/cancel", 
    webhook_url="https://yourapp.com/webhooks/paypal",  # Optional
    
    # Branding & Localization
    brand_name="Your Company Name",
    locale="en-US",  # "fr-FR", "de-DE", "es-ES", etc.
    
    # Payment Settings
    currencies=["USD", "EUR", "GBP", "CAD", "AUD"],
    min_amount=1.00,
    max_amount=5000.00,
    
    # Technical Settings
    timeout=30,  # Request timeout in seconds
    retry_attempts=3,  # Number of retries for failed requests
)
```

### **Environment Variables**
```bash
# Set PayPal credentials
export PAYPAL_CLIENT_ID="your_sandbox_client_id"
export PAYPAL_CLIENT_SECRET="your_sandbox_client_secret"

# Optional configuration
export PAYPAL_SANDBOX="true"
export PAYPAL_RETURN_URL="https://yourapp.com/success"
export PAYPAL_CANCEL_URL="https://yourapp.com/cancel"
export PAYPAL_BRAND_NAME="Your App Name"
export PAYPAL_CURRENCIES="USD,EUR,GBP"
export PAYPAL_MIN_AMOUNT="1.00"
export PAYPAL_MAX_AMOUNT="10000.00"
```

```python
# Load from environment
from paymcp.providers.paypal.config import PayPalConfig

config = PayPalConfig.from_env("PAYPAL")
provider = PayPalProvider.from_config(config)
```

## 📋 **Key Features**

### **PayPal-Specific Validation**
```python
from paymcp.providers.paypal import PayPalValidator

validator = PayPalValidator(
    supported_currencies=["USD", "EUR", "GBP"],
    min_amount=0.99,
    max_amount=999.99
)

# Comprehensive validation
try:
    validated = validator.validate_complete_payment(
        amount=29.99,
        currency="USD", 
        description="AI Service Payment",
        reference_id="order-12345",
        metadata={"user_id": "123", "plan": "premium"}
    )
    print("✅ Payment valid:", validated)
except PayPalValidationError as e:
    print("❌ Validation failed:", e)
```

### **Enhanced Status Management**
```python
# Get detailed status information
result = provider.get_payment_status_enhanced(payment_id)

print(f"Status: {result.status.value}")
print(f"Amount: {result.money.format()}")
print(f"Successful: {result.is_successful()}")
print(f"Needs action: {result.is_actionable()}")
```

### **Payment Lifecycle Management**
```python
# 1. Create payment
payment_id, approval_url = provider.create_payment(99.99, "USD", "Premium Service")

# 2. User completes payment at PayPal
# ...

# 3. Capture the payment
capture_result = provider.capture_payment(payment_id)
print(f"Captured: {capture_result.money.format()}")

# 4. Refund if needed
refund_result = provider.refund_payment(
    capture_id="capture_id_from_capture_result",
    amount=50.00,  # Partial refund
    currency="USD",
    reason="Customer request"
)
print(f"Refunded: {refund_result.amount.format()}")
```

## 🔍 **Advanced Usage**

### **Multiple Currencies**
```python
# Configure for global usage
provider = PayPalProvider(
    client_id=client_id,
    client_secret=client_secret,
    currencies=["USD", "EUR", "GBP", "CAD", "AUD", "JPY"],
    sandbox=True
)

# Create payments in different currencies
usd_payment = provider.create_payment(29.99, "USD", "US Customer")
eur_payment = provider.create_payment(24.99, "EUR", "EU Customer")
gbp_payment = provider.create_payment(21.99, "GBP", "UK Customer")
```

### **Custom Validation Rules**
```python
from paymcp.providers.paypal import PayPalValidator

# Create validator with custom rules
validator = PayPalValidator(
    supported_currencies=["USD", "EUR"],
    min_amount=5.00,  # Higher minimum
    max_amount=1000.00  # Lower maximum
)

# Validate specific requirements
def validate_subscription_payment(amount, currency, plan_type):
    # Business-specific validation
    if plan_type == "premium" and amount < 19.99:
        raise ValidationError("Premium plan minimum is $19.99")
    
    if plan_type == "enterprise" and amount < 99.99:
        raise ValidationError("Enterprise plan minimum is $99.99")
    
    # Use PayPal validator for technical validation
    return validator.validate_complete_payment(amount, currency, f"{plan_type} subscription")
```

### **Error Handling Strategies**
```python
import asyncio
from paymcp.providers.paypal import PayPalProvider, PaymentError, AuthenticationError

async def robust_payment_processing(provider, amount, currency, description):
    """Handle payments with comprehensive error recovery."""
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            payment_id, approval_url = provider.create_payment(amount, currency, description)
            return {"success": True, "payment_id": payment_id, "url": approval_url}
            
        except AuthenticationError as e:
            # Don't retry auth errors
            return {"success": False, "error": "Authentication failed", "retry": False}
            
        except PaymentError as e:
            if "network" in str(e).lower() and attempt < max_retries - 1:
                # Retry network errors with backoff
                await asyncio.sleep(2 ** attempt)
                continue
            return {"success": False, "error": str(e), "retry": attempt < max_retries - 1}
        
        except ValueError as e:
            # Don't retry validation errors
            return {"success": False, "error": f"Invalid parameters: {e}", "retry": False}
    
    return {"success": False, "error": "Max retries exceeded", "retry": False}
```

### **Health Monitoring**
```python
# Check PayPal connectivity
health = provider.health_check()
print(f"PayPal Status: {health['status']}")
print(f"Connected: {health['paypal_connected']}")
print(f"Environment: {health['environment']}")

# Integration with monitoring systems
def monitor_paypal_health():
    health = provider.health_check()
    if health['status'] != 'healthy':
        send_alert(f"PayPal connectivity issue: {health.get('error')}")
    
    # Send metrics
    send_metric('paypal.health', 1 if health['status'] == 'healthy' else 0)
```

## 🧪 **Testing**

### **Unit Tests**
```bash
# Run from project root directory (paymcp-main/)

# Test all PayPal components
python -m pytest tests/unit/paypal/ -v

# Test specific components  
python -m pytest tests/unit/paypal/test_config.py -v
python -m pytest tests/unit/paypal/test_validator.py -v
python -m pytest tests/unit/paypal/test_paypal_provider.py -v

# Test with coverage
python -m pytest tests/unit/paypal/ --cov=paymcp.providers.paypal --cov-report=html
```

### **Integration Tests**
```bash
# Set PayPal sandbox credentials
export PAYPAL_CLIENT_ID="your_sandbox_client_id" 
export PAYPAL_CLIENT_SECRET="your_sandbox_client_secret"

# Run PayPal integration tests
python -m pytest tests/unit/paypal/test_integration.py -v

# Run comprehensive provider tests (includes PayPal)
python scripts/test_all_providers.py --provider paypal

# Run MCP integration tests with PayPal
python tests/mcp/test_mcp_server.py
```

### **Mock Testing for Development**
```python
from unittest.mock import patch, Mock
from paymcp.providers.paypal import PayPalProvider

# Mock PayPal API responses for testing
@patch('paymcp.providers.paypal.provider.PayPalHTTPClient')
def test_payment_flow(mock_http_client):
    mock_client = Mock()
    mock_client.request.return_value = {
        "id": "ORDER123",
        "status": "CREATED",
        "links": [{"rel": "approve", "href": "https://paypal.com/approve"}]
    }
    mock_http_client.return_value = mock_client
    
    provider = PayPalProvider(client_id="test", client_secret="test")
    payment_id, url = provider.create_payment(10.0, "USD", "Test")
    
    assert payment_id == "ORDER123"
    assert "paypal.com" in url
```

## 🔐 **Security Best Practices**

### **Credential Management**
```python
# ✅ Use environment variables
import os
provider = PayPalProvider(
    client_id=os.getenv("PAYPAL_CLIENT_ID"),
    client_secret=os.getenv("PAYPAL_CLIENT_SECRET")
)

# ❌ Never hardcode credentials
provider = PayPalProvider(
    client_id="hardcoded_id",  # DON'T DO THIS
    client_secret="hardcoded_secret"  # DON'T DO THIS
)
```

### **HTTPS Enforcement**
```python
# ✅ All URLs automatically validated for HTTPS in production
provider = PayPalProvider(
    client_id=client_id,
    client_secret=client_secret,
    sandbox=False,  # Production
    return_url="https://secure-site.com/success",  # ✅ HTTPS required
    cancel_url="https://secure-site.com/cancel"    # ✅ HTTPS required
)

# ❌ HTTP URLs will be rejected in production
# return_url="http://insecure.com/success"  # Will raise ConfigurationError
```

### **Input Validation**
```python
# All inputs are automatically validated:
# ✅ Amount: positive, within limits, proper decimal places
# ✅ Currency: 3-letter code, PayPal-supported, configured
# ✅ Description: non-empty, safe characters, length limits
# ✅ URLs: valid format, HTTPS enforcement
# ✅ Metadata: key-value validation, size limits

try:
    provider.create_payment(-10.0, "USD", "Invalid")  # ❌ Negative amount
except RuntimeError as e:
    print(f"Validation caught: {e}")

try:
    provider.create_payment(10.0, "XYZ", "Invalid")  # ❌ Invalid currency
except RuntimeError as e:
    print(f"Validation caught: {e}")
```

## 🌍 **Production Deployment**

### **Docker Configuration**
```yaml
# docker-compose.yml
services:
  paypal-app:
    environment:
      - PAYPAL_CLIENT_ID=${PAYPAL_CLIENT_ID}
      - PAYPAL_CLIENT_SECRET=${PAYPAL_CLIENT_SECRET}
      - PAYPAL_SANDBOX=false  # Production
      - PAYPAL_RETURN_URL=https://yourapp.com/payment/success
      - PAYPAL_CANCEL_URL=https://yourapp.com/payment/cancel
      - PAYPAL_WEBHOOK_URL=https://yourapp.com/webhooks/paypal
      - PAYPAL_BRAND_NAME=Your Production App
      - PAYPAL_CURRENCIES=USD,EUR,GBP,CAD
```

### **Kubernetes Configuration**
```yaml
# k8s-secret.yml
apiVersion: v1
kind: Secret
metadata:
  name: paypal-credentials
type: Opaque
stringData:
  client-id: "your_production_client_id"
  client-secret: "your_production_client_secret"

---
# k8s-deployment.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: paypal-service
spec:
  template:
    spec:
      containers:
      - name: app
        env:
        - name: PAYPAL_CLIENT_ID
          valueFrom:
            secretKeyRef:
              name: paypal-credentials
              key: client-id
        - name: PAYPAL_CLIENT_SECRET
          valueFrom:
            secretKeyRef:
              name: paypal-credentials
              key: client-secret
        - name: PAYPAL_SANDBOX
          value: "false"
```

### **Monitoring & Alerting**
```python
# Integration with monitoring systems
def setup_paypal_monitoring(provider):
    """Set up comprehensive PayPal monitoring."""
    
    # Health check endpoint
    @app.route('/health/paypal')
    def paypal_health():
        health = provider.health_check()
        return jsonify(health), 200 if health['status'] == 'healthy' else 503
    
    # Metrics collection
    def collect_paypal_metrics():
        try:
            # Test authentication
            health = provider.health_check()
            metrics.gauge('paypal.health', 1 if health['status'] == 'healthy' else 0)
            
            # Monitor token expiration
            if hasattr(provider.token_manager, 'token_expires_at'):
                expires_in = provider.token_manager.token_expires_at - time.time()
                metrics.gauge('paypal.token.expires_in_seconds', expires_in)
            
        except Exception as e:
            metrics.increment('paypal.monitoring.errors')
            logger.error(f"PayPal monitoring error: {e}")
    
    # Schedule monitoring
    scheduler.add_job(collect_paypal_metrics, 'interval', minutes=5)
```

## 📊 **Performance Optimization**

### **Connection Pooling**
```python
# Built-in connection pooling
provider = PayPalProvider(
    client_id=client_id,
    client_secret=client_secret,
    timeout=30,  # Reasonable timeout
    retry_attempts=3  # Automatic retries
)

# The provider automatically:
# ✅ Reuses HTTP connections
# ✅ Implements retry logic with backoff
# ✅ Manages token lifecycle efficiently
# ✅ Uses connection pooling for high throughput
```

### **Concurrent Usage**
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Thread-safe for concurrent usage
provider = PayPalProvider(client_id=client_id, client_secret=client_secret)

async def process_multiple_payments(payment_requests):
    """Process multiple payments concurrently."""
    with ThreadPoolExecutor(max_workers=10) as executor:
        loop = asyncio.get_event_loop()
        
        tasks = []
        for amount, currency, description in payment_requests:
            task = loop.run_in_executor(
                executor, 
                provider.create_payment, 
                amount, currency, description
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results

# Usage
payments = [(10.0, "USD", "Service 1"), (20.0, "EUR", "Service 2")]
results = await process_multiple_payments(payments)
```

## 📚 **API Reference**

### **PayPalProvider**

#### **Constructor**
```python
PayPalProvider(
    client_id: str,
    client_secret: str,
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
    logger: Optional[logging.Logger] = None
)
```

#### **MCP Interface Methods**
- `create_payment(amount: float, currency: str, description: str) -> Tuple[str, str]`
- `get_payment_status(payment_id: str) -> str`

#### **Enhanced Interface Methods** 
- `create_payment_enhanced(request: PaymentRequest) -> PaymentResult`
- `get_payment_status_enhanced(payment_id: str) -> PaymentResult`
- `capture_payment(payment_id: str) -> PaymentResult`
- `refund_payment(capture_id: str, ...) -> RefundResult`

#### **Utility Methods**
- `get_capabilities() -> ProviderCapabilities`
- `get_configuration() -> Dict[str, Any]`
- `get_order_details(order_id: str) -> Dict[str, Any]`
- `health_check() -> Dict[str, Any]`

### **PayPalValidator**

#### **Validation Methods**
- `validate_amount(amount, currency: str) -> Decimal`
- `validate_currency(currency: str) -> str`
- `validate_description(description: str, max_length: int = 127) -> str`
- `validate_order_id(order_id: str) -> str`
- `validate_complete_payment(...) -> Dict`

### **PayPalConfig**

#### **Configuration Methods**
- `PayPalConfig.from_dict(config_dict: dict) -> PayPalConfig`
- `PayPalConfig.from_env(prefix: str = "PAYPAL") -> PayPalConfig`
- `to_payment_config() -> PaymentConfig`
- `mask_sensitive_data() -> Dict`

## 🎉 **Summary**

The PayPal provider in this module represents the **gold standard** for payment provider implementation:

### **✅ What Makes It The Best**

1. **🔧 Professional Implementation**
   - SOLID principles and clean architecture
   - Comprehensive validation with PayPal-specific rules
   - Thread-safe operations for concurrent usage
   - No hardcoded values - everything configurable

2. **🤖 Perfect MCP Integration**
   - Same interface as StripeProvider
   - Works with existing `@price` decorators
   - Seamless AI model monetization
   - Backward compatibility guaranteed

3. **🛡️ Production-Ready Security**
   - HTTPS enforcement in production
   - Input sanitization and validation
   - Secure credential management
   - Comprehensive error handling

4. **⚡ High Performance**
   - Connection pooling and retry logic
   - Efficient token management
   - Concurrent usage support
   - Health monitoring capabilities

5. **🧪 Thoroughly Tested**
   - Comprehensive unit test coverage
   - Integration tests with PayPal sandbox
   - Mock testing support for development
   - Validation for all edge cases

### **🚀 Ready for Production**

This PayPal provider is ready to handle:
- **High-volume payment processing**
- **Multi-currency global deployments**
- **AI model monetization at scale**
- **Enterprise security requirements**
- **24/7 production reliability**

**The only PayPal provider you'll ever need! 💰🚀**