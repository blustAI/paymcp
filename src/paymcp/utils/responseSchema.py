"""
Pydantic schemas for MCP elicitation responses.

This module defines response schemas used with MCP's elicitation protocol.
Elicitation allows the server to prompt the client for user input during
tool execution, which is essential for interactive payment flows.

The schemas define what data structure the client should return when
responding to elicitation prompts.
"""

from pydantic import BaseModel


class SimpleActionSchema(BaseModel):
    """
    Minimal schema for simple accept/decline/cancel responses.

    This empty schema is intentionally minimal to trigger the simplest
    possible UI in MCP clients - typically just Accept/Decline buttons.
    More complex schemas would require structured input forms.

    Usage:
    - Elicitation flows that only need binary user decisions
    - Payment confirmation prompts
    - Simple yes/no interactions

    Client Behavior:
    - FastMCP Python: Shows Accept/Decline/Cancel buttons
    - Claude Desktop: May show simple confirmation dialog
    - MCP Inspector: Depends on implementation

    The actual response typically includes an 'action' field with values
    like 'accept', 'decline', 'cancel', but the schema doesn't enforce
    this to remain flexible across different client implementations.

    Example Response (not enforced by schema):
        {"action": "accept"}
        {"action": "cancel"}
    """
    pass  # Intentionally empty for maximum client compatibility
