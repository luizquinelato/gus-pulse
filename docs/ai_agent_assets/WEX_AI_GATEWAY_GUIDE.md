# WEX AI Gateway Integration Guide

A complete, project-independent guide for integrating with the WEX AI Gateway using the OpenAI-compatible API. This guide covers basic setup, authentication, request/response patterns, and advanced features like batching, retries, and cost tracking.

---

## Table of Contents

1. [Overview](#overview)
2. [Available Endpoints & Capabilities](#available-endpoints--capabilities)
3. [Prerequisites](#prerequisites)
4. [Installation](#installation)
5. [Core Concepts](#core-concepts)
6. [Configuration](#configuration)
7. [Basic Usage](#basic-usage)
8. [Advanced Features](#advanced-features)
9. [Error Handling](#error-handling)
10. [Monitoring & Metrics](#monitoring--metrics)
11. [Best Practices](#best-practices)
12. [Complete Examples](#complete-examples)

---

## Overview

The **WEX AI Gateway** is an internal AI service that provides OpenAI-compatible endpoints for:
- **Text Embeddings**: Convert text to numerical vectors for semantic search and ML tasks
- **Text Generation**: Generate responses to prompts using language models
- **Chat Completions**: Run multi-turn conversations with context

The gateway acts as a proxy to various backend models (Azure OpenAI, local models, etc.) and provides:
- Automatic batching for efficiency
- Exponential backoff retry logic
- Cost tracking and performance metrics
- Async/await support for non-blocking operations

---

## Available Endpoints & Capabilities

The WEX AI Gateway is built on **LiteLLM v1.83.10**, a comprehensive AI proxy platform. Here's what's available:

### **Core AI Operations** (Most Common)

| Endpoint | Purpose | Example Use |
|----------|---------|-------------|
| `POST /v1/chat/completions` | Chat-based responses | Question answering, conversations |
| `POST /v1/completions` | Text completions | Continue text, content generation |
| `POST /v1/embeddings` | Generate embeddings | Semantic search, similarity matching |
| `POST /v1/moderations` | Content moderation | Check for harmful content |
| `GET /v1/models` | List available models | Discover what models are available |

### **Audio & Speech**

| Endpoint | Purpose |
|----------|---------|
| `POST /v1/audio/speech` | Convert text to speech |
| `POST /v1/audio/transcriptions` | Convert audio/speech to text |

### **Vision & Images**

| Endpoint | Purpose |
|----------|---------|
| `POST /v1/images/generations` | Generate images from text |
| `POST /v1/images/edits` | Edit/modify existing images |
| `POST /v1/ocr` | Optical character recognition |

### **Advanced Features**

| Feature | Purpose |
|---------|---------|
| **Assistants** | Create AI assistants with persistent state and tools |
| **Vector Stores** | RAG support - upload documents and query over them |
| **Batches** | Process large numbers of requests asynchronously |
| **Files** | Upload and manage files for processing |
| **RAG** | `POST /v1/rag/ingest`, `POST /v1/rag/query` |
| **Fine-tuning** | Train custom models (enterprise) |
| **Realtime** | WebSocket connections for streaming |
| **Search** | Integrated search capabilities |

### **Multiple Provider Support**

The gateway supports pass-throughs to:
- OpenAI (GPT-4, GPT-3.5, etc.)
- Azure OpenAI
- Anthropic (Claude)
- Google Vertex AI
- Cohere
- Mistral
- VLLM
- Bedrock
- And 100+ more models

### **Enterprise Features**

- Key & user management
- Team & organization management
- Budget tracking and cost limits
- Guardrails & content policies
- Access control & permissions
- Audit logging
- SSO integration
- SCIM v2 support

---

## Prerequisites

- **Python 3.8+** (3.9+ recommended)
- Access to a WEX AI Gateway instance with:
  - Base URL (e.g., `https://aips-ai-gateway.dev.ai-platform.int.wexfabric.com/`)
  - API Key (bearer token)
  - Model names available on the gateway
- Basic async Python knowledge (asyncio, await syntax)

---

## Installation

### 1. Install Required Package

```bash
pip install openai
```

The WEX AI Gateway is OpenAI-compatible, so we use the official OpenAI Python SDK.

### 2. Minimal Dependencies

```bash
# For async operations
pip install openai>=1.0.0

# For production use (logging, error handling)
pip install python-dotenv
```

---

## Core Concepts

### Request/Response Flow

```
Your Code
    ↓
AsyncOpenAI Client
    ↓
WEX AI Gateway (HTTP)
    ↓
Backend Models (Azure OpenAI, Local, etc.)
    ↓
Response → Async Chain → Your Code
```

### Key Components

| Component | Purpose |
|-----------|---------|
| `base_url` | Gateway endpoint URL |
| `api_key` | Authentication token |
| `model_name` | Model identifier on the gateway |
| `model_config` | Hyperparameters (temperature, max_tokens, etc.) |
| `AsyncOpenAI` | OpenAI-compatible async client |

---

## Configuration

### Configuration Object

Create a configuration dictionary with all necessary settings:

```python
config = {
    "base_url": "https://aips-ai-gateway.dev.ai-platform.int.wexfabric.com/",
    "api_key": "your-api-key-here",
    "model_config": {
        "temperature": 0.3,           # 0.0 = deterministic, 1.0 = creative
        "max_tokens": 700,            # Maximum response length
        "timeout": 120,               # Request timeout in seconds
        "max_retries": 3,             # Number of retry attempts
        "batch_size": 100             # For batch embeddings operations
    },
    "cost_config": {
        "cost_tier": "free"           # Track cost tier
    }
}
```

### Environment Variables

Store sensitive data in `.env`:

```bash
WEX_GATEWAY_BASE_URL=https://aips-ai-gateway.dev.ai-platform.int.wexfabric.com/
WEX_GATEWAY_API_KEY=your-api-key-here
WEX_GATEWAY_MODEL=azure-text-embedding-3-small
```

Load in your code:

```python
import os
from dotenv import load_dotenv

load_dotenv()

base_url = os.getenv("WEX_GATEWAY_BASE_URL")
api_key = os.getenv("WEX_GATEWAY_API_KEY")
model_name = os.getenv("WEX_GATEWAY_MODEL")
```

### Cost Tier and Model Selection

The `cost_tier` value is a classification helper for your integration settings. It is not required by the gateway itself, but it is useful for choosing the right model family and managing budget expectations.

Common `cost_tier` values:

- `free`: Low-cost models and embeddings, best for high-volume or exploratory workloads.
- `standard`: Mid-tier models with good quality and moderate cost.
- `premium`: High-end models for mission-critical or high-quality outputs.

#### How to use `cost_tier`

- Use `free` for defaults like `gpt-3.5-turbo` or `text-embedding-3-small`.
- Use `standard` for more capable but still economical options such as `gpt-4o`, `claude-3.5`, or `text-embedding-3-large`.
- Use `premium` for top-tier models like `gpt-4`, Claude 4, or enterprise-grade fine-tuned models.

> Tip: `cost_tier` should reflect the expected budget profile, not the exact gateway endpoint behavior.

### Recommended Models for Regular Analysis

For regular analysis, summarization, and general text workflows, the best cost/performance tradeoff is:

- **Primary recommendation**: `gpt-3.5-turbo`
- **When you need better quality**: `gpt-4`, `gemini-pro`, or `sonnet-4.6`
- **Fast and cheaper alternative**: `claude-3.5-sonic`

### Recommended Models for Embeddings

For embeddings, the best general choices are:

- **Default**: `text-embedding-3-small` — best cost/performance balance
- **Higher quality**: `text-embedding-3-large` — better semantic accuracy at higher cost
- **Budget/local fallback**: `all-MiniLM-L6-v2` or another local embedding option if supported

For a fuller list of available models and recommended selections, see `WEX_AI_GATEWAY_MODEL_CATALOG.md`.

---

## Basic Usage

### 1. Initialize the Client

```python
import asyncio
from openai import AsyncOpenAI

async def main():
    # Create OpenAI-compatible client pointing to WEX Gateway
    client = AsyncOpenAI(
        base_url="https://aips-ai-gateway.dev.ai-platform.int.wexfabric.com/",
        api_key="your-api-key",
        timeout=120
    )
    
    # Your code here...
    
    await client.close()  # Always close!

# Run async main
asyncio.run(main())
```

### 2. Generate Embeddings (Simple)

Convert a single text to a vector:

```python
async def get_embedding(client, text: str):
    """Get embedding for a single text"""
    response = await client.embeddings.create(
        model="azure-text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

# Usage
async with AsyncOpenAI(...) as client:
    embedding = await get_embedding(client, "Hello, world!")
    print(f"Embedding shape: {len(embedding)} dimensions")
```

### 3. Generate Text (Simple)

Send a prompt and get a response:

```python
async def ask_question(client, prompt: str) -> str:
    """Ask the AI a question and get a response"""
    response = await client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=500
    )
    return response.choices[0].message.content

# Usage
async with AsyncOpenAI(...) as client:
    answer = await ask_question(client, "What is Python?")
    print(answer)
```

---

## Advanced Features

### Batching for Embeddings

Process multiple texts efficiently with batching (important for large datasets):

```python
async def batch_embeddings(client, texts: list, batch_size: int = 100):
    """Generate embeddings for multiple texts with batching"""
    all_embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        
        response = await client.embeddings.create(
            model="azure-text-embedding-3-small",
            input=batch
        )
        
        batch_embeddings = [item.embedding for item in response.data]
        all_embeddings.extend(batch_embeddings)
        
        print(f"Processed batch {i//batch_size + 1}...")
    
    return all_embeddings

# Usage
texts = ["Document 1", "Document 2", ..., "Document 1000"]
embeddings = await batch_embeddings(client, texts, batch_size=100)
```

### Exponential Backoff Retries

Automatically retry failed requests with increasing delays:

```python
import asyncio

async def request_with_retries(client, max_retries: int = 3):
    """Make a request with exponential backoff on failure"""
    
    for attempt in range(max_retries):
        try:
            response = await client.embeddings.create(
                model="azure-text-embedding-3-small",
                input="test"
            )
            return response
            
        except Exception as e:
            if attempt == max_retries - 1:
                # Final attempt failed
                raise e
            else:
                # Wait before retry: 2^attempt seconds (1s, 2s, 4s, ...)
                wait_time = 2 ** attempt
                print(f"Attempt {attempt + 1} failed. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
```

### Cost Tracking

Monitor costs and token usage:

```python
class GatewayClient:
    def __init__(self, base_url: str, api_key: str):
        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key)
        self.total_cost = 0.0
        self.request_count = 0
    
    async def generate_embeddings(self, texts: list):
        """Generate embeddings and track cost"""
        response = await self.client.embeddings.create(
            model="azure-text-embedding-3-small",
            input=texts
        )
        
        # Track usage
        if hasattr(response, 'usage') and response.usage:
            tokens = response.usage.total_tokens
            cost = tokens * 0.0001  # $0.0001 per token (example)
            self.total_cost += cost
            self.request_count += 1
            
            print(f"Tokens used: {tokens}, Cost: ${cost:.4f}")
        
        return [item.embedding for item in response.data]
    
    def get_cost_summary(self):
        """Get cost and usage summary"""
        return {
            "total_cost": self.total_cost,
            "request_count": self.request_count,
            "avg_cost_per_request": self.total_cost / max(self.request_count, 1)
        }
```

### Health Checks

Verify gateway connectivity:

```python
async def health_check(client):
    """Check if gateway is accessible"""
    try:
        response = await client.embeddings.create(
            model="azure-text-embedding-3-small",
            input=["health check"]
        )
        
        if response and len(response.data) > 0:
            return {"status": "healthy"}
        else:
            return {"status": "unhealthy", "reason": "No embeddings returned"}
            
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

# Usage
health = await health_check(client)
print(f"Gateway health: {health}")
```

---

## Error Handling

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `AuthenticationError` | Invalid API key | Check `api_key` and permissions |
| `APIConnectionError` | Cannot reach gateway | Verify `base_url` and network |
| `RateLimitError` | Too many requests | Implement backoff, reduce batch size |
| `APITimeoutError` | Request took too long | Increase `timeout`, reduce text size |
| `InternalServerError` | Gateway error | Retry with exponential backoff |

### Comprehensive Error Handling

```python
from openai import (
    AuthenticationError,
    APIConnectionError,
    RateLimitError,
    APITimeoutError,
    InternalServerError
)

async def safe_embedding_request(client, text: str):
    """Make an embedding request with comprehensive error handling"""
    
    try:
        response = await client.embeddings.create(
            model="azure-text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
        
    except AuthenticationError:
        print("Authentication failed. Check API key.")
        raise
        
    except APIConnectionError as e:
        print(f"Cannot connect to gateway: {e}")
        raise
        
    except RateLimitError:
        print("Rate limit exceeded. Waiting and retrying...")
        await asyncio.sleep(5)
        # Retry...
        
    except APITimeoutError:
        print("Request timed out. Try with shorter text.")
        raise
        
    except InternalServerError:
        print("Gateway error. Retrying...")
        await asyncio.sleep(2)
        # Retry...
        
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise
```

---

## Monitoring & Metrics

### Performance Metrics

Track response times and throughput:

```python
import time

class MonitoredGatewayClient:
    def __init__(self, base_url: str, api_key: str):
        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key)
        self.request_times = []
        self.total_tokens = 0
    
    async def tracked_embedding(self, text: str):
        """Make embedding request and track performance"""
        start = time.time()
        
        response = await self.client.embeddings.create(
            model="azure-text-embedding-3-small",
            input=text
        )
        
        elapsed = time.time() - start
        self.request_times.append(elapsed)
        
        if hasattr(response, 'usage'):
            self.total_tokens += response.usage.total_tokens
        
        return response.data[0].embedding
    
    def get_metrics(self):
        """Get performance summary"""
        if not self.request_times:
            return {}
        
        times = self.request_times
        return {
            "avg_response_time": sum(times) / len(times),
            "min_response_time": min(times),
            "max_response_time": max(times),
            "total_requests": len(times),
            "total_tokens": self.total_tokens
        }
```

---

## Best Practices

### 1. **Use Context Managers**

Always close the client properly:

```python
async with AsyncOpenAI(base_url=..., api_key=...) as client:
    result = await client.embeddings.create(...)
# Client automatically closed here
```

### 2. **Batch Operations**

Never send huge lists at once; batch them:

```python
# ❌ Bad: Sending 10,000 texts at once
await client.embeddings.create(input=large_text_list)

# ✅ Good: Batch in chunks of 100-500
for i in range(0, len(texts), 500):
    batch = texts[i:i + 500]
    await client.embeddings.create(input=batch)
```

### 3. **Handle Retries Gracefully**

Implement exponential backoff for transient failures:

```python
# ✅ Good error handling with retries
for attempt in range(3):
    try:
        result = await client.embeddings.create(...)
        break
    except APIConnectionError:
        if attempt == 2:
            raise
        await asyncio.sleep(2 ** attempt)
```

### 4. **Cache Results**

Avoid redundant requests:

```python
cache = {}

async def get_cached_embedding(client, text: str):
    if text in cache:
        return cache[text]
    
    embedding = await client.embeddings.create(
        model="...",
        input=text
    )
    
    cache[text] = embedding.data[0].embedding
    return cache[text]
```

### 5. **Use Appropriate Models**

Choose the right model for your use case:

```python
# For semantic search / embeddings
embedding_model = "azure-text-embedding-3-small"

# For text generation / questions
generation_model = "gpt-4"  # or gpt-3.5-turbo

# For chat / conversations
chat_model = "gpt-4"
```

### 6. **Set Appropriate Timeouts**

Use reasonable timeout values:

```python
# Short timeout for embeddings (fast operation)
client = AsyncOpenAI(..., timeout=30)

# Longer timeout for text generation (slower operation)
client = AsyncOpenAI(..., timeout=120)
```

### 7. **Monitor Costs**

Track costs in production:

```python
# Log every request's cost
response = await client.embeddings.create(...)
if response.usage:
    tokens = response.usage.total_tokens
    cost = tokens * COST_PER_TOKEN
    logger.info(f"Request cost: ${cost:.4f}")
```

---

## Complete Examples

### Example 1: Simple Document Embedding

```python
import asyncio
from openai import AsyncOpenAI

async def embed_documents():
    """Embed multiple documents for semantic search"""
    
    client = AsyncOpenAI(
        base_url="https://aips-ai-gateway.dev.ai-platform.int.wexfabric.com/",
        api_key="your-api-key"
    )
    
    documents = [
        "Python is a programming language",
        "Machine learning uses data to train models",
        "Embeddings convert text to vectors"
    ]
    
    try:
        # Batch embeddings
        response = await client.embeddings.create(
            model="azure-text-embedding-3-small",
            input=documents
        )
        
        embeddings = [item.embedding for item in response.data]
        
        for doc, emb in zip(documents, embeddings):
            print(f"{doc}")
            print(f"  -> {len(emb)} dimensions")
            print()
            
    finally:
        await client.close()

asyncio.run(embed_documents())
```

### Example 2: Simple Question Answering

```python
import asyncio
from openai import AsyncOpenAI

async def ask_ai():
    """Ask the AI a question and get a response"""
    
    client = AsyncOpenAI(
        base_url="https://aips-ai-gateway.dev.ai-platform.int.wexfabric.com/",
        api_key="your-api-key"
    )
    
    questions = [
        "What is machine learning?",
        "How do embeddings work?",
        "Explain semantic search in simple terms"
    ]
    
    try:
        for question in questions:
            response = await client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "user", "content": question}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            answer = response.choices[0].message.content
            print(f"Q: {question}")
            print(f"A: {answer}")
            print()
            
    finally:
        await client.close()

asyncio.run(ask_ai())
```

### Example 3: Production-Ready Client

```python
import asyncio
import time
import logging
from openai import AsyncOpenAI, APIConnectionError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WEXGatewayClient:
    """Production-ready WEX AI Gateway client"""
    
    def __init__(self, base_url: str, api_key: str, timeout: int = 120):
        self.client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout
        )
        self.total_requests = 0
        self.total_cost = 0.0
    
    async def embed_batch(self, texts: list, batch_size: int = 100):
        """Embed multiple texts with batching and retry logic"""
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            for attempt in range(3):
                try:
                    response = await self.client.embeddings.create(
                        model="azure-text-embedding-3-small",
                        input=batch
                    )
                    
                    embeddings = [item.embedding for item in response.data]
                    all_embeddings.extend(embeddings)
                    
                    # Track metrics
                    self.total_requests += 1
                    if hasattr(response, 'usage'):
                        self.total_cost += response.usage.total_tokens * 0.0001
                    
                    logger.info(f"Processed batch {len(all_embeddings)}/{len(texts)}")
                    break
                    
                except APIConnectionError as e:
                    if attempt == 2:
                        logger.error(f"Failed after 3 attempts: {e}")
                        raise
                    
                    wait_time = 2 ** attempt
                    logger.warning(f"Connection error. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
        
        return all_embeddings
    
    async def generate_text(self, prompt: str, model: str = "gpt-4"):
        """Generate text with error handling"""
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=500
            )
            
            self.total_requests += 1
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Text generation failed: {e}")
            raise
    
    async def health_check(self):
        """Verify gateway is operational"""
        try:
            response = await self.client.embeddings.create(
                model="azure-text-embedding-3-small",
                input=["test"]
            )
            return "healthy" if response else "unhealthy"
        except Exception as e:
            return f"error: {e}"
    
    def get_stats(self):
        """Get usage statistics"""
        return {
            "total_requests": self.total_requests,
            "total_cost": f"${self.total_cost:.4f}"
        }
    
    async def cleanup(self):
        """Close client"""
        await self.client.close()

# Usage
async def main():
    client = WEXGatewayClient(
        base_url="https://aips-ai-gateway.dev.ai-platform.int.wexfabric.com/",
        api_key="your-api-key"
    )
    
    try:
        # Health check
        health = await client.health_check()
        print(f"Gateway health: {health}")
        
        # Embed documents
        documents = ["Doc 1", "Doc 2", "Doc 3"]
        embeddings = await client.embed_batch(documents)
        print(f"Generated {len(embeddings)} embeddings")
        
        # Generate text
        answer = await client.generate_text("What is AI?")
        print(f"Answer: {answer}")
        
        # Stats
        print(f"Stats: {client.get_stats()}")
        
    finally:
        await client.cleanup()

asyncio.run(main())
```

---

## Troubleshooting

### Gateway Not Reachable

```python
# Check base_url
print(f"Connecting to: {base_url}")

# Test with curl first
# curl https://aips-ai-gateway.dev.ai-platform.int.wexfabric.com/health
```

### API Key Issues

```python
# Verify API key format
if not api_key or len(api_key) == 0:
    raise ValueError("API key is empty")

# Test with a simple request
try:
    await client.embeddings.create(input="test", model="...")
except AuthenticationError:
    print("Invalid API key")
```

### Model Not Found

```python
# Verify model name
correct_models = ["gpt-4", "azure-text-embedding-3-small"]

# Ask gateway what models it supports
# via /v1/models endpoint or documentation
```

---

## Summary

- **WEX AI Gateway** is an OpenAI-compatible proxy to various AI models
- Use `AsyncOpenAI` client pointing to your gateway's base URL
- Implement batching for large-scale operations
- Add retry logic with exponential backoff
- Monitor costs and performance metrics
- Always close clients gracefully
- Use appropriate error handling for production systems

For more information, refer to the [OpenAI Python SDK documentation](https://github.com/openai/openai-python).
