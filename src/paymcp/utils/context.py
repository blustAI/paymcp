"""
Utility functions for extracting information from MCP context objects.
"""
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)


def extract_session_id(ctx: Any) -> Optional[str]:
    """
    Extract session ID from various possible locations in the context object.

    Different MCP implementations store session information in different places,
    so this function tries multiple approaches to find it.

    Args:
        ctx: The context object passed to the tool handler

    Returns:
        The session ID if found, None otherwise
    """
    if not ctx:
        logger.debug("No context provided")
        return None

    # Try multiple approaches to get session ID

    # 1. Direct session_id attribute (FastMCP style)
    if hasattr(ctx, 'session_id'):
        session_id = ctx.session_id
        logger.debug(f"Got session_id from ctx.session_id: {session_id}")
        return session_id

    # 2. From nested session object
    if hasattr(ctx, 'session'):
        if hasattr(ctx.session, 'id'):
            session_id = ctx.session.id
            logger.debug(f"Got session_id from ctx.session.id: {session_id}")
            return session_id
        elif hasattr(ctx.session, 'session_id'):
            session_id = ctx.session.session_id
            logger.debug(f"Got session_id from ctx.session.session_id: {session_id}")
            return session_id

    # 3. From meta attribute
    if hasattr(ctx, 'meta') and ctx.meta and isinstance(ctx.meta, dict):
        if 'session_id' in ctx.meta:
            session_id = ctx.meta['session_id']
            logger.debug(f"Got session_id from ctx.meta['session_id']: {session_id}")
            return session_id

    # 4. Fallback to request_id as session (temporary workaround for testing)
    if hasattr(ctx, 'request_id'):
        # Use request_id as a fallback - not ideal but helps test StateStore
        session_id = f"req_{ctx.request_id}"
        logger.info(f"Using request_id as session_id: {session_id}")
        return session_id

    logger.warning("No session_id found in context")
    return None


def log_context_info(ctx: Any) -> None:
    """
    Log debugging information about the context object.

    Args:
        ctx: The context object to inspect
    """
    if not ctx:
        return

    logger.info(f"Context type: {type(ctx)}")
    logger.info(f"Context attributes: {dir(ctx)}")

    # Log specific attributes if they exist
    if hasattr(ctx, 'request_id'):
        logger.info(f"Request ID: {ctx.request_id}")

    if hasattr(ctx, 'session_id'):
        logger.info(f"Session ID: {ctx.session_id}")