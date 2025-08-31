"""
PayPal Payment Provider Module

Professional PayPal implementation for the PayMCP framework with best practices,
comprehensive validation, and full MCP compatibility.
"""

from .provider import PayPalProvider
from .validator import PayPalValidator, PayPalValidationError
from .config import PayPalConfig, PayPalConfigError

__all__ = ['PayPalProvider', 'PayPalValidator', 'PayPalValidationError', 'PayPalConfig', 'PayPalConfigError']

# Version and metadata
__version__ = '1.0.0'
__author__ = 'PayMCP Team'
__description__ = 'Professional PayPal payment provider with best practices'
