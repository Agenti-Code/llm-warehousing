import json
import os
import time
from typing import Any, Dict, Optional

import httpx


WAREHOUSE_URL: Optional[str] = os.getenv("LLM_WAREHOUSE_URL")
WAREHOUSE_KEY: Optional[str] = os.getenv("LLM_WAREHOUSE_API_KEY")
FALLBACK_PATH: str = os.getenv("LLM_WAREHOUSE_FALLBACK", "llm_calls.jsonl")

# Supabase configuration
SUPABASE_URL: Optional[str] = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY: Optional[str] = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_KEY: Optional[str] = os.getenv("SUPABASE_KEY")  # fallback if service role not set
SUPABASE_TABLE: str = os.getenv("LLM_WAREHOUSE_SUPABASE_TABLE", "llm_calls")
_supabase_table_ready: bool = False
DEBUG: bool = os.getenv("LLM_WAREHOUSE_DEBUG", "0") not in {"", "0", "false", "False", "no", "off"}


def _headers() -> Dict[str, str]:
    headers: Dict[str, str] = {"Content-Type": "application/json"}
    if WAREHOUSE_KEY:
        headers["Authorization"] = f"Bearer {WAREHOUSE_KEY}"
    return headers


def _sb_base_urls() -> Optional[Dict[str, str]]:
    """Return normalized REST and pg-meta base URLs for Supabase.

    Accepts SUPABASE_URL that may or may not already include "/rest/v1".
    """
    if not SUPABASE_URL:
        return None
    base = SUPABASE_URL.rstrip("/")
    if base.endswith("/rest/v1"):
        project_base = base[: -len("/rest/v1")]
    else:
        project_base = base
    return {
        "rest": f"{project_base}/rest/v1",
        "pg": f"{project_base}/pg",
    }


def _sb_auth_headers() -> Optional[Dict[str, str]]:
    key = SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY
    if not (SUPABASE_URL and key):
        return None
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def _ensure_supabase_table() -> None:
    """Table should be created manually. This function is now a no-op."""
    global _supabase_table_ready
    _supabase_table_ready = True


def _send_via_supabase(record: Dict[str, Any]) -> bool:
    urls = _sb_base_urls()
    headers = _sb_auth_headers()
    if not urls or not headers:
        return False
    try:
        _ensure_supabase_table()
        # Insert record as a JSONB column to keep schema stable
        if DEBUG:
            print("[llm-warehouse] rest insert", {"url": f"{urls['rest']}/{SUPABASE_TABLE}"})
        resp = httpx.post(
            f"{urls['rest']}/{SUPABASE_TABLE}",
            headers={**headers, "Prefer": "return=minimal"},
            json=[{"data": record}],
            timeout=6.0,
        )
        if DEBUG:
            print("[llm-warehouse] rest insert status:", resp.status_code, resp.text[:200])
        if 200 <= resp.status_code < 300:
            return True

        return False
    except Exception:
        if DEBUG:
            print("[llm-warehouse] supabase send exception")
        return False


def send(record: Dict[str, Any]) -> None:
    """Send a single record to the configured LLM warehouse Flask app, or append to a JSONL file.

    Never raises; failures fall back to local file append.
    """
    record.setdefault("ts", time.time())
    record.setdefault("source", "python-openai")
    record.setdefault(
        "env",
        {k: os.getenv(k) for k in ["OPENAI_BASE_URL", "OPENAI_ORG", "OPENAI_PROJECT"]},
    )

    # Priority 1: Flask LLM Warehouse app
    if WAREHOUSE_URL and WAREHOUSE_KEY:
        try:
            # Construct the full URL for the llm-logs endpoint
            warehouse_url = WAREHOUSE_URL.rstrip("/")
            if not warehouse_url.endswith("/llm-logs"):
                warehouse_url = f"{warehouse_url}/llm-logs"
            
            response = httpx.post(
                warehouse_url, 
                json=record, 
                timeout=10.0, 
                headers=_headers()
            )
            
            if DEBUG:
                print(f"[llm-warehouse] Flask app response: {response.status_code}")
            
            # Consider 2xx status codes as success
            if 200 <= response.status_code < 300:
                if DEBUG:
                    print(f"[llm-warehouse] Successfully sent to Flask app: {warehouse_url}")
                return
            else:
                if DEBUG:
                    print(f"[llm-warehouse] Flask app error: {response.text[:200]}")
                
        except Exception as e:
            if DEBUG:
                print(f"[llm-warehouse] Flask app send exception: {e}")
            # Fall through to file without interrupting user code
            pass

    # Priority 2: Supabase fallback (if Flask app fails and Supabase is configured)
    if SUPABASE_URL and (SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY):
        if DEBUG:
            print("[llm-warehouse] Falling back to Supabase")
        if _send_via_supabase(record):
            return

    # Priority 3: Local file fallback
    if DEBUG:
        print(f"[llm-warehouse] Falling back to local file: {FALLBACK_PATH}")
    
    with open(FALLBACK_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


