"""
Observify - A user-friendly interface for LLM call observation.

This module provides a simple API to enable/disable OpenAI call monitoring
without requiring environment variables or sitecustomize imports.
"""
import os
import warnings
from typing import Optional

from .patch_llm import install_patch


_is_patched = False


def patch(enabled: bool = True, debug: bool = False) -> None:
    """
    Enable or configure LLM call observation.
    
    Args:
        enabled: Whether to enable call observation. Defaults to True.
        debug: Whether to enable debug logging. Defaults to False.
    
    Example:
        ```python
        import observify
        observify.patch()  # Enable with defaults
        
        # Or with explicit configuration
        observify.patch(enabled=True, debug=True)
        ```
    """
    global _is_patched
    
    if enabled:
        # Set environment variables for internal compatibility
        os.environ["LLM_WAREHOUSE_ENABLED"] = "1"
        if debug:
            os.environ["LLM_WAREHOUSE_DEBUG"] = "1"
        else:
            os.environ.pop("LLM_WAREHOUSE_DEBUG", None)
        
        if not _is_patched:
            try:
                if debug:
                    print("[observify] Installing OpenAI patches...")
                install_patch()
                _is_patched = True
                if debug:
                    print("[observify] Patches installed successfully")
            except Exception as e:
                # Never break user apps because of warehousing
                warnings.warn(f"observify failed to patch OpenAI: {e}")
        elif debug:
            print("[observify] Patches already installed")
    else:
        # Disable by setting environment variable
        os.environ["LLM_WAREHOUSE_ENABLED"] = "0"
        if debug:
            print("[observify] LLM observation disabled")


def is_enabled() -> bool:
    """
    Check if LLM call observation is currently enabled.
    
    Returns:
        True if observation is enabled, False otherwise.
    """
    value = os.getenv("LLM_WAREHOUSE_ENABLED", "0")
    return value not in {"", "0", "false", "False", "no", "off"}


def is_patched() -> bool:
    """
    Check if the OpenAI patches have been applied.
    
    Returns:
        True if patches are applied, False otherwise.
    """
    return _is_patched


def status() -> dict:
    """
    Get the current status of observify.
    
    Returns:
        A dictionary with current configuration and status.
    """
    return {
        "enabled": is_enabled(),
        "patched": is_patched(),
        "debug": os.getenv("LLM_WAREHOUSE_DEBUG", "0") not in {"", "0", "false", "False", "no", "off"}
    }
