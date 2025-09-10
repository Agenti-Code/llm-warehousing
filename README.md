# LLM Warehouse

🏠 **Auto-capture OpenAI and Anthropic LLM calls for warehousing**

A lightweight Python library that automatically logs all your OpenAI and Anthropic API calls to various storage backends, including your own Flask app, Supabase, or local files.

## 🚀 Quick Start

### Installation

```bash
pip install git+https://github.com/yourusername/llm-warehouse.git
```

### Basic Usage

```python
import llm_warehouse

# Option 1: Use with your own warehouse
llm_warehouse.patch(
    warehouse_url="https://your-warehouse.com",
    api_key="your-warehouse-api-key"
)

# Option 2: Use with Supabase
llm_warehouse.patch(
    supabase_url="https://your-project.supabase.co",
    supabase_key="your-supabase-anon-key"
)

# Option 3: Save to local file
llm_warehouse.patch(log_file="llm_calls.jsonl")

# Now use OpenAI/Anthropic normally - all calls are automatically logged!
import openai
client = openai.Client()
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

## 🎯 Automatic Setup (Recommended)

For automatic patching on import, set environment variables:

```bash
export LLM_WAREHOUSE_API_KEY="your-warehouse-api-key"
export LLM_WAREHOUSE_URL="https://your-warehouse.com"
```

Then just import any LLM library - logging happens automatically:

```python
import openai  # Automatically patched!
# or
import anthropic  # Automatically patched!
```

## 📊 What Gets Logged

- **Request data**: Model, messages, parameters
- **Response data**: Completions, token usage, timing
- **Metadata**: Timestamps, SDK method, streaming info
- **Errors**: API errors and exceptions

## 🔧 Configuration Options

```python
import llm_warehouse

# Configure multiple backends (fallback priority)
llm_warehouse.patch(
    warehouse_url="https://your-warehouse.com",
    api_key="your-warehouse-api-key",
    supabase_url="https://backup.supabase.co",
    supabase_key="backup-key",
    log_file="local-backup.jsonl",
    debug=True
)
```

## 📚 Storage Backends

### 1. **LLM Warehouse Dashboard** (recommended)
Deploy your own dashboard for advanced analytics:
- Web interface for viewing calls
- User management and API tokens
- Advanced filtering and search
- Repository: [llm-warehouse-dashboard](https://github.com/yourusername/llm-warehouse-dashboard)

### 2. **Supabase**
```python
llm_warehouse.patch(
    supabase_url="https://your-project.supabase.co",
    supabase_key="your-supabase-anon-key"
)
```

### 3. **Local Files**
```python
llm_warehouse.patch(log_file="llm_calls.jsonl")
```

## 🛡️ Environment Variables

| Variable | Description |
|----------|-------------|
| `OBSERVIFY_API_TOKEN` | Your warehouse API token (enables auto-patching) |
| `LLM_WAREHOUSE_URL` | Your warehouse URL |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_KEY` | Supabase anon key |
| `OBSERVIFY_DEBUG` | Enable debug logging |

## 🔄 Programmatic Control

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

## 🏗️ Related Projects

- **[LLM Warehouse Dashboard](https://github.com/yourusername/llm-warehouse-dashboard)** - Web interface and API for managing logged calls

## 📄 License

MIT License - see LICENSE file for details.