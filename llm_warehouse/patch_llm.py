import inspect
import json
import os
import time
from typing import Any

import wrapt

from .transport import send

def _serialize(obj: Any) -> Any:
    """Best-effort serialization for OpenAI SDK, LangChain, and common Python types."""
    import uuid
    
    def _make_serializable(value: Any) -> Any:
        """Recursively convert objects to JSON-serializable types."""
        if isinstance(value, uuid.UUID):
            return str(value)
        elif isinstance(value, dict):
            return {k: _make_serializable(v) for k, v in value.items()}
        elif isinstance(value, (list, tuple)):
            return [_make_serializable(item) for item in value]
        else:
            return value
    
    try:
        # Handle LangChain Message objects
        if hasattr(obj, "content") and hasattr(obj, "type"):
            # This is likely a LangChain message object
            result = {"content": obj.content, "type": obj.type}
            if hasattr(obj, "additional_kwargs"):
                result["additional_kwargs"] = obj.additional_kwargs
            if hasattr(obj, "response_metadata"):
                result["response_metadata"] = obj.response_metadata
            if hasattr(obj, "usage_metadata"):
                result["usage_metadata"] = obj.usage_metadata
            if hasattr(obj, "id"):
                result["id"] = obj.id
            result = _make_serializable(result)
            if is_debug():
                print(f"[llm-warehouse] result in _serialize 1: {result}")
            return result
        
        # Handle LangChain Generation objects
        if hasattr(obj, "text") and hasattr(obj, "generation_info"):
            result = {
                "text": obj.text,
                "generation_info": obj.generation_info
            }
            result = _make_serializable(result)
            if is_debug():
                print(f"[llm-warehouse] result in _serialize 2: {result}")
            return result
        
        # Handle standard serialization methods
        if hasattr(obj, "to_dict"):
            result = obj.to_dict()
            result = _make_serializable(result)
            if is_debug():
                print(f"[llm-warehouse] result in _serialize 3: {result}")
            return result
        if hasattr(obj, "model_dump"):
            result = obj.model_dump()
            result = _make_serializable(result)
            if is_debug():
                print(f"[llm-warehouse] result in _serialize 4: {result}")
            return result
        if hasattr(obj, "dict"):
            result = obj.dict()
            result = _make_serializable(result)
            if is_debug():
                print(f"[llm-warehouse] result in _serialize 5: {result}")
            return result
    except Exception:
        pass
    
    try:
        # Make a copy and ensure it's serializable
        serializable_obj = _make_serializable(obj)
        json.dumps(serializable_obj)
        if is_debug():
            print(f"[llm-warehouse] result in _serialize 6: {serializable_obj}")
        return serializable_obj
    except Exception:
        result = str(obj)
        if is_debug():
            print(f"[llm-warehouse] result in _serialize 7: {result}")
        return result


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
                
                # Handle streaming responses early
                if kwargs.get("stream") is True:
                    record["streaming"] = True
                    record["latency_s"] = time.time() - t0
                    send(record)
                    return result
                
                # Calculate latency after completion
                record["latency_s"] = time.time() - t0
                
                # Enhanced response serialization for async completions
                if is_debug():
                    print(f"[llm-warehouse] async create result type: {type(result)}")
                    print(f"[llm-warehouse] async create result: {result}")
                
                # Handle async streaming responses
                if hasattr(result, '__aiter__'):
                    record["streaming"] = True
                    record["response"] = "async_stream_response"
                    send(record)
                    return result
                
                # Serialize the completed response
                record["response"] = _serialize(result)
                
                # Extract request ID if available
                try:
                    record["request_id"] = getattr(result, "_request_id", None) or getattr(result, "id", None)
                except Exception:
                    pass
                
                # Send the log after completion
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
                
                # Calculate latency after completion
                record["latency_s"] = time.time() - t0
                
                # Enhanced response serialization for async completions
                if is_debug():
                    print(f"[llm-warehouse] async result type: {type(result)}")
                    print(f"[llm-warehouse] async result: {result}")
                
                # Handle streaming responses
                if hasattr(result, '__aiter__'):
                    record["streaming"] = True
                    record["response"] = "async_stream_response"
                    send(record)
                    return result
                
                # Serialize the completed response
                print(f"[llm-warehouse] result in _wrap_method: {result}")
                record["response"] = _serialize(result)
                
                # Extract request ID if available
                try:
                    record["request_id"] = getattr(result, "_request_id", None) or getattr(result, "id", None)
                except Exception:
                    pass
                
                # Send the log after completion
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
    - LangChain: ChatOpenAI and other LLM wrappers, sync and async
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

    # # Chat Completions API (async)
    # try:
    #     from openai.resources.chat.completions import (
    #         AsyncCompletions as AsyncChatCompletions,
    #     )
    #     _wrap_create(AsyncChatCompletions, "openai.async.chat.completions.create")
    # except Exception:
    #     pass

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

    # === LangChain SDK Patches ===
    
    # ChatOpenAI async methods
    try:
        from langchain_openai import ChatOpenAI
        _wrap_method(ChatOpenAI, "ainvoke", "langchain.openai.chat.ainvoke")
        # _wrap_method(ChatOpenAI, "agenerate", "langchain.openai.chat.agenerate")
        # _wrap_method(ChatOpenAI, "astream", "langchain.openai.chat.astream")
        # Also wrap sync methods for completeness
        _wrap_method(ChatOpenAI, "invoke", "langchain.openai.chat.invoke")
        # _wrap_method(ChatOpenAI, "generate", "langchain.openai.chat.generate")
        # _wrap_method(ChatOpenAI, "stream", "langchain.openai.chat.stream")
    except Exception as e:
        if is_debug():
            print(f"[llm-warehouse] Failed to patch langchain_openai.ChatOpenAI: {e}")
        pass

    # ChatAnthropic async methods (if available)
    try:
        from langchain_anthropic import ChatAnthropic
        _wrap_method(ChatAnthropic, "ainvoke", "langchain.anthropic.chat.ainvoke")
        # _wrap_method(ChatAnthropic, "agenerate", "langchain.anthropic.chat.agenerate")
        # _wrap_method(ChatAnthropic, "astream", "langchain.anthropic.chat.astream")
        # Also wrap sync methods for completeness
        _wrap_method(ChatAnthropic, "invoke", "langchain.anthropic.chat.invoke")
        # _wrap_method(ChatAnthropic, "generate", "langchain.anthropic.chat.generate")
        # _wrap_method(ChatAnthropic, "stream", "langchain.anthropic.chat.stream")
    except Exception as e:
        if is_debug():
            print(f"[llm-warehouse] Failed to patch langchain_anthropic.ChatAnthropic: {e}")
        pass

    # Generic LLM classes (fallback for other providers)
    try:
        from langchain_community.llms import OpenAI as LangChainOpenAI
        _wrap_method(LangChainOpenAI, "ainvoke", "langchain.community.openai.ainvoke")
        # _wrap_method(LangChainOpenAI, "agenerate", "langchain.community.openai.agenerate")
        _wrap_method(LangChainOpenAI, "invoke", "langchain.community.openai.invoke")
        # _wrap_method(LangChainOpenAI, "generate", "langchain.community.openai.generate")
    except Exception as e:
        if is_debug():
            print(f"[llm-warehouse] Failed to patch langchain_community.llms.OpenAI: {e}")
        pass

    _PATCH_APPLIED = True
    if is_debug():
        print("[llm-warehouse] install_patch complete")


