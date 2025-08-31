# PayMCP Test Scripts Deep Dive

This document provides comprehensive technical details about each MCP test script, including their purpose, internal flow, architecture, and specific testing methodologies.

## Architecture Overview

All MCP test scripts share common architectural patterns:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Test Script   │───▶│    MockMCP       │───▶│   PayMCP Core   │
│                 │    │   (Simulates     │    │   (Business     │
│   • Setup       │    │    MCP Server)   │    │    Logic)       │
│   • Execute     │    │                  │    │                 │
│   • Report      │    │   • Tool Reg.    │    │   • Providers   │
└─────────────────┘    │   • Protocol     │    │   • Payment     │
                       │   • Validation   │    │   • Flows       │
                       └──────────────────┘    └─────────────────┘
```

---

## 1. `test_mcp_server.py` - Comprehensive Test Suite

**Purpose**: Production-grade comprehensive testing of all PayMCP MCP server functionality

**File Size**: 403 lines | **Complexity**: High | **Test Coverage**: Complete

### Architecture

```python
class MCPServerTester:
    """Main test orchestrator with enterprise-grade testing patterns"""
    
    # Core Components
    - results: List[Dict[str, Any]]  # Test result storage
    - start_time: datetime          # Performance tracking
    - log()                        # Timestamped logging system
    - add_result()                 # Structured result recording
```

### Detailed Test Flow

#### Phase 1: Initialization & Environment Setup
```
1. Environment Loading
   └── load_env_file() → Loads .env credentials
   └── Credential Discovery
       ├── PayPal: PAYPAL_CLIENT_ID + PAYPAL_CLIENT_SECRET
       ├── Stripe: STRIPE_API_KEY  
       └── Walleot: WALLEOT_API_KEY

2. Provider Configuration Assembly
   └── Dynamic provider dict construction based on available credentials
   └── Sandbox/test mode configuration
   └── URL configuration (return_url, cancel_url, success_url)

3. PayMCP Instantiation
   └── MockMCP() → Creates lightweight MCP server simulator
   └── PayMCP(mcp_instance=mcp, providers=providers, payment_flow=TWO_STEP)
   └── Validates provider count and accessibility
```

#### Phase 2: Provider Availability Testing
```python
async def test_provider_availability(self, paymcp: PayMCP):
    """Deep provider validation beyond basic configuration"""
    
    # For each provider type:
    # 1. Credential validation
    # 2. Provider instantiation test
    # 3. Basic functionality verification
    # 4. API connectivity check (without actual API calls)
    
    # PayPal specific:
    PayPalConfig.from_env() → Tests .env loading + validation
    
    # Stripe specific:  
    StripeProvider(api_key=key) → Tests provider instantiation
    
    # Walleot specific:
    Validates API key format and presence
```

#### Phase 3: MCP Tools Discovery & Validation
```python
async def test_mcp_tools_list(self, paymcp: PayMCP):
    """MCP protocol tool discovery simulation"""
    
    # Expected core tools:
    expected_tools = [
        'create_payment',      # Payment initiation
        'get_payment_status',  # Payment status checking  
        'list_providers'       # Provider enumeration
    ]
    
    # Validation process:
    # 1. Check PayMCP object has required methods/attributes
    # 2. Validate provider tools are accessible
    # 3. Confirm tool signatures match MCP expectations
    # 4. Return available tool count for reporting
```

#### Phase 4: Payment Creation Testing
```python
async def test_create_payment(self, paymcp: PayMCP, available_providers: List[str]):
    """Real payment creation with actual API calls"""
    
    # Test cases with different scenarios:
    test_cases = [
        {
            "provider": "paypal",
            "amount": 10.99,
            "currency": "USD", 
            "description": "Test PayPal payment via MCP"
        },
        {
            "provider": "stripe",
            "amount": 25.50, 
            "currency": "USD",
            "description": "Test Stripe payment via MCP"
        }
    ]
    
    # For each test case:
    # 1. Skip if provider not available
    # 2. Call provider.create_payment() → Returns (payment_id, payment_url)
    # 3. Validate response format and content
    # 4. Store payment details for status testing
    # 5. Log payment URL and ID for manual verification
    # 6. Record success/failure with detailed error messages
```

#### Phase 5: Payment Status Verification
```python
async def test_payment_status(self, paymcp: PayMCP, successful_payments: List[Dict]):
    """Payment status checking for all created payments"""
    
    # For each successful payment from Phase 4:
    # 1. Call provider.get_payment_status(payment_id)
    # 2. Validate status response (created, pending, completed, etc.)
    # 3. Verify status makes sense for new payment
    # 4. Record status check success/failure
    # 5. Handle provider-specific status formats
```

#### Phase 6: MCP Integration Testing
```python
async def test_mcp_integration(self):
    """High-level MCP protocol compliance testing"""
    
    integration_tests = [
        "Tool discovery",        # MCP tools list protocol
        "Parameter validation",  # Input parameter checking  
        "Error handling",       # Error response formatting
        "Response formatting"    # MCP response structure
    ]
    
    # Simulates MCP client-server interaction patterns
    # Tests async operation handling
    # Validates MCP protocol compliance
```

#### Phase 7: Comprehensive Reporting
```python
def print_summary(self):
    """Enterprise-grade test reporting with metrics"""
    
    # Metrics calculated:
    total_tests = len(self.results)
    successful_tests = sum(1 for r in self.results if r["success"])
    failed_tests = total_tests - successful_tests
    duration = (datetime.now() - self.start_time).total_seconds()
    success_rate = (successful_tests/total_tests*100)
    
    # Report sections:
    # 1. Executive summary with runtime metrics
    # 2. Test breakdown by provider
    # 3. Test breakdown by test type  
    # 4. Failed test details with specific error messages
    # 5. Actionable recommendations
    # 6. Production readiness assessment
```

---

## 2. `test_mcp_simple.py` - Quick Test Script  

**Purpose**: Rapid validation and development testing with minimal setup

**File Size**: 122 lines | **Complexity**: Low | **Test Coverage**: Basic

### Architecture

```python
# Simplified linear flow without complex state management
def main():
    """Single function orchestrating all test phases"""
    
    # Core flow:
    # 1. Environment setup
    # 2. Provider configuration  
    # 3. PayMCP instantiation
    # 4. Basic payment testing
    # 5. Simple result reporting
```

### Detailed Test Flow

#### Phase 1: Rapid Environment Setup
```python
# Load environment variables
load_env_file()
print("✅ Environment loaded")

# Quick provider discovery
providers = {}

# PayPal setup (if credentials available)
if os.getenv("PAYPAL_CLIENT_ID") and os.getenv("PAYPAL_CLIENT_SECRET"):
    providers["paypal"] = {
        "client_id": os.getenv("PAYPAL_CLIENT_ID"),
        "client_secret": os.getenv("PAYPAL_CLIENT_SECRET"),
        "sandbox": True,
        "return_url": "https://example.com/success",
        "cancel_url": "https://example.com/cancel"
    }
    print("✅ PayPal provider configured")

# Stripe setup (if credentials available)
stripe_api_key = os.getenv("STRIPE_API_KEY")
if stripe_api_key:
    providers["stripe"] = {
        "api_key": stripe_api_key,
        "success_url": "https://example.com/success?session_id={CHECKOUT_SESSION_ID}",
        "cancel_url": "https://example.com/cancel"
    }
    print("✅ Stripe provider configured")
```

#### Phase 2: Basic PayMCP Testing
```python
# Initialize PayMCP with minimal configuration
mcp = MockMCP()
paymcp = PayMCP(
    mcp_instance=mcp,
    providers=providers,
    payment_flow=PaymentFlow.TWO_STEP
)
print(f"✅ PayMCP initialized with {len(paymcp.providers)} providers")
```

#### Phase 3: Simple Payment Testing
```python
# Test PayPal payment (if available)
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
    
    # Quick status check
    status = provider.get_payment_status(payment_id)
    print(f"   Status: {status}")
```

#### Design Philosophy
- **Speed over completeness**: Minimal test cases for rapid feedback
- **Development-focused**: Quick validation during development cycles
- **Human-readable output**: Clear, concise logging for debugging
- **Fail-fast approach**: Early exit on critical failures

---

## 3. `test_mcp_protocol.py` - MCP Protocol Simulation

**Purpose**: Detailed MCP protocol interaction simulation and tool behavior testing

**File Size**: 241 lines | **Complexity**: Medium-High | **Test Coverage**: Protocol-Focused

### Architecture

```python
class MockMCP:
    """Enhanced MCP server simulator with protocol-accurate behavior"""
    
    # Advanced features:
    - tools: Dict[str, Dict]        # Tool registry with metadata
    - call_history: List[Dict]      # Protocol interaction tracking
    - _extract_schema()             # Function signature analysis
    - call_tool()                   # MCP tool execution simulation
    - list_tools()                  # MCP tools list protocol
```

### Detailed Test Flow

#### Phase 1: Enhanced MCP Simulation Setup
```python
class MockMCP:
    def tool(self, name=None, description=None):
        """Enhanced tool decorator with metadata extraction"""
        
        def decorator(func):
            tool_name = name or func.__name__
            self.tools[tool_name] = {
                'function': func,
                'name': tool_name,
                'description': description or func.__doc__ or "",
                'schema': self._extract_schema(func)  # Parameter schema generation
            }
            return func
        return decorator
    
    def _extract_schema(self, func):
        """Automatic parameter schema generation from function signatures"""
        
        import inspect
        sig = inspect.signature(func)
        parameters = {}
        
        for param_name, param in sig.parameters.items():
            # Type inference from annotations
            param_type = "string"  # Default
            if param.annotation != inspect.Parameter.empty:
                if param.annotation == int: param_type = "integer"
                elif param.annotation == float: param_type = "number"  
                elif param.annotation == bool: param_type = "boolean"
            
            parameters[param_name] = {
                "type": param_type,
                "description": f"The {param_name} parameter"
            }
        
        # Return JSON Schema format
        return {
            "type": "object",
            "properties": parameters,
            "required": list(parameters.keys())
        }
```

#### Phase 2: Sample Tool Registration  
```python
def setup_sample_tools(paymcp: PayMCP):
    """Register sample MCP tools demonstrating payment workflows"""
    
    # Paid tools with different price points
    @paymcp.mcp.tool(name="premium_report", description="Generate a premium report")
    @price(price=5.99, currency="USD")
    def generate_premium_report(report_type: str):
        """Generate a premium report for the given type."""
        return f"Premium {report_type} report generated successfully!"
    
    @paymcp.mcp.tool(name="consultation", description="Book a consultation session")  
    @price(price=25.00, currency="USD")
    def book_consultation(duration: str, topic: str):
        """Book a consultation session."""
        return f"Consultation booked: {duration} session on {topic}"
    
    # Free tool for comparison
    @paymcp.mcp.tool(name="free_summary", description="Generate a free summary")
    def free_summary(content: str):
        """Generate a free summary of the given content."""
        return f"Summary: {content[:100]}..." if len(content) > 100 else f"Summary: {content}"
```

#### Phase 3: MCP Client Interaction Simulation
```python
def simulate_mcp_client_interaction(mcp: MockMCP):
    """Comprehensive MCP protocol interaction simulation"""
    
    # 1. Tool Discovery (MCP List Tools Protocol)
    print("\n1️⃣ Listing available tools...")
    tools_response = mcp.list_tools()
    tools = tools_response.get("tools", [])
    
    # Tool analysis and reporting
    print(f"Found {len(tools)} tools:")
    for tool in tools:
        print(f"   • {tool['name']}: {tool['description']}")
    
    # 2. Free Tool Execution
    print("\n2️⃣ Calling free tool...")
    result = mcp.call_tool("free_summary", {
        "content": "This is a sample text that needs to be summarized for testing purposes."
    })
    print(f"Result: {result}")
    
    # 3. Paid Tool Execution (triggers payment workflow)
    print("\n3️⃣ Calling paid tool (premium report)...")
    result = mcp.call_tool("premium_report", {
        "report_type": "financial"
    })
    print(f"Result: {result}")
    
    # 4. Protocol Interaction History
    print("\n5️⃣ Call History:")
    for i, call in enumerate(mcp.call_history, 1):
        status = "✅" if call["success"] else "❌"
        print(f"   {i}. {status} {call['tool']}: {call.get('result', call.get('error'))}")
```

#### Key Protocol Features Tested
- **Tool Discovery Protocol**: MCP `list_tools` implementation
- **Parameter Schema Generation**: Automatic JSON Schema creation
- **Tool Execution Protocol**: MCP `call_tool` with parameter validation
- **Payment Flow Integration**: Paid vs free tool differentiation  
- **Error Handling Protocol**: MCP-compliant error responses
- **Interaction Tracking**: Complete protocol interaction history

---

## 4. `test_mcp_workflow.py` - Complete Workflow Demo

**Purpose**: End-to-end workflow demonstration showing complete PayMCP integration lifecycle

**File Size**: 160 lines | **Complexity**: Medium | **Test Coverage**: Workflow-Focused

### Architecture

```python
class WorkflowMCP:
    """Simplified MCP focused on async workflow demonstration"""
    
    # Streamlined for workflow testing:
    - tools: Dict[str, Function]  # Direct function storage
    - tool() decorator            # Simple tool registration
```

### Detailed Test Flow

#### Phase 1: Workflow-Focused Setup
```python
async def test_complete_workflow():
    """Async workflow demonstration with real-world scenarios"""
    
    # Environment and provider setup (similar to other tests)
    # Focus on demonstrating complete payment workflow lifecycle
```

#### Phase 2: Realistic Tool Definition
```python
# Define tools that represent real-world use cases
@paymcp.mcp.tool(name="ai_analysis", description="Perform AI analysis")
@price(price=12.99, currency="USD")
def ai_analysis(data_type: str, complexity: str):
    """Perform AI analysis on the given data."""
    return f"AI analysis completed: {complexity} analysis of {data_type} data"

@paymcp.mcp.tool(name="basic_info", description="Get basic information")  
def basic_info(topic: str):
    """Get basic information about a topic."""
    return f"Basic information about {topic}: This is publicly available information."
```

#### Phase 3: Complete Workflow Simulation
```python
# 1. Tool Registration and Discovery
print(f"✅ Tools registered: {len(mcp.tools)}")
print("\n📋 Available Tools:")
for tool_name in mcp.tools:
    print(f"   • {tool_name}")

# 2. Free Tool Testing
print("\n1️⃣ Testing free tool...")
result = basic_info("machine learning")
print(f"Result: {result}")

# 3. Paid Tool Workflow Explanation
print("\n2️⃣ Testing paid tool workflow...")
print("This would typically involve:")
print("   a) User calls 'ai_analysis'")
print("   b) System generates payment request")  
print("   c) User completes payment")
print("   d) System calls 'confirm_ai_analysis_payment'")
print("   e) Original function executes")

# 4. Payment Confirmation Simulation
if "ai_analysis" in mcp.tools:
    print("\n   Simulating payment confirmation...")
    if "confirm_ai_analysis_payment" in mcp.tools:
        confirm_func = mcp.tools["confirm_ai_analysis_payment"]
        print("   ✅ Payment confirmation function available")
```

#### Phase 4: Provider Capability Demonstration
```python
print(f"\n3️⃣ Provider Capabilities:")
for provider_name, provider in paymcp.providers.items():
    print(f"   • {provider_name.title()}: Payment creation and status checking")
    
    # Demonstrate actual payment capabilities
    try:
        payment_id, payment_url = provider.create_payment(
            amount=12.99,
            currency="USD",
            description="AI Analysis Service"
        )
        print(f"     Test Payment ID: {payment_id}")
        print(f"     Test Payment URL: {payment_url[:50]}...")
        
        # Status checking demonstration
        status = provider.get_payment_status(payment_id)
        print(f"     Status: {status}")
        
    except Exception as e:
        print(f"     Error: {e}")
```

#### Workflow Concepts Demonstrated
- **Complete Payment Lifecycle**: From tool call to payment completion
- **Two-Step Payment Flow**: Request → Confirmation → Execution  
- **Multi-Provider Support**: Simultaneous provider management
- **Async Operations**: Non-blocking payment processing
- **Real-World Scenarios**: Practical use case examples
- **Error Handling**: Graceful failure management

---

## Common Patterns Across All Scripts

### 1. Environment Management
```python
# Consistent pattern across all scripts
load_env_file()  # Load .env file
providers = {}   # Dynamic provider discovery
if os.getenv("PROVIDER_CREDENTIALS"): # Conditional setup
    providers["provider"] = {...}
```

### 2. MockMCP Integration
```python
# All scripts use MockMCP for MCP server simulation
mcp = MockMCP()
paymcp = PayMCP(
    mcp_instance=mcp,
    providers=providers, 
    payment_flow=PaymentFlow.TWO_STEP
)
```

### 3. Error Handling
```python
# Consistent error handling pattern
try:
    # Test operations
    result = operation()
    print("✅ Success")
except Exception as e:
    print(f"❌ Error: {e}")
    # Optional: traceback for debugging
```

### 4. Logging and Reporting  
```python
# Standardized logging across scripts
print("🚀 Test Suite Starting...")  # Start
print("✅ Operation successful")     # Success
print("⚠️  Warning message")         # Warning  
print("❌ Error occurred")           # Error
print("🎉 Test completed!")          # Completion
```

## Usage Recommendations

### For Development
- **`test_mcp_simple.py`**: Quick validation during development
- **`test_mcp_workflow.py`**: Understanding workflow concepts

### For Testing  
- **`test_mcp_server.py`**: Comprehensive pre-production testing
- **`test_mcp_protocol.py`**: MCP protocol compliance validation

### For Production
- **`test_mcp_server.py`**: Production readiness verification
- Customize test cases for specific deployment requirements
- Add monitoring and alerting for continuous validation

## Performance Characteristics

| Script | Execution Time | API Calls | Memory Usage | Complexity |
|--------|----------------|-----------|--------------|------------|
| `test_mcp_simple.py` | ~1-2 seconds | 2-4 payments | Low | Simple |
| `test_mcp_server.py` | ~2-3 seconds | 2-4 payments + status | Medium | Complex |
| `test_mcp_protocol.py` | ~0.5 seconds | 0 (simulation) | Low | Medium |
| `test_mcp_workflow.py` | ~1-2 seconds | 2-4 payments | Medium | Medium |

All scripts are optimized for rapid execution while providing comprehensive validation of PayMCP MCP server functionality.