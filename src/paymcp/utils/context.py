"""
Context extraction utilities for MCP (Model Context Protocol) integration.

This module handles the complexity of extracting session and request information
from various MCP client implementations. Different clients (Claude Desktop,
FastMCP, MCP Inspector, etc.) structure their context objects differently,
so these utilities provide a unified interface for accessing context data.

Why this exists:
1. MCP doesn't standardize context structure across implementations
2. Session persistence requires consistent session ID extraction
3. Debugging requires visibility into context structure
4. Future-proofing against new MCP client implementations
"""
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)


def extract_session_id(ctx: Any) -> Optional[str]:
    """
    Extract session ID from various possible locations in the context object.

    Session ID is critical for:
    - StateStore: Persisting payment state across timeout/reconnection
    - Idempotency: Preventing duplicate payments for the same session
    - Recovery: Resuming interrupted payment flows

    Different MCP implementations store session information in different places:
    - FastMCP: ctx.session_id (direct attribute)
    - Claude Desktop: ctx.session.id (nested object)
    - MCP Inspector: May not have session, falls back to request_id
    - Custom clients: ctx.meta['session_id'] (metadata dict)

    Args:
        ctx: The context object passed to the tool handler.
             Can be None, a dict, or an object with various attributes.

    Returns:
        The session ID if found, None otherwise.
        Format depends on the client but typically a UUID or unique string.

    Example:
        >>> ctx = SimpleNamespace(session_id="abc-123")
        >>> extract_session_id(ctx)
        'abc-123'
    """
    if not ctx:
        logger.debug("No context provided")
        return None

    # Strategy: Try multiple extraction approaches in order of preference
    # Each approach is based on observed MCP client implementations

    # Approach 1: Direct session_id attribute (FastMCP style)
    # This is the cleanest approach when available
    if hasattr(ctx, 'session_id'):
        session_id = ctx.session_id
        logger.debug(f"Got session_id from ctx.session_id: {session_id}")
        return session_id

    # Approach 2: From nested session object (Claude Desktop style)
    # Some clients wrap session info in a session object
    if hasattr(ctx, 'session'):
        # Try session.id first (more common)
        if hasattr(ctx.session, 'id'):
            session_id = ctx.session.id
            logger.debug(f"Got session_id from ctx.session.id: {session_id}")
            return session_id
        # Try session.session_id as alternative
        elif hasattr(ctx.session, 'session_id'):
            session_id = ctx.session.session_id
            logger.debug(f"Got session_id from ctx.session.session_id: {session_id}")
            return session_id

    # Approach 3: From meta attribute (custom implementations)
    # Some clients store metadata in a dict
    if hasattr(ctx, 'meta') and ctx.meta and isinstance(ctx.meta, dict):
        if 'session_id' in ctx.meta:
            session_id = ctx.meta['session_id']
            logger.debug(f"Got session_id from ctx.meta['session_id']: {session_id}")
            return session_id

    # Approach 4: Fallback to request_id as pseudo-session
    # Not ideal: request_id changes per request, breaking session persistence
    # But useful for testing and clients without proper session support
    if hasattr(ctx, 'request_id'):
        # Prefix with 'req_' to distinguish from real session IDs
        session_id = f"req_{ctx.request_id}"
        logger.info(f"Using request_id as session_id: {session_id} (fallback mode)")
        return session_id

    logger.warning("No session_id found in context")
    return None


def log_context_info(ctx: Any) -> None:
    """
    Log debugging information about the context object structure.

    This utility helps developers:
    1. Understand what context structure their MCP client provides
    2. Debug session extraction issues
    3. Add support for new MCP client implementations
    4. Troubleshoot payment flow problems

    The function is intentionally verbose to aid debugging.
    In production, these logs should be at DEBUG level.

    Args:
        ctx: The context object to inspect.
             Can be None, dict, or any object with attributes.

    Side Effects:
        Writes detailed information to the logger at INFO level.
        This includes object type, available attributes, and key values.

    Example Output:
        Context type: <class 'types.SimpleNamespace'>
        Context attributes: ['session_id', 'request_id', 'meta', ...]
        Request ID: req_12345
        Session ID: sess_abc123
    """
    if not ctx:
        return

    # Log basic context information
    logger.info(f"Context type: {type(ctx)}")
    logger.info(f"Context attributes: {dir(ctx)}")

    # Log specific attributes that are important for payment flows
    # These are the most commonly needed fields
    if hasattr(ctx, 'request_id'):
        logger.info(f"Request ID: {ctx.request_id}")

    if hasattr(ctx, 'session_id'):
        logger.info(f"Session ID (direct): {ctx.session_id}")

    # Check for nested session object
    if hasattr(ctx, 'session'):
        logger.info(f"Session object found: {type(ctx.session)}")
        if hasattr(ctx.session, 'id'):
            logger.info(f"Session ID (nested): {ctx.session.id}")

    # Check for metadata
    if hasattr(ctx, 'meta'):
        logger.info(f"Meta attribute found: {type(ctx.meta)}")
        if isinstance(ctx.meta, dict) and 'session_id' in ctx.meta:
            logger.info(f"Session ID (meta): {ctx.meta['session_id']}")

    # Check for elicitation support (important for payment flows)
    if hasattr(ctx, 'elicit'):
        logger.info("Elicitation support: AVAILABLE")
    else:
        logger.info("Elicitation support: NOT AVAILABLE")

    # Check for progress reporting support
    if hasattr(ctx, 'report_progress'):
        logger.info("Progress reporting support: AVAILABLE")
    else:
        logger.info("Progress reporting support: NOT AVAILABLE")