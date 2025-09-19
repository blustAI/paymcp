"""
Shared constants for PayMCP system-wide consistency and maintainability.

DESIGN DECISION: Separate from TypeScript constants.ts
- Python uses seconds (ecosystem standard), TypeScript uses milliseconds
- Each implementation uses language-appropriate patterns (classes vs const objects)
- Values are synchronized manually between languages
"""

from enum import Enum
from typing import Final


class PaymentStatus:
    """
    Payment status constants used across all payment providers and flows.

    These constants standardize how payment states are represented throughout
    the system. All payment providers must return these exact string values
    to ensure consistent handling across different flows and state management.

    Status Lifecycle:
    1. REQUESTED → PENDING → PAID (successful path)
    2. REQUESTED → PENDING → CANCELED (user cancellation)
    3. REQUESTED → PENDING → FAILED (provider error)
    4. REQUESTED → PENDING → EXPIRED (timeout)

    Each status has specific semantics:
    - Terminal states: PAID, CANCELED, FAILED, EXPIRED (no further changes)
    - Active states: REQUESTED, PENDING (can transition to terminal states)
    - Error states: ERROR, TIMEOUT, UNSUPPORTED (system-level issues)

    Usage by components:
    - Providers: Must return these exact values from get_payment_status()
    - State management: Uses these for state transitions and cleanup decisions
    - Flows: Check these values to determine next actions
    - Response builders: Map these to appropriate user messages
    """

    # Successful completion - payment verified and accepted
    PAID: Final = 'paid'

    # Payment is being processed, final status not yet determined
    # This is the most common intermediate state
    PENDING: Final = 'pending'

    # User explicitly canceled the payment (not a system error)
    # Can happen through payment provider UI or client cancellation
    CANCELED: Final = 'canceled'

    # Payment timeout - provider gave up waiting
    # Different from client timeout (TIMEOUT constant)
    EXPIRED: Final = 'expired'

    # Payment failed due to provider error (invalid card, insufficient funds, etc.)
    # This is a provider-side failure, not a system error
    FAILED: Final = 'failed'

    # System-level error (network issues, malformed requests, etc.)
    # Different from payment failure (FAILED)
    ERROR: Final = 'error'

    # Client-side timeout (user disconnected while payment was processing)
    # Payment might still complete on provider side
    TIMEOUT: Final = 'timeout'

    # Initial state when payment is first created
    # Brief transition state before PENDING
    REQUESTED: Final = 'requested'

    # Payment method is not supported by the provider
    # Used for graceful degradation
    UNSUPPORTED: Final = 'unsupported'


class ResponseType:
    """
    MCP response type constants for consistent client communication.

    These constants define the standardized response statuses that MCP clients
    expect to receive. They are used in response builders to ensure all
    payment flows return properly formatted responses.

    These map to but are distinct from PaymentStatus constants:
    - ResponseType: Client-facing status for MCP protocol
    - PaymentStatus: Provider-specific payment state

    Mapping examples:
    - PaymentStatus.PAID → ResponseType.SUCCESS
    - PaymentStatus.PENDING → ResponseType.PENDING
    - PaymentStatus.CANCELED → ResponseType.CANCELED
    - PaymentStatus.FAILED → ResponseType.ERROR
    """

    # Tool execution completed successfully after payment
    # Indicates both payment and tool execution succeeded
    SUCCESS: Final = 'success'

    # An error occurred during payment or tool execution
    # Covers both payment failures and system errors
    ERROR: Final = 'error'

    # Payment is required and in progress
    # User needs to complete payment before tool can execute
    PENDING: Final = 'pending'

    # Payment was canceled by user or system
    # Tool execution did not occur
    CANCELED: Final = 'canceled'


class Timing:
    """
    Timing constants for payment flow behavior and performance tuning.

    These values control various timing aspects of payment flows and can be
    adjusted based on performance requirements and user experience needs.

    Considerations for timing values:
    - Shorter polls = better responsiveness, more API calls
    - Longer timeouts = better for slow payment methods, more resource usage
    - Longer TTL = better recovery, more memory usage

    Production tuning:
    - Increase poll intervals for high-volume scenarios
    - Decrease timeouts for fast payment methods
    - Adjust TTL based on expected session lengths
    """

    # How often to check payment status during active polling
    # Balance between responsiveness and API call frequency
    # 3 seconds provides good UX without overwhelming providers
    DEFAULT_POLL_SECONDS: Final = 3

    # Maximum time to wait for payment completion before giving up
    # 15 minutes allows for slow payment methods (bank transfers, etc.)
    # After this timeout, payments may still complete but won't trigger tools
    MAX_WAIT_SECONDS: Final = 15 * 60  # 15 minutes

    # How long to keep payment state in storage for recovery
    # 30 minutes allows users to resume after client disconnections
    # Longer than MAX_WAIT_SECONDS to handle edge cases
    STATE_TTL_SECONDS: Final = 30 * 60  # 30 minutes


class PaymentFlow(Enum):
    """
    Payment flow types - separate implementations instead of unified flow.

    DESIGN DECISION: Why separate flows instead of one unified flow?
    - Each flow optimized for specific client capabilities (elicitation, progress, basic)
    - Avoids complex branching logic in unified implementation
    - Easier testing and maintenance of individual flows
    """

    # Two-step flow: separate payment initiation and confirmation
    TWO_STEP = 'two_step'

    # Progress flow: single call with progress reporting
    PROGRESS = 'progress'

    # Elicitation flow: interactive prompts for payment
    ELICITATION = 'elicitation'

    # Out-of-band flow: payment handled externally
    OOB = 'oob'