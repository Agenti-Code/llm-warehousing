__all__ = [
    "install_patch", 
    "get_recent_logs", "get_recent_logs_async",
    "show_recent_logs", "show_recent_logs_async",
    "patch", "is_enabled", "is_patched", "status"
]

import os
import warnings

from .patch_llm import install_patch
from .query import get_recent_logs, get_recent_logs_async, show_recent_logs, show_recent_logs_async
from .observify import patch, is_enabled, is_patched, status


def _should_auto_patch() -> bool:
    """Check if automatic patching should be enabled based on OBSERVIFY_API_TOKEN."""
    token = os.getenv("OBSERVIFY_API_TOKEN", "").strip()
    return bool(token)  # Any non-empty token is considered valid for now


def _is_debug() -> bool:
    """Check if debug mode is enabled."""
    value = os.getenv("OBSERVIFY_DEBUG", "0")
    return value not in {"", "0", "false", "False", "no", "off"}


# 🚀 Automatic patching on import if OBSERVIFY_API_TOKEN is set
if _should_auto_patch():
    try:
        if _is_debug():
            print("[llm-warehouse] Auto-patching enabled via OBSERVIFY_API_TOKEN")
        install_patch()
        if _is_debug():
            print("[llm-warehouse] Auto-patching complete")
    except Exception as e:
        # Never break user apps because of warehousing
        warnings.warn(f"llm-warehouse failed to auto-patch: {e}", stacklevel=2)

