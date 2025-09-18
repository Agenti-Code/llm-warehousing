# LLM Warehouse

🏠 **Auto-capture OpenAI and Anthropic LLM calls for warehousing**

A lightweight Python library that automatically logs all your OpenAI and Anthropic API calls to various storage backends, including your own Flask app, Supabase, or local files.

## 🚀 Quick Start

### Installation

```bash
pip install llm-warehouse
```

Or for the latest development version:

```bash
pip install git+https://github.com/sinanozdemir/llm-warehouse.git
```

### Basic Usage

For automatic patching on import, set environment variables:

```bash
export LLM_WAREHOUSE_API_KEY="your-warehouse-api-key"
export LLM_WAREHOUSE_URL="https://your-warehouse.com"
```

Then just import any LLM library AFTER importing this package - logging happens automatically:

```python
import llm_warehouse  # BEFORE openai or anthropic

import openai  # Automatically patched!
# or
import anthropic  # Automatically patched!
```

Sample usage:

```python
import llm_warehouse

# Now use OpenAI/Anthropic normally - all calls are automatically logged!
import openai
client = openai.Client()
response = client.chat.completions.create(
    model="gpt-4.1-mini",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

## 📊 What Gets Logged

- **Request data**: Model, messages, parameters
- **Response data**: Completions, token usage, timing
- **Metadata**: Timestamps, SDK method, streaming info
- **Errors**: API errors and exceptions

## 🔧 Configuration Options

## 🛡️ Environment Variables

| Variable | Description |
|----------|-------------|
| `LLM_WAREHOUSE_API_KEY` | Your warehouse API token (enables auto-patching) |
| `LLM_WAREHOUSE_URL` | Your warehouse URL |

## 🔄 Programmatic Control (for advanced users)

```python
import llm_warehouse

# Enable logging
llm_warehouse.patch(warehouse_url="...", api_key="...")

# Disable logging
llm_warehouse.unpatch()

# Check status
if llm_warehouse.is_patched():
    print("LLM calls are being logged")
```

## 🏗️ Backend Options

### API Warehouse Backend
Use with the included API (recommended):

```python
llm_warehouse.patch(
    warehouse_url="https://your-warehouse.com",
    api_key="your-warehouse-api-key"
)
```

### Supabase Backend
Direct integration with Supabase:

```python
llm_warehouse.patch(
    supabase_url="https://your-project.supabase.co",
    supabase_key="your-supabase-anon-key"
)
```

### Local File Backend
For development and testing:

```python
llm_warehouse.patch(log_file="llm_calls.jsonl")
```

## 📦 Features

- ✅ **Zero-configuration**: Works out of the box with environment variables
- ✅ **Multiple backends**: Flask warehouse, Supabase, local files
- ✅ **Async support**: Full async/await compatibility
- ✅ **Streaming support**: Captures streaming responses
- ✅ **Error handling**: Logs API errors and exceptions
- ✅ **Minimal overhead**: Designed for production use
- ✅ **Thread-safe**: Works in multi-threaded applications

## 🧪 Development

```bash
git clone https://github.com/sinanozdemir/llm-warehouse.git
cd llm-warehouse/llm-warehouse-package
pip install -e ".[dev]"
```

Run tests:
```bash
pytest
```

Format code:
```bash
black llm_warehouse/
isort llm_warehouse/
```

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.
