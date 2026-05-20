# WEX AI Gateway Model Catalog

This model catalog is intended as a starting point for working with the WEX AI Gateway. The actual available models depend on the gateway configuration and can be queried dynamically using the gateway's `GET /v1/models` endpoint or the public model hub.

---

## Discovering Available Models

Use the gateway's model discovery endpoints to get the current inventory:

- `GET https://aips-ai-gateway.dev.ai-platform.int.wexfabric.com/v1/models`
- `GET https://aips-ai-gateway.dev.ai-platform.int.wexfabric.com/public/model_hub`

If you need to refresh available models, run one of those requests and inspect the returned model names and metadata.

---

## Recommended Model Families

### Regular Analysis / Text Generation

These models are the best fit for typical analysis, summarization, QA, and conversational workflows.

| Model | Category | Best For | Cost/Performance | Notes |
|-------|----------|----------|------------------|-------|
| `gpt-3.5-turbo` | OpenAI-compatible | General analysis, chat, summarization | Low cost, good speed | Default best fit for budget-sensitive workloads |
| `gpt-3.5-turbo-16k` | OpenAI-compatible | Longer context analysis | Low cost, larger context window | Good for larger documents |
| `gpt-4o` | OpenAI-compatible | Higher-quality analysis | Mid cost, strong speed | Better reasoning than 3.5 |
| `gpt-4` | OpenAI-compatible | High-accuracy analysis, important reports | Higher cost, best quality | Use when quality is more important than cost |
| `gemini-pro` | Google Gemini-compatible | Premium conversation and analysis | Higher cost, top-tier quality | Best when gateway exposes Google Gemini models |
| `sonnet-4.6` | Sonnet family | High-quality analysis and reasoning | Mid-to-high cost, strong capability | Good alternative to GPT-4-level models |
| `claude-3.5` | Anthropic-compatible | General analysis with Claude flavor | Mid cost, quality similar to 3.5/4 | Use if your gateway routes to Anthropic |
| `claude-3.5-sonic` | Anthropic-compatible | Fast, lower-cost analysis | Lower cost, faster response | Best for high-volume lightweight tasks |
| `mistral-large` | Mistral-compatible | Creative analysis, code reasoning | Mid cost, strong quality | Good alternative for OpenAI-style workloads |

> Recommendation for regular analysis: start with `gpt-3.5-turbo` as the best cost-performance balance. If you need more reliable or higher-quality outputs, move to `gpt-4` or a comparable high-end provider.

### Embedding Models

These models are typically used for semantic search, similarity, and retrieval workflows.

| Model | Category | Best For | Cost/Performance | Notes |
|-------|----------|----------|------------------|-------|
| `text-embedding-3-small` | OpenAI-compatible | Default embeddings | Low cost, good quality | Best starting point for most use cases |
| `text-embedding-3-large` | OpenAI-compatible | High-precision semantic search | Higher cost, better quality | Use for critical similarity tasks |
| `all-MiniLM-L6-v2` | Sentence Transformers-style | Local/fast embeddings | Very low cost, decent quality | Often used when gateway supports local models |
| `text-embedding-3-small` | OpenAI-compatible | Basic search and clustering | Low cost, fast | Good general-purpose fallback |

> Embedding recommendation: use `text-embedding-3-small` for regular semantic analysis, and `text-embedding-3-large` only when you need higher quality and are willing to pay more.

---

## Cost Tier Guidance

The `cost_tier` setting is primarily a budget/label property used by your integration layer. It does not directly change gateway behavior, but it helps classify models by expected cost:

- `free` — Budget-friendly or low-cost models (e.g. `gpt-3.5-turbo`, `text-embedding-3-small`)
- `standard` — Mid-tier models with solid quality (e.g. `gpt-4o`, `claude-3.5`, `text-embedding-3-large`)
- `premium` — High-end models with the best output quality (e.g. `gpt-4`, `gemini-pro`, `sonnet-4.6`, Claude 4, enterprise fine-tuned models)

Use `cost_tier` to select a default profile for your application, then tune the actual model by querying the gateway for available names.

---

## Example: Choosing a Model for Regular Analysis

If your workflow is regular analysis, summarization, or conversational insights, this is a good pattern:

- Start with `gpt-3.5-turbo` for cost-efficient analysis
- If the results are too generic or inaccurate, switch to `gpt-4` or `gpt-4o`
- If you need a cheaper fast path, consider `claude-3.5-sonic`

## Example: Choosing an Embedding Model

- Default: `text-embedding-3-small`
- Better quality: `text-embedding-3-large`
- Lowest-cost / local fallback: `all-MiniLM-L6-v2` or equivalent local embedding provider if available

---

## Model Metadata to Inspect

When you query `GET /v1/models`, you should look for:

- Model name
- Model type (`text`, `embeddings`, `chat`, etc.)
- Maximum context length
- Cost metadata (if provided)
- Status / availability

Use those details to map gateway models to your `cost_tier` strategy.

---

## Practical Model Selection Strategy

1. Query `/v1/models` and `/public/model_hub` to discover the gateway models.
2. Match each model to one of these profiles:
   - Budget / light use
   - Standard analysis
   - Premium quality
3. Set `cost_tier` in your integration settings based on the profile.
4. For embeddings, prefer `text-embedding-3-small` first and `text-embedding-3-large` only when needed.

---

## Notes

- Gateway availability may change: always refresh model inventory before locking in a model name.
- If your gateway uses a custom naming scheme or proxy route, use `GET /v1/models` to verify exact names.
- This catalog is intended as a general guide; treat gateway model metadata as the source of truth for your environment.
