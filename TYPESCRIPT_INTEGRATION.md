# TypeScript/JavaScript Integration Guide

> **Direct API integration for TypeScript/JavaScript applications**

This guide shows how to integrate with the LLM Warehouse API directly using fetch calls, perfect for TypeScript/JavaScript applications that want to log LLM calls without using the Python package.

## Quick Start

### 1. Get Your API Token

First, you'll need an API token from the LLM Warehouse.

### 2. Configuration

```typescript
// Configuration
const LLM_WAREHOUSE_BASE_URL = 'https://warehouse.useagenti.com";
const API_TOKEN = 'your-api-token-here'; // Your warehouse API token

// Headers for API calls
const getHeaders = () => ({
  'Content-Type': 'application/json',
  'Authorization': `Bearer ${API_TOKEN}`
});
```

## TypeScript Interfaces

```typescript
interface LLMCallData {
  sdk_method: string;           // e.g., "openai.chat.completions.create"
  request: {
    args: any[];               // Usually empty for most APIs
    kwargs: Record<string, any>; // The actual parameters (model, messages, etc.)
  };
  response?: any;              // The LLM response (optional if error occurred)
  latency_s?: number;          // Request duration in seconds
  error?: string;              // Error message if request failed
  request_id?: string;         // LLM provider's request ID
  timestamp?: string;          // ISO timestamp
}

interface LogResponse {
  message: string;             // Success message
  task_id: string;            // Background task ID
  status: string;             // "queued"
  status_url: string;         // URL to check task status
}
```

## Core Logging Function

```typescript
async function logLLMCall(callData: LLMCallData): Promise<LogResponse> {
  try {
    const response = await fetch(`${LLM_WAREHOUSE_BASE_URL}/llm-logs`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(callData)
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Failed to log LLM call:', error);
    throw error;
  }
}
```

## OpenAI Integration

### Installation

First, install the official OpenAI Node.js SDK:

```bash
npm install openai
# or
yarn add openai
```

### Using the Official OpenAI Node SDK

The guide works perfectly with the [official OpenAI Node.js SDK](https://github.com/openai/openai-node). Here's how to wrap their SDK calls:

```typescript
import OpenAI from 'openai';

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

async function callOpenAIWithLogging(
  messages: any[], 
  model: string = 'gpt-4',
  options: Record<string, any> = {}
): Promise<any> {
  const startTime = Date.now();
  
  try {
    // Use the official OpenAI SDK
    const result = await openai.chat.completions.create({
      model,
      messages,
      ...options
    });

    const endTime = Date.now();

    // Log success to warehouse
    await logLLMCall({
      sdk_method: 'openai.chat.completions.create',
      request: {
        args: [],
        kwargs: {
          model,
          messages,
          ...options
        }
      },
      response: result,
      latency_s: (endTime - startTime) / 1000,
      request_id: result.id,
      timestamp: new Date().toISOString()
    });

    return result;
  } catch (error) {
    const endTime = Date.now();
    
    // Log error to warehouse
    await logLLMCall({
      sdk_method: 'openai.chat.completions.create',
      request: {
        args: [],
        kwargs: {
          model,
          messages,
          ...options
        }
      },
      latency_s: (endTime - startTime) / 1000,
      error: error.toString(),
      timestamp: new Date().toISOString()
    });

    throw error;
  }
}

// Alternative: Raw fetch approach (if you prefer not to use the SDK)
async function callOpenAIRawWithLogging(
  messages: any[], 
  model: string = 'gpt-4',
  options: Record<string, any> = {}
): Promise<any> {
  const startTime = Date.now();
  
  try {
    // Direct fetch approach
    const openaiResponse = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${process.env.OPENAI_API_KEY}`
      },
      body: JSON.stringify({
        model,
        messages,
        ...options
      })
    });

    const result = await openaiResponse.json();
    const endTime = Date.now();

    // Log success to warehouse
    await logLLMCall({
      sdk_method: 'openai.chat.completions.create',
      request: {
        args: [],
        kwargs: {
          model,
          messages,
          ...options
        }
      },
      response: result,
      latency_s: (endTime - startTime) / 1000,
      request_id: result.id,
      timestamp: new Date().toISOString()
    });

    return result;
  } catch (error) {
    const endTime = Date.now();
    
    // Log error to warehouse
    await logLLMCall({
      sdk_method: 'openai.chat.completions.create',
      request: {
        args: [],
        kwargs: {
          model,
          messages,
          ...options
        }
      },
      latency_s: (endTime - startTime) / 1000,
      error: error.toString(),
      timestamp: new Date().toISOString()
    });

    throw error;
  }
}
```

### OpenAI Usage Example

```typescript
// Using the official OpenAI SDK (recommended)
const result = await callOpenAIWithLogging([
  { role: 'user', content: 'Hello, how are you?' }
], 'gpt-4');

// With additional options
const result = await callOpenAIWithLogging([
  { role: 'system', content: 'You are a helpful assistant.' },
  { role: 'user', content: 'Explain quantum computing' }
], 'gpt-4', {
  temperature: 0.7,
  max_tokens: 500,
  stream: false
});

// For streaming responses with the official SDK
async function streamOpenAIWithLogging(
  messages: any[],
  model: string = 'gpt-4',
  options: Record<string, any> = {}
) {
  const startTime = Date.now();
  let fullResponse = '';
  
  try {
    const stream = await openai.chat.completions.create({
      model,
      messages,
      stream: true,
      ...options
    });

    for await (const chunk of stream) {
      const content = chunk.choices[0]?.delta?.content || '';
      fullResponse += content;
      // Yield content for real-time display
      yield content;
    }

    const endTime = Date.now();

    // Log the complete interaction
    await logLLMCall({
      sdk_method: 'openai.chat.completions.create',
      request: {
        args: [],
        kwargs: {
          model,
          messages,
          stream: true,
          ...options
        }
      },
      response: {
        choices: [{ message: { content: fullResponse } }],
        // Note: streaming responses don't have the same structure as non-streaming
      },
      latency_s: (endTime - startTime) / 1000,
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    const endTime = Date.now();
    
    await logLLMCall({
      sdk_method: 'openai.chat.completions.create',
      request: {
        args: [],
        kwargs: {
          model,
          messages,
          stream: true,
          ...options
        }
      },
      latency_s: (endTime - startTime) / 1000,
      error: error.toString(),
      timestamp: new Date().toISOString()
    });

    throw error;
  }
}
```

### Advanced OpenAI SDK Integration

The official OpenAI Node.js SDK has excellent TypeScript support and many advanced features. Here's how to integrate them with logging:

```typescript
import OpenAI from 'openai';

// Advanced OpenAI wrapper class
class LoggedOpenAI {
  private client: OpenAI;

  constructor(apiKey?: string) {
    this.client = new OpenAI({
      apiKey: apiKey || process.env.OPENAI_API_KEY,
    });
  }

  async createChatCompletion(
    params: OpenAI.Chat.ChatCompletionCreateParams
  ): Promise<OpenAI.Chat.ChatCompletion> {
    const startTime = Date.now();
    
    try {
      const result = await this.client.chat.completions.create(params);
      const endTime = Date.now();

      await logLLMCall({
        sdk_method: 'openai.chat.completions.create',
        request: {
          args: [],
          kwargs: params
        },
        response: result,
        latency_s: (endTime - startTime) / 1000,
        request_id: result.id,
        timestamp: new Date().toISOString()
      });

      return result;
    } catch (error) {
      const endTime = Date.now();
      
      await logLLMCall({
        sdk_method: 'openai.chat.completions.create',
        request: {
          args: [],
          kwargs: params
        },
        latency_s: (endTime - startTime) / 1000,
        error: error.toString(),
        timestamp: new Date().toISOString()
      });

      throw error;
    }
  }

  // For other OpenAI endpoints
  async createEmbedding(
    params: OpenAI.EmbeddingCreateParams
  ): Promise<OpenAI.CreateEmbeddingResponse> {
    const startTime = Date.now();
    
    try {
      const result = await this.client.embeddings.create(params);
      const endTime = Date.now();

      await logLLMCall({
        sdk_method: 'openai.embeddings.create',
        request: {
          args: [],
          kwargs: params
        },
        response: result,
        latency_s: (endTime - startTime) / 1000,
        request_id: result.object,
        timestamp: new Date().toISOString()
      });

      return result;
    } catch (error) {
      const endTime = Date.now();
      
      await logLLMCall({
        sdk_method: 'openai.embeddings.create',
        request: {
          args: [],
          kwargs: params
        },
        latency_s: (endTime - startTime) / 1000,
        error: error.toString(),
        timestamp: new Date().toISOString()
      });

      throw error;
    }
  }
}

// Usage with proper TypeScript types
const loggedOpenAI = new LoggedOpenAI();

const response = await loggedOpenAI.createChatCompletion({
  model: 'gpt-4',
  messages: [
    { role: 'user', content: 'Hello!' }
  ],
  temperature: 0.7,
  max_tokens: 100
});
```

## Anthropic Integration

### Basic Anthropic Messages

```typescript
async function callAnthropicWithLogging(
  messages: any[],
  model: string = 'claude-3-haiku-20240307',
  maxTokens: number = 1000,
  options: Record<string, any> = {}
): Promise<any> {
  const startTime = Date.now();
  
  try {
    const anthropicResponse = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': process.env.ANTHROPIC_API_KEY,
        'anthropic-version': '2023-06-01'
      },
      body: JSON.stringify({
        model,
        messages,
        max_tokens: maxTokens,
        ...options
      })
    });

    const result = await anthropicResponse.json();
    const endTime = Date.now();

    // Log success to warehouse
    await logLLMCall({
      sdk_method: 'anthropic.messages.create',
      request: {
        args: [],
        kwargs: {
          model,
          messages,
          max_tokens: maxTokens,
          ...options
        }
      },
      response: result,
      latency_s: (endTime - startTime) / 1000,
      request_id: result.id,
      timestamp: new Date().toISOString()
    });

    return result;
  } catch (error) {
    const endTime = Date.now();
    
    // Log error to warehouse
    await logLLMCall({
      sdk_method: 'anthropic.messages.create',
      request: {
        args: [],
        kwargs: {
          model,
          messages,
          max_tokens: maxTokens,
          ...options
        }
      },
      latency_s: (endTime - startTime) / 1000,
      error: error.toString(),
      timestamp: new Date().toISOString()
    });

    throw error;
  }
}
```

### Anthropic Usage Example

```typescript
// Simple message
const result = await callAnthropicWithLogging([
  { role: 'user', content: 'Hello, how are you?' }
], 'claude-3-haiku-20240307', 1000);

// With system message and options
const result = await callAnthropicWithLogging([
  { role: 'user', content: 'Write a poem about the ocean' }
], 'claude-3-sonnet-20240229', 2000, {
  temperature: 0.8,
  top_p: 0.9
});
```

## Error Handling & Best Practices

### Robust Error Handling

```typescript
async function safeLogLLMCall(callData: LLMCallData): Promise<void> {
  try {
    await logLLMCall(callData);
  } catch (error) {
    // Don't let logging errors break your main application
    console.error('Warning: Failed to log LLM call to warehouse:', error);
    
    // Optional: Store locally as fallback
    const fallbackLog = {
      timestamp: new Date().toISOString(),
      ...callData
    };
    localStorage.setItem(
      `llm_call_${Date.now()}`, 
      JSON.stringify(fallbackLog)
    );
  }
}
```

### Environment Variables

Create a `.env` file:

```bash
# LLM Provider Keys
OPENAI_API_KEY=sk-your-openai-key-here
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here

# LLM Warehouse Configuration
LLM_WAREHOUSE_BASE_URL=https://your-warehouse-domain.com
LLM_WAREHOUSE_TOKEN=your-warehouse-api-token-here
```

### Generic LLM Wrapper

```typescript
interface LLMProvider {
  name: string;
  call: (messages: any[], options?: any) => Promise<any>;
}

class LLMClient {
  constructor(private warehouseUrl: string, private warehouseToken: string) {}

  async callWithLogging(
    provider: LLMProvider,
    messages: any[],
    options: any = {}
  ): Promise<any> {
    const startTime = Date.now();
    const sdkMethod = `${provider.name}.create`;
    
    try {
      const result = await provider.call(messages, options);
      const endTime = Date.now();

      await this.logCall({
        sdk_method: sdkMethod,
        request: { args: [], kwargs: { messages, ...options } },
        response: result,
        latency_s: (endTime - startTime) / 1000,
        request_id: result.id,
        timestamp: new Date().toISOString()
      });

      return result;
    } catch (error) {
      const endTime = Date.now();
      
      await this.logCall({
        sdk_method: sdkMethod,
        request: { args: [], kwargs: { messages, ...options } },
        latency_s: (endTime - startTime) / 1000,
        error: error.toString(),
        timestamp: new Date().toISOString()
      });

      throw error;
    }
  }

  private async logCall(callData: LLMCallData): Promise<void> {
    await safeLogLLMCall(callData);
  }
}
```

## Querying Your Logs

### Get Recent Logs

```typescript
async function getRecentLogs(limit: number = 10): Promise<any[]> {
  const response = await fetch(`${LLM_WAREHOUSE_BASE_URL}/llm-logs?limit=${limit}`, {
    headers: getHeaders()
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch logs: ${response.statusText}`);
  }

  const data = await response.json();
  return data.logs;
}
```

### Search by Model

```typescript
async function getLogsByModel(model: string, limit: number = 10): Promise<any[]> {
  const response = await fetch(
    `${LLM_WAREHOUSE_BASE_URL}/llm-logs?model=${encodeURIComponent(model)}&limit=${limit}`,
    { headers: getHeaders() }
  );

  if (!response.ok) {
    throw new Error(`Failed to fetch logs: ${response.statusText}`);
  }

  const data = await response.json();
  return data.logs;
}
```

## React Hook Example

```typescript
import { useState, useCallback } from 'react';

export function useLLMWithLogging() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const callLLM = useCallback(async (
    provider: 'openai' | 'anthropic',
    messages: any[],
    options: any = {}
  ) => {
    setLoading(true);
    setError(null);

    try {
      let result;
      if (provider === 'openai') {
        result = await callOpenAIWithLogging(messages, options.model, options);
      } else {
        result = await callAnthropicWithLogging(messages, options.model, options.max_tokens, options);
      }
      return result;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return { callLLM, loading, error };
}
```

## Next Steps

1. **Set up your environment variables** with your API keys and warehouse token
2. **Test the integration** with a simple call to verify logging works
3. **Add error handling** appropriate for your application
4. **Monitor your logs** in the warehouse dashboard
5. **Scale as needed** - the warehouse handles async processing automatically

## Support

- Check the warehouse dashboard for logs and debugging
- API endpoint: `GET /llm-logs` for querying your data
- All logs are processed asynchronously for optimal performance
- Contact support if you need help with API token generation

---

*Happy logging! 🚀*
