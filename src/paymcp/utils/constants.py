"""
Shared constants for PayMCP
"""

from enum import Enum
from typing import Final


class PaymentStatus:
    """Payment status constants"""
    PAID: Final = 'paid'
    PENDING: Final = 'pending'
    CANCELED: Final = 'canceled'
    EXPIRED: Final = 'expired'
    FAILED: Final = 'failed'
    ERROR: Final = 'error'
    TIMEOUT: Final = 'timeout'
    REQUESTED: Final = 'requested'
    UNSUPPORTED: Final = 'unsupported'


class ResponseType:
    """MCP response type constants"""
    SUCCESS: Final = 'success'
    ERROR: Final = 'error'
    PENDING: Final = 'pending'
    CANCELED: Final = 'canceled'


class Timing:
    """Timing constants"""
    DEFAULT_POLL_SECONDS: Final = 3  # Poll every 3 seconds
    MAX_WAIT_SECONDS: Final = 15 * 60  # 15 minutes timeout
    STATE_TTL_SECONDS: Final = 30 * 60  # 30 minutes state TTL


class FlowType(Enum):
    """Payment flow types"""
    TWO_STEP = 'TWO_STEP'
    PROGRESS = 'PROGRESS'
    ELICITATION = 'ELICITATION'