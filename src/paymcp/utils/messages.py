"""
User-facing message generation utilities for payment flows.

This module creates consistent, user-friendly messages for payment prompts.
These messages are shown to users during payment flows to guide them through
the payment process and set clear expectations.

The messages are designed to be:
1. Clear and concise
2. Action-oriented
3. Consistent across all payment flows
4. Informative about next steps
"""


def open_link_message(url: str, amount: float, currency: str) -> str:
    """
    Generate a payment prompt message when webview is NOT available.

    This message is used when the payment must be completed in an external
    browser window. It emphasizes clicking the link and returning after payment.

    Used by:
    - All payment flows when webview is not supported
    - MCP Inspector (no webview support)
    - Command-line MCP clients

    Args:
        url: Payment URL where user completes payment.
        amount: Payment amount in the specified currency.
        currency: Currency code (e.g., 'USD', 'EUR').

    Returns:
        Formatted message string with payment instructions.

    Example Output:
        "To run this tool, please pay 5.00 USD using the link below:

        https://pay.example.com/abc123

        After completing the payment, come back and confirm."
    """
    return (
        f"To run this tool, please pay {amount} {currency} using the link below:\n\n"
        f"{url}\n\n"
        "After completing the payment, come back and confirm."
    )

def opened_webview_message(url: str, amount: float, currency: str) -> str:
    """
    Generate a payment prompt message when webview IS available.

    This message is used when the payment window opens automatically in a
    webview or popup. It assumes the window is already open but provides
    the link as a fallback.

    Used by:
    - Claude Desktop (has webview support)
    - Desktop MCP clients with webview capability
    - Browser-based MCP implementations

    The message is less directive about clicking since the window
    should already be visible to the user.

    Args:
        url: Payment URL (provided as fallback if webview fails).
        amount: Payment amount in the specified currency.
        currency: Currency code (e.g., 'USD', 'EUR').

    Returns:
        Formatted message string with payment instructions.

    Example Output:
        "To run this tool, please pay 5.00 USD.
        A payment window should be open. If not, you can use this link:

        https://pay.example.com/abc123

        After completing the payment, come back and confirm."
    """
    return (
        f"To run this tool, please pay {amount} {currency}.\n"
        "A payment window should be open. If not, you can use this link:\n\n"
        f"{url}\n\n"
        "After completing the payment, come back and confirm."
    )

def description_with_price(description: str, price_info: dict) -> str:
    """
    Enhance a tool's description with pricing information.

    This function appends pricing details to tool descriptions so users
    (and LLMs) know a tool requires payment before they invoke it.
    This transparency helps set expectations and avoid surprises.

    The enhanced description appears in:
    - Tool listing (when client lists available tools)
    - Tool help/documentation
    - Error messages when payment is required

    Args:
        description: Original tool description from the developer.
        price_info: Dictionary with pricing details.
                   Expected keys:
                   - 'price': Numeric amount (e.g., 5.00)
                   - 'currency': Currency code (e.g., 'USD')
                   Optional keys:
                   - 'per': Unit of measurement (e.g., 'request', 'minute')

    Returns:
        Enhanced description with pricing information appended.

    Example:
        >>> desc = "Generate an image from text prompt"
        >>> price = {"price": 2.50, "currency": "USD"}
        >>> description_with_price(desc, price)
        "Generate an image from text prompt
        This is a paid function: 2.5 USD. Payment will be requested during execution."
    """
    # Format the pricing message
    # Note: We strip the original description to avoid extra whitespace
    extra_desc = (
        f"\nThis is a paid function: {price_info['price']} {price_info['currency']}."
        " Payment will be requested during execution."
    )

    # Append to original description
    return description.strip() + extra_desc