"""Query and display logged LLM calls from Supabase or local files."""

import asyncio
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any

import httpx


async def _get_flask_logs_async(warehouse_url: str, warehouse_key: str, limit: int) -> List[Dict[str, Any]]:
    """Retrieve logs from Flask LLM Warehouse app."""
    try:
        # Construct the query URL
        base_url = warehouse_url.rstrip("/")
        if not base_url.endswith("/llm-logs"):
            base_url = f"{base_url}/llm-logs"
        
        headers = {
            "Authorization": f"Bearer {warehouse_key}",
            "Content-Type": "application/json"
        }
        
        params = {"limit": limit}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(base_url, headers=headers, params=params, timeout=10.0)
            
            if response.status_code == 200:
                data = response.json()
                return data.get("logs", [])
            else:
                print(f"[llm-warehouse] Flask app query failed: {response.status_code} {response.text[:200]}")
                return []
                
    except Exception as e:
        print(f"[llm-warehouse] Flask app query exception: {e}")
        return []


def _get_flask_logs_sync(warehouse_url: str, warehouse_key: str, limit: int) -> List[Dict[str, Any]]:
    """Retrieve logs from Flask LLM Warehouse app (sync version)."""
    try:
        # Construct the query URL
        base_url = warehouse_url.rstrip("/")
        if not base_url.endswith("/llm-logs"):
            base_url = f"{base_url}/llm-logs"
        
        headers = {
            "Authorization": f"Bearer {warehouse_key}",
            "Content-Type": "application/json"
        }
        
        params = {"limit": limit}
        
        response = httpx.get(base_url, headers=headers, params=params, timeout=10.0)
        
        if response.status_code == 200:
            data = response.json()
            return data.get("logs", [])
        else:
            print(f"[llm-warehouse] Flask app query failed: {response.status_code} {response.text[:200]}")
            return []
            
    except Exception as e:
        print(f"[llm-warehouse] Flask app query exception: {e}")
        return []


async def get_recent_logs_async(limit: int = 5, table: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve recent logs from configured storage backend (async version).
    
    Args:
        limit: Number of recent logs to retrieve (default: 5)
        table: Override table name (not used for Flask app)
    
    Returns:
        List of log entries, most recent first
    """
    # Priority 1: Try Flask LLM Warehouse app
    warehouse_url = os.getenv("LLM_WAREHOUSE_URL")
    warehouse_key = os.getenv("LLM_WAREHOUSE_API_KEY")
    
    if warehouse_url and warehouse_key:
        return await _get_flask_logs_async(warehouse_url, warehouse_key, limit)
    
    # Priority 2: Try Supabase
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    
    if supabase_url and supabase_key:
        return await _get_supabase_logs_async(supabase_url, supabase_key, limit, table)
    
    # Priority 3: Fall back to local file
    fallback_path = os.getenv("LLM_WAREHOUSE_FALLBACK", "llm_calls.jsonl")
    return _get_local_logs(fallback_path, limit)


def get_recent_logs(limit: int = 5, table: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve recent logs from configured storage backend (sync wrapper).
    
    Args:
        limit: Number of recent logs to retrieve (default: 5)
        table: Override table name (default: from LLM_WAREHOUSE_SUPABASE_TABLE env var)
    
    Returns:
        List of log entries, most recent first
    """
    try:
        # Check if we're in an async context (like Jupyter notebooks)
        asyncio.get_running_loop()
        # If we get here, there's already a loop running - use sync fallback
        return _get_recent_logs_sync(limit, table)
    except RuntimeError:
        # No event loop running, safe to use asyncio.run()
        return asyncio.run(get_recent_logs_async(limit, table))


async def show_recent_logs_async(limit: int = 5, table: Optional[str] = None) -> None:
    """Display recent logs in a nicely formatted way (async version).
    
    Args:
        limit: Number of recent logs to show (default: 5)
        table: Override table name (default: from LLM_WAREHOUSE_SUPABASE_TABLE env var)
    """
    print(f"=== 🔍 Fetching {limit} Most Recent Log(s) ===")
    
    try:
        logs = await get_recent_logs_async(limit, table)
        
        if not logs:
            print("❌ No logs found")
            print("Make sure you've made some OpenAI API calls after setting up the warehouse")
            return
        
        print(f"✅ SUCCESS! Found {len(logs)} log(s)")
        
        for i, log_entry in enumerate(logs, 1):
            print(f"\n--- 📋 Log {i} ---")
            
            # Handle both Supabase format (with 'data' field) and direct format
            if isinstance(log_entry, dict) and 'data' in log_entry:
                # Supabase format
                created_at = log_entry.get('created_at')
                log_data = log_entry['data']
            else:
                # Direct format (local file)
                created_at = log_entry.get('ts')
                if created_at:
                    created_at = datetime.fromtimestamp(created_at).isoformat()
                log_data = log_entry
            
            print(f"📅 Created: {created_at}")
            print(f"🔧 SDK Method: {log_data.get('sdk_method')}")
            print(f"⚡ Latency: {log_data.get('latency_s', 'N/A')}s")
            
            # Show request details
            request_data = log_data.get('request', {})
            if 'kwargs' in request_data:
                model = request_data['kwargs'].get('model', 'Unknown')
                print(f"🤖 Model: {model}")
                
                # Handle both chat completions and responses API
                messages = request_data['kwargs'].get('messages')
                input_text = request_data['kwargs'].get('input')
                
                if messages and len(messages) > 0:
                    user_msg = next((m['content'] for m in messages if m.get('role') == 'user'), 'N/A')
                    print(f"💬 User Message: {str(user_msg)[:50]}{'...' if len(str(user_msg)) > 50 else ''}")
                elif input_text:
                    print(f"💬 Input: {str(input_text)[:50]}{'...' if len(str(input_text)) > 50 else ''}")
            
            # Show response details if available
            response_data = log_data.get('response', {})
            if response_data:
                usage = response_data.get('usage', {})
                if usage:
                    prompt_tokens = usage.get('prompt_tokens', 'N/A')
                    completion_tokens = usage.get('completion_tokens', 'N/A') 
                    total_tokens = usage.get('total_tokens', 'N/A')
                    print(f"📊 Tokens - Prompt: {prompt_tokens}, Completion: {completion_tokens}, Total: {total_tokens}")
                
                # Show response content
                choices = response_data.get('choices', [])
                output = response_data.get('output', [])  # For responses API
                
                if choices and len(choices) > 0:
                    choice = choices[0]
                    if 'message' in choice and choice['message'].get('content'):
                        content = choice['message']['content']
                        print(f"🤖 Response: {content[:100]}{'...' if len(content) > 100 else ''}")
                elif output and len(output) > 0:
                    # Responses API format
                    first_output = output[0]
                    if hasattr(first_output, 'text') or (isinstance(first_output, dict) and 'text' in first_output):
                        text = first_output.get('text') if isinstance(first_output, dict) else first_output.text
                        print(f"🤖 Response: {text[:100]}{'...' if len(str(text)) > 100 else ''}")
            
            # Show errors if any
            error = log_data.get('error')
            if error:
                print(f"❌ Error: {error}")
                
    except Exception as e:
        print(f"❌ Error retrieving logs: {e}")
        print("Check your configuration and network connection")


def show_recent_logs(limit: int = 5, table: Optional[str] = None) -> None:
    """Display recent logs in a nicely formatted way (sync wrapper).
    
    Args:
        limit: Number of recent logs to show (default: 5)
        table: Override table name (default: from LLM_WAREHOUSE_SUPABASE_TABLE env var)
    """
    try:
        # Check if we're in an async context (like Jupyter notebooks)
        asyncio.get_running_loop()
        # If we get here, there's already a loop running - use sync fallback
        _show_recent_logs_sync(limit, table)
    except RuntimeError:
        # No event loop running, safe to use asyncio.run()
        asyncio.run(show_recent_logs_async(limit, table))


async def _get_supabase_logs_async(base_url: str, api_key: str, limit: int, table: Optional[str]) -> List[Dict[str, Any]]:
    """Get logs from Supabase (async version)."""
    table_name = table or os.getenv("LLM_WAREHOUSE_SUPABASE_TABLE", "llm_calls")
    base = base_url.rstrip("/")
    
    url = f"{base}/rest/v1/{table_name}?select=*&order=created_at.desc&limit={limit}"
    headers = {
        "apikey": api_key,
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, timeout=10)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Supabase query failed: {response.status_code} - {response.text}")


def _get_supabase_logs(base_url: str, api_key: str, limit: int, table: Optional[str]) -> List[Dict[str, Any]]:
    """Get logs from Supabase (sync version)."""
    table_name = table or os.getenv("LLM_WAREHOUSE_SUPABASE_TABLE", "llm_calls")
    base = base_url.rstrip("/")
    
    url = f"{base}/rest/v1/{table_name}?select=*&order=created_at.desc&limit={limit}"
    headers = {
        "apikey": api_key,
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    response = httpx.get(url, headers=headers, timeout=10)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Supabase query failed: {response.status_code} - {response.text}")


def _get_recent_logs_sync(limit: int = 5, table: Optional[str] = None) -> List[Dict[str, Any]]:
    """Sync implementation of get_recent_logs for when async is not available."""
    # Priority 1: Try Flask LLM Warehouse app
    warehouse_url = os.getenv("LLM_WAREHOUSE_URL")
    warehouse_key = os.getenv("LLM_WAREHOUSE_API_KEY")
    
    if warehouse_url and warehouse_key:
        return _get_flask_logs_sync(warehouse_url, warehouse_key, limit)
    
    # Priority 2: Try Supabase
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    
    if supabase_url and supabase_key:
        return _get_supabase_logs(supabase_url, supabase_key, limit, table)
    
    # Priority 3: Fall back to local file
    fallback_path = os.getenv("LLM_WAREHOUSE_FALLBACK", "llm_calls.jsonl")
    return _get_local_logs(fallback_path, limit)


def _show_recent_logs_sync(limit: int = 5, table: Optional[str] = None) -> None:
    """Sync implementation of show_recent_logs for when async is not available."""
    print(f"=== 🔍 Fetching {limit} Most Recent Log(s) ===")
    
    try:
        logs = _get_recent_logs_sync(limit, table)
        
        if not logs:
            print("❌ No logs found")
            print("Make sure you've made some OpenAI API calls after setting up the warehouse")
            return
        
        print(f"✅ SUCCESS! Found {len(logs)} log(s)")
        
        for i, log_entry in enumerate(logs, 1):
            print(f"\n--- 📋 Log {i} ---")
            
            # Handle both Supabase format (with 'data' field) and direct format
            if isinstance(log_entry, dict) and 'data' in log_entry:
                # Supabase format
                created_at = log_entry.get('created_at')
                log_data = log_entry['data']
            else:
                # Direct format (local file)
                created_at = log_entry.get('ts')
                if created_at:
                    created_at = datetime.fromtimestamp(created_at).isoformat()
                log_data = log_entry
            
            print(f"📅 Created: {created_at}")
            print(f"🔧 SDK Method: {log_data.get('sdk_method')}")
            print(f"⚡ Latency: {log_data.get('latency_s', 'N/A')}s")
            
            # Show request details
            request_data = log_data.get('request', {})
            if 'kwargs' in request_data:
                model = request_data['kwargs'].get('model', 'Unknown')
                print(f"🤖 Model: {model}")
                
                # Handle both chat completions and responses API
                messages = request_data['kwargs'].get('messages')
                input_text = request_data['kwargs'].get('input')
                
                if messages and len(messages) > 0:
                    user_msg = next((m['content'] for m in messages if m.get('role') == 'user'), 'N/A')
                    print(f"💬 User Message: {str(user_msg)[:50]}{'...' if len(str(user_msg)) > 50 else ''}")
                elif input_text:
                    print(f"💬 Input: {str(input_text)[:50]}{'...' if len(str(input_text)) > 50 else ''}")
            
            # Show response details if available
            response_data = log_data.get('response', {})
            if response_data:
                usage = response_data.get('usage', {})
                if usage:
                    prompt_tokens = usage.get('prompt_tokens', 'N/A')
                    completion_tokens = usage.get('completion_tokens', 'N/A') 
                    total_tokens = usage.get('total_tokens', 'N/A')
                    print(f"📊 Tokens - Prompt: {prompt_tokens}, Completion: {completion_tokens}, Total: {total_tokens}")
                
                # Show response content
                choices = response_data.get('choices', [])
                output = response_data.get('output', [])  # For responses API
                
                if choices and len(choices) > 0:
                    choice = choices[0]
                    if 'message' in choice and choice['message'].get('content'):
                        content = choice['message']['content']
                        print(f"🤖 Response: {content[:100]}{'...' if len(content) > 100 else ''}")
                elif output and len(output) > 0:
                    # Responses API format
                    first_output = output[0]
                    if hasattr(first_output, 'text') or (isinstance(first_output, dict) and 'text' in first_output):
                        text = first_output.get('text') if isinstance(first_output, dict) else first_output.text
                        print(f"🤖 Response: {text[:100]}{'...' if len(str(text)) > 100 else ''}")
            
            # Show errors if any
            error = log_data.get('error')
            if error:
                print(f"❌ Error: {error}")
                
    except Exception as e:
        print(f"❌ Error retrieving logs: {e}")
        print("Check your configuration and network connection")


def _get_local_logs(file_path: str, limit: int) -> List[Dict[str, Any]]:
    """Get logs from local JSONL file."""
    if not os.path.exists(file_path):
        return []
    
    logs = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    log_entry = json.loads(line)
                    logs.append(log_entry)
                except json.JSONDecodeError:
                    continue
    
    # Sort by timestamp (most recent first) and limit
    logs.sort(key=lambda x: x.get('ts', 0), reverse=True)
    return logs[:limit]
