import os
import warnings


def _is_enabled() -> bool:
    value = os.getenv("LLM_WAREHOUSE_ENABLED", "0")
    return value not in {"", "0", "false", "False", "no", "off"}


if _is_enabled():
    try:
        from llm_warehouse.patch_openai import install_patch
        if os.getenv("LLM_WAREHOUSE_DEBUG", "0") not in {"", "0", "false", "False", "no", "off"}:
            print("[llm-warehouse] sitecustomize enabling patch")
        install_patch()
    except Exception as e:  # noqa: BLE001
        # Never break user apps because of warehousing
        warnings.warn(f"llm-warehouse failed to patch: {e}")


