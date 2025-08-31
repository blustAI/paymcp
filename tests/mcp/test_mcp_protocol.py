#!/usr/bin/env python3
"""
MCP Protocol Test

This script demonstrates how to interact with PayMCP using MCP protocol-like commands.
This simulates how an AI client would interact with the PayMCP server.
"""

import sys
import json
import os
from pathlib import Path
from typing import Dict, Any, List

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from paymcp import PayMCP, PaymentFlow
from paymcp.utils.env import load_env_file
from paymcp.decorators import price


class MockMCP:
    """Enhanced Mock MCP server that simulates protocol interactions."""
    
    def __init__(self):
        self.tools = {}
        self.call_history = []
    
    def tool(self, name=None, description=None):
        """Mock tool decorator that captures tool registration."""
        def decorator(func):
            tool_name = name or func.__name__
            self.tools[tool_name] = {
                'function': func,
                'name': tool_name,
                'description': description or func.__doc__ or "",
                'schema': self._extract_schema(func)
            }
            return func
        return decorator
    
    def _extract_schema(self, func):
        """Extract parameter schema from function (simplified)."""
        import inspect
        sig = inspect.signature(func)
        parameters = {}
        
        for param_name, param in sig.parameters.items():
            param_type = "string"  # Simplified - in real MCP this would be more sophisticated
            if param.annotation != inspect.Parameter.empty:
                if param.annotation == int:
                    param_type = "integer"
                elif param.annotation == float:
                    param_type = "number"
                elif param.annotation == bool:
                    param_type = "boolean"
            
            parameters[param_name] = {
                "type": param_type,
                "description": f"The {param_name} parameter"
            }
        
        return {
            "type": "object",
            "properties": parameters,
            "required": list(parameters.keys())
        }
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]):
        """Simulate calling a tool via MCP protocol."""
        if tool_name not in self.tools:
            return {"error": f"Tool '{tool_name}' not found"}
        
        try:
            tool_info = self.tools[tool_name]
            result = tool_info['function'](**arguments)
            
            call_record = {
                "tool": tool_name,
                "arguments": arguments,
                "result": result,
                "success": True
            }
            self.call_history.append(call_record)
            
            return {"result": result}
            
        except Exception as e:
            error_record = {
                "tool": tool_name,
                "arguments": arguments,
                "error": str(e),
                "success": False
            }
            self.call_history.append(error_record)
            
            return {"error": str(e)}
    
    def list_tools(self):
        """List available tools (MCP protocol method)."""
        tools = []
        for tool_name, tool_info in self.tools.items():
            tools.append({
                "name": tool_name,
                "description": tool_info["description"],
                "inputSchema": tool_info["schema"]
            })
        return {"tools": tools}


def setup_sample_tools(paymcp: PayMCP):
    """Setup sample MCP tools that use payment functionality."""
    
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
    
    @paymcp.mcp.tool(name="custom_analysis", description="Perform custom data analysis")
    @price(price=15.50, currency="USD") 
    def custom_analysis(dataset: str, analysis_type: str):
        """Perform custom analysis on the given dataset."""
        return f"Custom {analysis_type} analysis completed for {dataset}"
    
    # Add a free tool for comparison
    @paymcp.mcp.tool(name="free_summary", description="Generate a free summary")
    def free_summary(content: str):
        """Generate a free summary of the given content."""
        return f"Summary: {content[:100]}..." if len(content) > 100 else f"Summary: {content}"


def simulate_mcp_client_interaction(mcp: MockMCP):
    """Simulate how an MCP client would interact with the server."""
    
    print("🤖 Simulating MCP Client Interaction")
    print("="*50)
    
    # 1. List available tools
    print("\n1️⃣ Listing available tools...")
    tools_response = mcp.list_tools()
    tools = tools_response.get("tools", [])
    
    print(f"Found {len(tools)} tools:")
    for tool in tools:
        print(f"   • {tool['name']}: {tool['description']}")
    
    # 2. Call a free tool
    print("\n2️⃣ Calling free tool...")
    result = mcp.call_tool("free_summary", {
        "content": "This is a sample text that needs to be summarized for testing purposes."
    })
    print(f"Result: {result}")
    
    # 3. Call a paid tool (this would trigger payment)
    print("\n3️⃣ Calling paid tool (premium report)...")
    result = mcp.call_tool("premium_report", {
        "report_type": "financial"
    })
    print(f"Result: {result}")
    
    # 4. Call another paid tool
    print("\n4️⃣ Calling paid tool (consultation)...")
    result = mcp.call_tool("consultation", {
        "duration": "1 hour",
        "topic": "software architecture"
    })
    print(f"Result: {result}")
    
    # 5. Show call history
    print("\n5️⃣ Call History:")
    for i, call in enumerate(mcp.call_history, 1):
        status = "✅" if call["success"] else "❌"
        print(f"   {i}. {status} {call['tool']}: {call.get('result', call.get('error'))}")


def main():
    print("🚀 PayMCP Protocol Test")
    print("="*40)
    
    try:
        # Load environment
        load_env_file()
        print("✅ Environment loaded")
        
        # Setup providers
        providers = {}
        
        if os.getenv("PAYPAL_CLIENT_ID") and os.getenv("PAYPAL_CLIENT_SECRET"):
            providers["paypal"] = {
                "client_id": os.getenv("PAYPAL_CLIENT_ID"),
                "client_secret": os.getenv("PAYPAL_CLIENT_SECRET"),
                "sandbox": True,
                "return_url": "https://example.com/success",
                "cancel_url": "https://example.com/cancel"
            }
            print("✅ PayPal configured")
        
        if os.getenv("STRIPE_API_KEY"):
            providers["stripe"] = {
                "api_key": os.getenv("STRIPE_API_KEY"),
                "success_url": "https://example.com/success?session_id={CHECKOUT_SESSION_ID}",
                "cancel_url": "https://example.com/cancel"
            }
            print("✅ Stripe configured")
        
        if not providers:
            print("⚠️  No providers configured - some tests may not work")
        
        # Initialize PayMCP with enhanced MockMCP
        mcp = MockMCP()
        paymcp = PayMCP(
            mcp_instance=mcp,
            providers=providers,
            payment_flow=PaymentFlow.TWO_STEP
        )
        print(f"✅ PayMCP initialized with {len(paymcp.providers)} providers")
        
        # Setup sample tools
        setup_sample_tools(paymcp)
        print(f"✅ Sample tools registered")
        
        # Simulate MCP client interactions
        simulate_mcp_client_interaction(mcp)
        
        print("\n🎉 MCP protocol test completed!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()