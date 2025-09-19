"""
Common utilities for payment flows and MCP tool execution.

This module provides shared utilities that are used across all payment flow
implementations (elicitation, progress, sync, etc.). It centralizes common
patterns to avoid code duplication and ensure consistent behavior.

Key Features:
1. Tool execution: Safe invocation of original tool handlers
2. Argument normalization: Handle various MCP SDK argument formats
3. Flow control: Client abort detection and timing utilities
4. Logging: Consistent structured logging across flows
5. Description generation: Standard tool description formatting

These utilities are designed to work with any MCP client implementation
and provide a stable foundation for payment flow implementations.
"""

import asyncio
import logging
from typing import Any, Callable, Dict, Optional, Tuple


async def call_original_tool(func: Callable, args: Dict[str, Any], kwargs: Dict[str, Any]) -> Any:
    """
    Safely invoke the original tool handler with its arguments after payment.

    This function provides a centralized way to execute the actual tool function
    after payment has been confirmed. It handles both positional and keyword
    arguments correctly and ensures the tool runs in the expected context.

    Critical for payment flows because:
    1. Tool execution must happen AFTER payment confirmation
    2. Original arguments must be preserved exactly
    3. Error handling should be consistent across flows
    4. Both sync and async tool functions need support

    Args:
        func: The original tool function to execute.
              Can be async or sync, MCP SDK handles both.
        args: Positional arguments as a dictionary.
              Format: {"_positional": [arg1, arg2, ...]} or empty dict.
        kwargs: Keyword arguments to pass to the function.
                These are the actual named parameters.

    Returns:
        The return value from the original tool function.
        Type depends on what the tool returns.

    Raises:
        Any exception raised by the original tool function.
        These should propagate to the MCP client for proper error handling.

    Example:
        >>> args = {"_positional": ["hello"]}
        >>> kwargs = {"model": "gpt-4", "temperature": 0.7}
        >>> result = await call_original_tool(generate_text, args, kwargs)
    """
    # Handle arguments based on what was provided
    if args and "_positional" in args:
        # Call with both positional and keyword arguments
        positional = args["_positional"]
        return await func(*positional, **kwargs)
    elif args:
        # Legacy format: args contains keyword arguments
        # Merge with kwargs, giving precedence to kwargs
        merged_args = {**args, **kwargs}
        return await func(**merged_args)
    else:
        # Only keyword arguments provided
        return await func(**kwargs)


def normalize_tool_args(*args, **kwargs) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Normalize tool call arguments from various MCP SDK formats.

    Different MCP clients and SDK versions pass arguments in different ways:
    - Some use only keyword arguments
    - Some mix positional and keyword arguments
    - Some have special handling for certain parameter types

    This function standardizes the format so payment flows can handle
    arguments consistently regardless of the MCP client implementation.

    Args:
        *args: Positional arguments from the MCP tool call.
               These are less common but some tools use them.
        **kwargs: Keyword arguments from the MCP tool call.
                 This is the most common format.

    Returns:
        Tuple of (positional_args_dict, keyword_args_dict):
        - positional_args_dict: Either empty dict or {"_positional": args}
        - keyword_args_dict: All keyword arguments as provided

    Example:
        >>> # Call: generate_text("hello", model="gpt-4")
        >>> args_dict, kwargs_dict = normalize_tool_args("hello", model="gpt-4")
        >>> # args_dict = {"_positional": ["hello"]}
        >>> # kwargs_dict = {"model": "gpt-4"}

        >>> # Call: generate_text(prompt="hello", model="gpt-4")
        >>> args_dict, kwargs_dict = normalize_tool_args(prompt="hello", model="gpt-4")
        >>> # args_dict = {}
        >>> # kwargs_dict = {"prompt": "hello", "model": "gpt-4"}
    """
    # Convert positional args to a standardized format
    args_dict = {}
    if args and len(args) > 0:
        # Store positional args in a special key for later retrieval
        # This preserves the order and distinguishes them from keyword args
        args_dict = {"_positional": list(args)}

    # Keyword args are returned as-is
    # The MCP SDK should have already handled any normalization needed
    return args_dict, kwargs


async def delay(seconds: float) -> None:
    """
    Asynchronous delay utility for payment flow timing.

    This is a simple wrapper around asyncio.sleep that provides consistent
    timing behavior across all payment flows. It's used for:

    1. Polling intervals: Checking payment status periodically
    2. User experience: Giving users time to process payment prompts
    3. Rate limiting: Avoiding overwhelming payment providers
    4. Retry logic: Implementing exponential backoff strategies

    Args:
        seconds: Number of seconds to delay.
                Can be a fractional value (e.g., 0.5 for 500ms).

    Example:
        >>> # Wait 2 seconds before checking payment status again
        >>> await delay(2.0)

        >>> # Brief pause for user experience
        >>> await delay(0.5)
    """
    await asyncio.sleep(seconds)


def is_client_aborted(ctx: Any) -> bool:
    """
    Check if the MCP client has aborted the current operation.

    MCP clients can cancel operations (like when a user closes a window or
    hits Ctrl+C). This function provides a consistent way to detect such
    cancellations across different MCP client implementations.

    Abort detection is important for:
    1. Resource cleanup: Stop payment polling when client disconnects
    2. User experience: Don't show completion messages to disconnected clients
    3. Provider efficiency: Avoid unnecessary API calls
    4. State management: Update payment state appropriately

    Args:
        ctx: MCP context object from the client.
             Different clients implement abort signaling differently.

    Returns:
        True if the client has signaled an abort, False otherwise.
        Returns False if abort detection is not supported by the client.

    Example:
        >>> if is_client_aborted(ctx):
        ...     logger.info("Client aborted, stopping payment check")
        ...     return {"error": "Operation canceled by user"}
    """
    # Check for standard abort signal pattern
    # Some clients provide ctx.signal.aborted (following browser AbortSignal API)
    if hasattr(ctx, 'signal') and hasattr(ctx.signal, 'aborted'):
        return ctx.signal.aborted

    # Future: Could check for other abort patterns as they're discovered
    # e.g., ctx.cancelled, ctx.aborted, ctx.is_cancelled(), etc.

    # Default to not aborted if no signal is available
    return False


def log_flow(
    logger: Optional[logging.Logger],
    flow_name: str,
    level: str,
    message: str,
    *args,
    **kwargs
) -> None:
    """
    Structured logging utility with consistent formatting across payment flows.

    This function provides standardized logging for all payment flows with:
    1. Consistent prefixes: [PayMCP:FlowName] for easy filtering
    2. Fallback handling: Print important messages even without a logger
    3. Level support: All standard Python logging levels
    4. Parameter passing: Supports logger formatting args and kwargs

    Structured logging is crucial for:
    - Debugging payment issues across different flows
    - Monitoring payment success/failure rates
    - Tracking flow performance and timing
    - Correlating logs across different system components

    Args:
        logger: Python logger instance to use.
               If None, important messages will print to stdout.
        flow_name: Name of the payment flow for log prefixing.
                  Examples: 'Progress', 'Elicitation', 'Sync', 'WebView'
        level: Python logging level name.
              Valid values: 'debug', 'info', 'warning', 'error', 'critical'
        message: Log message template.
                Can include format placeholders for args.
        *args: Positional arguments for logger formatting.
        **kwargs: Keyword arguments for logger formatting.

    Example:
        >>> log_flow(logger, "Elicitation", "info", "Payment %s confirmed", payment_id)
        # Outputs: [PayMCP:Elicitation] Payment pay_123 confirmed

        >>> log_flow(None, "Progress", "error", "Provider failed: %s", error)
        # Prints: ERROR: [PayMCP:Progress] Provider failed: Connection timeout
    """
    # Create consistent prefix for all PayMCP logs
    prefix = f"[PayMCP:{flow_name}]"
    full_message = f"{prefix} {message}"

    if logger:
        # Use the provided logger with the requested level
        log_func = getattr(logger, level, None)
        if log_func and callable(log_func):
            log_func(full_message, *args, **kwargs)
        else:
            # Invalid log level, fall back to info
            logger.info(f"INVALID_LEVEL({level}): {full_message}", *args, **kwargs)
    elif level in ('error', 'warning', 'critical'):
        # No logger provided, but this is an important message
        # Print to stdout so it's not lost completely
        try:
            formatted_message = full_message % args if args else full_message
            print(f"{level.upper()}: {formatted_message}")
        except (TypeError, ValueError):
            # Formatting failed, print raw message
            print(f"{level.upper()}: {full_message} (formatting error)")


def extract_tool_description(tool_name: str, flow_type: str) -> str:
    """
    Generate consistent tool descriptions for payment-enabled tools.

    This function creates standardized descriptions that appear in:
    1. Tool listings (when MCP clients enumerate available tools)
    2. Help documentation
    3. Error messages when payment is required
    4. Debugging and logging output

    Consistent descriptions help users understand:
    - Which tools require payment
    - What type of payment flow will be used
    - What they're paying for

    Args:
        tool_name: Name of the original tool function.
                  Example: "generate_image", "analyze_document"
        flow_type: Type of payment flow being used.
                  Examples: "elicitation", "progress", "sync", "webview"

    Returns:
        Formatted description string ready for display to users.

    Example:
        >>> extract_tool_description("generate_image", "elicitation")
        "generate_image() execution fee via elicitation flow"

        >>> extract_tool_description("analyze_document", "progress")
        "analyze_document() execution fee via progress flow"
    """
    return f"{tool_name}() execution fee via {flow_type} flow"