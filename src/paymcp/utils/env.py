"""
Environment utilities for PayMCP.

This module provides utilities for loading environment variables and .env files.
"""

import os
from typing import Optional


def load_env_file(env_path: Optional[str] = None) -> None:
    """
    Load environment variables from .env file.

    Args:
        env_path: Path to .env file. If None, looks for .env in current directory.
    """
    # Try to load .env file using python-dotenv if available
    try:
        from dotenv import load_dotenv
        if env_path:
            load_dotenv(env_path)
        else:
            load_dotenv()
        return
    except ImportError:
        pass

    # Fallback to manual .env loading
    if env_path is None:
        env_path = os.path.join(os.getcwd(), '.env')

    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Only set if not already in environment
                    os.environ.setdefault(key.strip(), value.strip())


def get_env_with_fallback(*keys: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get environment variable with multiple key fallbacks.

    Args:
        *keys: Environment variable keys to try in order
        default: Default value if none found

    Returns:
        First found environment variable value or default
    """
    for key in keys:
        value = os.getenv(key)
        if value:
            return value
    return default
