"""
Common utilities for payment flows
"""

import asyncio
import logging
from typing import Any, Callable, Dict, Optional, Tuple


async def call_original_tool(func: Callable, args: Dict[str, Any], kwargs: Dict[str, Any]) -> Any:
    """
    Safely invoke the original tool handler with its arguments.

    This eliminates duplicate function definitions across all flow files.
    """
    if args:
        return await func(**args, **kwargs)
    else:
        return await func(**kwargs)


def normalize_tool_args(*args, **kwargs) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Normalize tool call arguments from MCP SDK.

    Returns:
        Tuple of (positional_args_dict, kwargs)
    """
    # Convert positional args to dict if needed
    args_dict = {}
    if args and len(args) > 0:
        # Store positional args for compatibility
        args_dict = {"_positional": args}

    return args_dict, kwargs


async def delay(seconds: float) -> None:
    """Utility to delay execution"""
    await asyncio.sleep(seconds)


def is_client_aborted(ctx: Any) -> bool:
    """Check if client has aborted the operation"""
    if hasattr(ctx, 'signal') and hasattr(ctx.signal, 'aborted'):
        return ctx.signal.aborted
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
    Log wrapper with consistent formatting

    Args:
        logger: Logger instance or None
        flow_name: Name of the flow (e.g., 'Progress', 'Elicitation')
        level: Log level ('debug', 'info', 'warning', 'error')
        message: Log message
        *args: Additional positional arguments for logger
        **kwargs: Additional keyword arguments for logger
    """
    prefix = f"[PayMCP:{flow_name}]"
    full_message = f"{prefix} {message}"

    if logger:
        log_func = getattr(logger, level, None)
        if log_func:
            log_func(full_message, *args, **kwargs)
    elif level in ('error', 'warning'):
        # Fall back to print for important messages
        print(f"{level.upper()}: {full_message}")


def extract_tool_description(tool_name: str, flow_type: str) -> str:
    """
    Generate a consistent tool description

    Args:
        tool_name: Name of the tool
        flow_type: Type of payment flow

    Returns:
        Formatted description string
    """
    return f"{tool_name}() execution fee via {flow_type} flow"