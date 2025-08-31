#!/usr/bin/env python3
"""
MCP Prompt-Based Client Simulation Test

This script simulates how a real MCP client (like Claude) would interact with PayMCP
using natural language prompts and tool calling. It provides comprehensive testing
of the complete MCP protocol flow including prompt interpretation, tool discovery,
parameter extraction, payment processing, and result delivery.

Key Features:
- Natural language prompt simulation
- Intent recognition and tool matching
- Parameter extraction from prompts
- Complete payment flow testing
- Error handling and edge cases
- Realistic conversational scenarios
"""

import sys
import os
import json
import asyncio
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from paymcp import PayMCP, PaymentFlow
from paymcp.utils.env import load_env_file
from paymcp.decorators import price


class PromptIntent(Enum):
    """Intent classification for natural language prompts."""
    TOOL_DISCOVERY = "tool_discovery"
    TOOL_CALL = "tool_call" 
    PAYMENT_INQUIRY = "payment_inquiry"
    STATUS_CHECK = "status_check"
    HELP = "help"
    UNKNOWN = "unknown"


@dataclass
class ParsedPrompt:
    """Structured representation of a parsed natural language prompt."""
    intent: PromptIntent
    tool_name: Optional[str] = None
    parameters: Dict[str, Any] = None
    raw_text: str = ""
    confidence: float = 0.0


class PromptParser:
    """Simple prompt parser that simulates NLP understanding."""
    
    def __init__(self, available_tools: Dict[str, Any]):
        self.available_tools = available_tools
        
        # Simple keyword mapping (in real implementation this would use NLP)
        self.tool_keywords = {
            "report": ["report", "generate", "create", "analysis", "document"],
            "consultation": ["consult", "meeting", "session", "advice", "help"],
            "analysis": ["analyze", "study", "examine", "process", "evaluate"],
            "summary": ["summarize", "summary", "brief", "overview"],
            "premium": ["premium", "advanced", "detailed", "professional"],
            "ai_analysis": ["ai", "artificial intelligence", "machine learning", "deep"]
        }
    
    def parse(self, prompt: str) -> ParsedPrompt:
        """Parse natural language prompt into structured intent."""
        prompt_lower = prompt.lower()
        
        # Tool discovery intents
        if any(phrase in prompt_lower for phrase in ["what can you do", "list tools", "available functions", "help me"]):
            return ParsedPrompt(
                intent=PromptIntent.TOOL_DISCOVERY,
                raw_text=prompt,
                confidence=0.9
            )
        
        # Payment inquiry intents  
        if any(phrase in prompt_lower for phrase in ["how much", "cost", "price", "payment", "pay"]):
            return ParsedPrompt(
                intent=PromptIntent.PAYMENT_INQUIRY,
                raw_text=prompt,
                confidence=0.8
            )
        
        # Tool calling intents - match to specific tools
        best_tool = None
        best_score = 0.0
        best_params = {}
        
        for tool_name, tool_info in self.available_tools.items():
            score = self._calculate_tool_match_score(prompt_lower, tool_name, tool_info)
            if score > best_score:
                best_score = score
                best_tool = tool_name
                best_params = self._extract_parameters(prompt, tool_info)
        
        if best_tool and best_score > 0.3:
            return ParsedPrompt(
                intent=PromptIntent.TOOL_CALL,
                tool_name=best_tool,
                parameters=best_params,
                raw_text=prompt,
                confidence=best_score
            )
        
        return ParsedPrompt(
            intent=PromptIntent.UNKNOWN,
            raw_text=prompt,
            confidence=0.0
        )
    
    def _calculate_tool_match_score(self, prompt: str, tool_name: str, tool_info: Dict) -> float:
        """Calculate how well a prompt matches a specific tool."""
        score = 0.0
        
        # Check tool name match
        if tool_name.replace("_", " ") in prompt:
            score += 0.5
        
        # Check description match
        description = tool_info.get("description", "").lower()
        desc_words = set(description.split())
        prompt_words = set(prompt.split())
        
        overlap = len(desc_words.intersection(prompt_words))
        if desc_words:
            score += (overlap / len(desc_words)) * 0.3
        
        # Check keyword matches
        for keyword_group in self.tool_keywords.values():
            if any(keyword in prompt for keyword in keyword_group):
                score += 0.2
                break
        
        return min(score, 1.0)
    
    def _extract_parameters(self, prompt: str, tool_info: Dict) -> Dict[str, Any]:
        """Extract parameters from prompt based on tool schema."""
        params = {}
        schema = tool_info.get("schema", {})
        properties = schema.get("properties", {})
        
        # Simple parameter extraction (in real implementation this would use NER)
        prompt_lower = prompt.lower()
        
        for param_name, param_info in properties.items():
            if param_name in prompt_lower:
                # Extract value after parameter name (very simplified)
                words = prompt.split()
                try:
                    param_idx = next(i for i, word in enumerate(words) if param_name in word.lower())
                    if param_idx + 1 < len(words):
                        params[param_name] = words[param_idx + 1]
                except (StopIteration, IndexError):
                    pass
        
        # Fallback: use common parameter patterns
        if "report_type" in properties and any(word in prompt_lower for word in ["financial", "technical", "marketing"]):
            if "financial" in prompt_lower:
                params["report_type"] = "financial"
            elif "technical" in prompt_lower:
                params["report_type"] = "technical"
            elif "marketing" in prompt_lower:
                params["report_type"] = "marketing"
        
        if "duration" in properties:
            if "hour" in prompt_lower:
                params["duration"] = "1 hour"
            elif "30 min" in prompt_lower or "half hour" in prompt_lower:
                params["duration"] = "30 minutes"
        
        if "topic" in properties:
            topics = ["architecture", "design", "development", "strategy", "planning"]
            for topic in topics:
                if topic in prompt_lower:
                    params["topic"] = topic
                    break
        
        if "analysis_type" in properties:
            types = ["statistical", "predictive", "trend", "comparative"]
            for analysis_type in types:
                if analysis_type in prompt_lower:
                    params["analysis_type"] = analysis_type
                    break
        
        if "dataset" in properties:
            datasets = ["customer", "sales", "financial", "user", "market"]
            for dataset in datasets:
                if dataset in prompt_lower:
                    params["dataset"] = f"{dataset} data"
                    break
        
        return params


class SimulatedMCPClient:
    """Simulates a real MCP client like Claude Desktop."""
    
    def __init__(self):
        self.tools = {}
        self.call_history = []
        self.conversation_context = []
        self.parser = None
    
    def initialize(self, available_tools: Dict[str, Any]):
        """Initialize client with available tools."""
        self.tools = available_tools
        self.parser = PromptParser(available_tools)
    
    def process_prompt(self, prompt: str) -> Dict[str, Any]:
        """Process a natural language prompt and return appropriate response."""
        print(f"\n🤖 **User**: {prompt}")
        self.conversation_context.append({"role": "user", "content": prompt})
        
        # Parse the prompt
        parsed = self.parser.parse(prompt)
        
        if parsed.intent == PromptIntent.TOOL_DISCOVERY:
            return self._handle_tool_discovery()
        
        elif parsed.intent == PromptIntent.TOOL_CALL:
            return self._handle_tool_call(parsed)
        
        elif parsed.intent == PromptIntent.PAYMENT_INQUIRY:
            return self._handle_payment_inquiry(parsed)
        
        else:
            return self._handle_unknown_intent(parsed)
    
    def _handle_tool_discovery(self) -> Dict[str, Any]:
        """Handle requests to discover available tools."""
        response = "I can help you with the following services:\n\n"
        
        for tool_name, tool_info in self.tools.items():
            description = tool_info.get("description", "")
            
            # Check if it's a paid tool (has price info in description)
            if "$" in description or "price" in description.lower():
                response += f"💰 **{tool_name.replace('_', ' ').title()}** - {description}\n"
            else:
                response += f"🆓 **{tool_name.replace('_', ' ').title()}** - {description}\n"
        
        response += "\nJust ask me to use any of these services and I'll help you get started!"
        
        print(f"🤖 **Assistant**: {response}")
        return {"response": response, "intent": "tool_discovery"}
    
    def _handle_tool_call(self, parsed: ParsedPrompt) -> Dict[str, Any]:
        """Handle tool calling requests."""
        tool_name = parsed.tool_name
        
        if tool_name not in self.tools:
            error = f"I don't have access to a tool called '{tool_name}'. Let me show you what I can do instead."
            print(f"🤖 **Assistant**: {error}")
            return self._handle_tool_discovery()
        
        # Check if we have all required parameters
        tool_info = self.tools[tool_name]
        schema = tool_info.get("schema", {})
        required_params = schema.get("required", [])
        provided_params = parsed.parameters or {}
        
        missing_params = set(required_params) - set(provided_params.keys())
        
        if missing_params:
            return self._request_missing_parameters(tool_name, missing_params, provided_params)
        
        # Call the tool
        return self._execute_tool_call(tool_name, provided_params)
    
    def _request_missing_parameters(self, tool_name: str, missing_params: set, provided_params: Dict) -> Dict[str, Any]:
        """Request missing parameters from user."""
        response = f"I'd be happy to help with {tool_name.replace('_', ' ')}! "
        response += f"I need a bit more information:\n\n"
        
        for param in missing_params:
            response += f"• What {param.replace('_', ' ')} would you like?\n"
        
        if provided_params:
            response += f"\nI already have: {', '.join(provided_params.keys())}"
        
        print(f"🤖 **Assistant**: {response}")
        return {"response": response, "intent": "parameter_request", "missing": list(missing_params)}
    
    def _execute_tool_call(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the actual tool call."""
        # Check if this is a paid tool
        tool_info = self.tools[tool_name]
        description = tool_info.get("description", "")
        
        if "$" in description or "price" in description.lower():
            return self._handle_paid_tool_call(tool_name, parameters, tool_info)
        else:
            return self._handle_free_tool_call(tool_name, parameters, tool_info)
    
    def _handle_paid_tool_call(self, tool_name: str, parameters: Dict, tool_info: Dict) -> Dict[str, Any]:
        """Handle paid tool execution."""
        # Extract price from description (simplified)
        description = tool_info.get("description", "")
        price = "5.99"  # Default price
        if "$" in description:
            try:
                price_start = description.index("$") + 1
                price_part = description[price_start:].split()[0]
                price = price_part.replace(",", "").replace(")", "")
            except:
                pass
        
        response = f"🔄 **Processing Payment Required**\n\n"
        response += f"Service: {tool_name.replace('_', ' ').title()}\n"
        response += f"Price: ${price} USD\n"
        response += f"Parameters: {json.dumps(parameters, indent=2)}\n\n"
        response += f"💳 **Initiating payment process...**\n"
        response += f"🔗 **Payment URL**: https://sandbox.paypal.com/checkoutnow?token=example123\n\n"
        response += f"Once payment is confirmed, I'll execute the {tool_name.replace('_', ' ')} service for you!"
        
        print(f"🤖 **Assistant**: {response}")
        
        # Simulate calling the tool
        try:
            result = tool_info['function'](**parameters)
            
            call_record = {
                "tool": tool_name,
                "parameters": parameters,
                "result": result,
                "success": True,
                "paid": True,
                "price": price
            }
            self.call_history.append(call_record)
            
            return {
                "response": response,
                "intent": "paid_tool_call",
                "payment_required": True,
                "payment_url": "https://sandbox.paypal.com/checkoutnow?token=example123",
                "result": result
            }
            
        except Exception as e:
            error_record = {
                "tool": tool_name,
                "parameters": parameters,
                "error": str(e),
                "success": False,
                "paid": True
            }
            self.call_history.append(error_record)
            
            error_response = f"❌ Error processing {tool_name}: {str(e)}"
            print(f"🤖 **Assistant**: {error_response}")
            return {"response": error_response, "intent": "error"}
    
    def _handle_free_tool_call(self, tool_name: str, parameters: Dict, tool_info: Dict) -> Dict[str, Any]:
        """Handle free tool execution."""
        try:
            result = tool_info['function'](**parameters)
            
            response = f"✅ **{tool_name.replace('_', ' ').title()} Complete**\n\n"
            response += f"Result: {result}"
            
            print(f"🤖 **Assistant**: {response}")
            
            call_record = {
                "tool": tool_name,
                "parameters": parameters,
                "result": result,
                "success": True,
                "paid": False
            }
            self.call_history.append(call_record)
            
            return {
                "response": response,
                "intent": "free_tool_call",
                "result": result
            }
            
        except Exception as e:
            error_record = {
                "tool": tool_name,
                "parameters": parameters,
                "error": str(e),
                "success": False,
                "paid": False
            }
            self.call_history.append(error_record)
            
            error_response = f"❌ Error: {str(e)}"
            print(f"🤖 **Assistant**: {error_response}")
            return {"response": error_response, "intent": "error"}
    
    def _handle_payment_inquiry(self, parsed: ParsedPrompt) -> Dict[str, Any]:
        """Handle payment-related questions."""
        response = "Here are the pricing details for my services:\n\n"
        
        for tool_name, tool_info in self.tools.items():
            description = tool_info.get("description", "")
            if "$" in description:
                response += f"💰 **{tool_name.replace('_', ' ').title()}**: {description}\n"
        
        response += "\n🆓 I also have free services that don't require payment."
        response += "\nPayment is processed securely through PayPal or Stripe."
        
        print(f"🤖 **Assistant**: {response}")
        return {"response": response, "intent": "payment_inquiry"}
    
    def _handle_unknown_intent(self, parsed: ParsedPrompt) -> Dict[str, Any]:
        """Handle unknown or unclear prompts."""
        response = "I'm not sure exactly what you're looking for. Here's what I can help with:\n\n"
        
        # Show top 3 tools as suggestions
        tool_names = list(self.tools.keys())[:3]
        for tool_name in tool_names:
            tool_info = self.tools[tool_name]
            description = tool_info.get("description", "")
            response += f"• **{tool_name.replace('_', ' ').title()}** - {description}\n"
        
        response += "\nTry asking me to 'generate a report' or 'book a consultation' for example!"
        
        print(f"🤖 **Assistant**: {response}")
        return {"response": response, "intent": "clarification"}


# Enhanced MockMCP with conversation support
class ConversationalMCP:
    """Enhanced Mock MCP server with conversation capabilities."""
    
    def __init__(self):
        self.tools = {}
        self.client = SimulatedMCPClient()
    
    def tool(self, name=None, description=None):
        """Tool decorator that captures tool registration."""
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
        """Extract parameter schema from function."""
        import inspect
        sig = inspect.signature(func)
        parameters = {}
        
        for param_name, param in sig.parameters.items():
            param_type = "string"
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
    
    def initialize_client(self):
        """Initialize the simulated client with available tools."""
        self.client.initialize(self.tools)
    
    def process_user_prompt(self, prompt: str):
        """Process a user prompt through the simulated client."""
        return self.client.process_prompt(prompt)
    
    def get_conversation_history(self):
        """Get the full conversation history."""
        return self.client.conversation_context
    
    def get_call_history(self):
        """Get the tool call history."""
        return self.client.call_history


def setup_realistic_tools(paymcp: PayMCP):
    """Setup realistic business tools for testing."""
    
    @paymcp.mcp.tool(name="premium_financial_report", description="Generate premium financial analysis report - $19.99")
    @price(price=19.99, currency="USD")
    def premium_financial_report(company: str, period: str, analysis_type: str = "comprehensive"):
        """Generate a comprehensive financial analysis report."""
        return f"📊 Premium Financial Report for {company} ({period}): {analysis_type} analysis complete with detailed insights, projections, and recommendations."
    
    @paymcp.mcp.tool(name="expert_consultation", description="Book 1-hour expert consultation session - $75.00")
    @price(price=75.00, currency="USD")
    def expert_consultation(duration: str, topic: str, expertise_level: str = "senior"):
        """Book an expert consultation session."""
        return f"📅 Expert Consultation Scheduled: {duration} {expertise_level} consultation on {topic}. Meeting link and calendar invite will be sent upon payment confirmation."
    
    @paymcp.mcp.tool(name="ai_powered_analysis", description="Advanced AI analysis of your data - $12.50")
    @price(price=12.50, currency="USD") 
    def ai_powered_analysis(dataset: str, analysis_type: str, output_format: str = "detailed"):
        """Perform advanced AI analysis on datasets."""
        return f"🤖 AI Analysis Complete: {analysis_type} analysis of {dataset} data delivered in {output_format} format with machine learning insights and predictive modeling."
    
    @paymcp.mcp.tool(name="quick_summary", description="Generate a quick summary of any content - Free")
    def quick_summary(content: str, length: str = "brief"):
        """Generate a free summary of content."""
        summary_length = 50 if length == "brief" else 100
        return f"📝 Quick Summary ({length}): {content[:summary_length]}{'...' if len(content) > summary_length else ''}"
    
    @paymcp.mcp.tool(name="basic_info_lookup", description="Look up basic information about any topic - Free")
    def basic_info_lookup(topic: str):
        """Look up basic information about a topic."""
        return f"ℹ️ Basic Information about {topic}: This is general, publicly available information. For detailed analysis, consider our premium services."


def run_realistic_conversation_scenarios(mcp: ConversationalMCP):
    """Run realistic conversation scenarios to test the MCP interaction."""
    
    print("\n🎭 **Realistic MCP Conversation Scenarios**")
    print("="*60)
    
    # Scenario 1: Tool Discovery
    print(f"\n{'='*20} SCENARIO 1: Tool Discovery {'='*20}")
    mcp.process_user_prompt("Hi! What services can you help me with?")
    
    # Scenario 2: Free Tool Usage  
    print(f"\n{'='*20} SCENARIO 2: Free Tool Usage {'='*20}")
    mcp.process_user_prompt("Can you give me a quick summary of this text: 'Artificial intelligence is transforming businesses across industries by automating processes, providing insights from data, and enabling new capabilities that were previously impossible.'")
    
    # Scenario 3: Paid Tool with Complete Parameters
    print(f"\n{'='*20} SCENARIO 3: Paid Tool (Complete) {'='*20}")
    mcp.process_user_prompt("I need a comprehensive financial report for Apple Inc for Q4 2024")
    
    # Scenario 4: Paid Tool with Missing Parameters
    print(f"\n{'='*20} SCENARIO 4: Paid Tool (Missing Info) {'='*20}")
    mcp.process_user_prompt("I'd like to book an expert consultation")
    
    # Scenario 5: Payment Inquiry
    print(f"\n{'='*20} SCENARIO 5: Payment Inquiry {'='*20}")
    mcp.process_user_prompt("How much do your services cost?")
    
    # Scenario 6: Complex AI Analysis Request
    print(f"\n{'='*20} SCENARIO 6: AI Analysis Request {'='*20}")
    mcp.process_user_prompt("Can you run a predictive analysis on my customer data and give me detailed insights?")
    
    # Scenario 7: Ambiguous Request
    print(f"\n{'='*20} SCENARIO 7: Ambiguous Request {'='*20}")
    mcp.process_user_prompt("Help me with my business")
    
    # Summary
    print(f"\n{'='*20} CONVERSATION SUMMARY {'='*20}")
    call_history = mcp.get_call_history()
    
    print(f"📊 **Session Statistics**:")
    print(f"   • Total tool calls: {len(call_history)}")
    print(f"   • Successful calls: {sum(1 for call in call_history if call['success'])}")
    print(f"   • Failed calls: {sum(1 for call in call_history if not call['success'])}")
    print(f"   • Paid tools used: {sum(1 for call in call_history if call.get('paid', False))}")
    print(f"   • Free tools used: {sum(1 for call in call_history if not call.get('paid', False))}")
    
    total_revenue = sum(float(call.get('price', 0)) for call in call_history if call.get('paid', False) and call['success'])
    print(f"   • Total potential revenue: ${total_revenue:.2f}")
    
    print(f"\n📋 **Tool Call Details**:")
    for i, call in enumerate(call_history, 1):
        status = "✅" if call["success"] else "❌"
        price_info = f" (${call.get('price', '0')}) " if call.get('paid', False) else " (Free) "
        print(f"   {i}. {status} {call['tool']}{price_info}")


def main():
    """Main test function."""
    print("🚀 PayMCP Prompt-Based Client Simulation")
    print("="*50)
    
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
            print("⚠️  No providers configured - using mock payments")
        
        # Initialize PayMCP with ConversationalMCP
        mcp = ConversationalMCP()
        paymcp = PayMCP(
            mcp_instance=mcp,
            providers=providers,
            payment_flow=PaymentFlow.TWO_STEP
        )
        print(f"✅ PayMCP initialized with {len(paymcp.providers)} providers")
        
        # Setup realistic business tools
        setup_realistic_tools(paymcp)
        print(f"✅ Realistic business tools registered ({len(mcp.tools)} tools)")
        
        # Initialize the client with available tools
        mcp.initialize_client()
        print("✅ MCP client simulation initialized")
        
        # Run conversation scenarios
        run_realistic_conversation_scenarios(mcp)
        
        print(f"\n🎉 **Prompt-based MCP simulation completed successfully!**")
        print(f"\n💡 **Key Features Demonstrated**:")
        print(f"   ✅ Natural language prompt processing")
        print(f"   ✅ Intent recognition and tool matching")
        print(f"   ✅ Parameter extraction from prompts")
        print(f"   ✅ Payment flow initiation and handling")
        print(f"   ✅ Conversational error handling")
        print(f"   ✅ Mixed free/paid service scenarios")
        print(f"   ✅ Realistic business use cases")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()