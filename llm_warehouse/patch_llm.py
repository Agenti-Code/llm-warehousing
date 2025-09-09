import inspect
import json
import os
import time
from typing import Any

import wrapt

from .transport import send


def _serialize(obj: Any) -> Any:
    """Best-effort serialization for OpenAI SDK objects and common Python types."""
    try:
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        if hasattr(obj, "dict"):
            return obj.dict()
    except Exception:
        pass
    try:
        json.dumps(obj)
        return obj
    except Exception:
        return str(obj)


def is_debug() -> bool:
    return os.getenv("LLM_WAREHOUSE_DEBUG", "0") not in {"", "0", "false", "False", "no", "off"}

# Track if patch has already been applied to prevent duplicate wrapping
_PATCH_APPLIED: bool = False


def _wrap_create(owner: Any, attr_path: str) -> None:
    """Wrap an OpenAI resource's create method to capture request/response.

    owner: A class or instance that exposes a callable attribute `create`.
    attr_path: Logical label used for diagnostics (e.g., "responses.create").
    """
    if not hasattr(owner, "create"):
        return

    original = getattr(owner, "create")
    if is_debug():
        try:
            owner_name = getattr(owner, "__name__", repr(owner))
        except Exception:
            owner_name = repr(owner)
        print(f"[llm-warehouse] wrapping {owner_name}.create as {attr_path}")

    @wrapt.decorator
    def wrapper(wrapped, instance, args, kwargs):  # type: ignore[no-untyped-def]
        t0 = time.time()
        record = {
            "sdk_method": attr_path,
            "request": _serialize({"args": args, "kwargs": kwargs}),
        }
        try:
            result = wrapped(*args, **kwargs)

            # Streaming is typically signaled by a `stream=True` kwarg. If streaming,
            # do not buffer tokens; just emit metadata and return through.
            if kwargs.get("stream") is True:
                record["streaming"] = True
                record["latency_s"] = time.time() - t0
                send(record)
                return result

            # Some SDK paths may return a generator/iterator for streaming
            if inspect.isgenerator(result):
                record["streaming"] = True
                record["latency_s"] = time.time() - t0
                send(record)
                return result

            record["latency_s"] = time.time() - t0
            print(f"[llm-warehouse] raw result: {result}")
            # Extract chat completion from APIResponse if available
            # Debug: print all available attributes and keys
            print(f'DEBUG: {is_debug()}')
            if is_debug():
                print(f"[llm-warehouse] result type: {type(result)}")
                print(f"[llm-warehouse] result dir: {dir(result)}")
                if hasattr(result, '__dict__'):
                    print(f"[llm-warehouse] result.__dict__: {result.__dict__}")
            if is_debug():
                print(f"[llm-warehouse] result: {result}")
            if hasattr(result, 'parse') and callable(getattr(result, 'parse')):
                if is_debug():
                    # If result has a parse() method, call it to get the actual data
                    print(f"[llm-warehouse] calling result.parse()")
                record["response"] = _serialize(result.parse())
            else:
                record["response"] = _serialize(result)
            try:
                record["request_id"] = getattr(result, "_request_id", None)
            except Exception:
                pass
            send(record)
            return result
        except Exception as e:  # noqa: BLE001
            record["latency_s"] = time.time() - t0
            record["error"] = repr(e)
            send(record)
            raise

    # Handle async create separately without wrapt (cleaner for coroutines)
    if inspect.iscoroutinefunction(original):

        async def async_wrapper(*args, **kwargs):  # type: ignore[no-untyped-def]
            t0 = time.time()
            record = {
                "sdk_method": attr_path,
                "request": _serialize({"args": args, "kwargs": kwargs}),
            }
            try:
                result = await original(*args, **kwargs)
                if kwargs.get("stream") is True:
                    record["streaming"] = True
                    record["latency_s"] = time.time() - t0
                    send(record)
                    return result
                record["latency_s"] = time.time() - t0
                record["response"] = _serialize(result)
                try:
                    record["request_id"] = getattr(result, "_request_id", None)
                except Exception:
                    pass
                send(record)
                return result
            except Exception as e:  # noqa: BLE001
                record["latency_s"] = time.time() - t0
                record["error"] = repr(e)
                send(record)
                raise

        setattr(owner, "create", async_wrapper)
    else:
        setattr(owner, "create", wrapper(original))


def _wrap_method(owner: Any, method_name: str, attr_path: str) -> None:
    if not hasattr(owner, method_name):
        return
    original = getattr(owner, method_name)
    if is_debug():
        try:
            owner_name = getattr(owner, "__name__", repr(owner))
        except Exception:
            owner_name = repr(owner)
        print(f"[llm-warehouse] wrapping {owner_name}.{method_name} as {attr_path}")

    if inspect.iscoroutinefunction(original):

        async def async_wrapper(*args, **kwargs):  # type: ignore[no-untyped-def]
            t0 = time.time()
            record = {
                "sdk_method": attr_path,
                "request": _serialize({"args": args, "kwargs": kwargs}),
            }
            try:
                result = await original(*args, **kwargs)
                record["latency_s"] = time.time() - t0
                record["response"] = _serialize(result)
                send(record)
                return result
            except Exception as e:  # noqa: BLE001
                record["latency_s"] = time.time() - t0
                record["error"] = repr(e)
                send(record)
                raise

        setattr(owner, method_name, async_wrapper)
    else:

        def sync_wrapper(*args, **kwargs):  # type: ignore[no-untyped-def]
            t0 = time.time()
            record = {
                "sdk_method": attr_path,
                "request": _serialize({"args": args, "kwargs": kwargs}),
            }
            try:
                result = original(*args, **kwargs)
                record["latency_s"] = time.time() - t0
                record["response"] = _serialize(result)
                send(record)
                return result
            except Exception as e:  # noqa: BLE001
                record["latency_s"] = time.time() - t0
                record["error"] = repr(e)
                send(record)
                raise

        setattr(owner, method_name, sync_wrapper)


def install_patch() -> None:
    """Attempts to patch OpenAI and Anthropic Python SDK resource classes in-place.

    This targets:
    - OpenAI: Responses API and Chat Completions, sync and async
    - Anthropic: Messages API, sync and async
    Failing imports are ignored to be resilient across SDK versions.
    """
    global _PATCH_APPLIED
    if _PATCH_APPLIED:
        if is_debug():
            print("[llm-warehouse] patch already applied, skipping")
        return
    
    if is_debug():
        print("[llm-warehouse] install_patch starting")

    # === OpenAI SDK Patches ===
    
    # Responses API (sync)
    try:
        from openai.resources.responses import Responses
        _wrap_create(Responses, "openai.responses.create")
    except Exception:
        pass

    # Chat Completions API (sync)
    try:
        from openai.resources.chat.completions import Completions as ChatCompletions
        _wrap_create(ChatCompletions, "openai.chat.completions.create")
    except Exception:
        pass

    # Responses API (async)
    try:
        from openai.resources.responses import AsyncResponses
        _wrap_create(AsyncResponses, "openai.async.responses.create")
    except Exception:
        pass

    # Chat Completions API (async)
    try:
        from openai.resources.chat.completions import (
            AsyncCompletions as AsyncChatCompletions,
        )
        _wrap_create(AsyncChatCompletions, "openai.async.chat.completions.create")
    except Exception:
        pass

    # === Anthropic SDK Patches ===
    
    # Messages API (sync)
    try:
        from anthropic.resources.messages import Messages
        _wrap_create(Messages, "anthropic.messages.create")
    except Exception:
        pass

    # Messages API (async)  
    try:
        from anthropic.resources.messages import AsyncMessages
        _wrap_create(AsyncMessages, "anthropic.async.messages.create")
    except Exception:
        pass

    _PATCH_APPLIED = True
    if is_debug():
        print("[llm-warehouse] install_patch complete")


