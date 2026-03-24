# 0003 — Local ONNX Runtime for embeddings instead of an external API

## Context

To generate vector embeddings for highlights, a language model is needed to
convert text into numerical vectors. The options are: calling an external API
(OpenAI, Cohere, etc.) or running a model locally.

## Decision

Use **ONNX Runtime** with the `paraphrase-multilingual-MiniLM-L12-v2` model downloaded
locally. The model runs in the Celery worker without an internet connection.

Characteristics of the chosen model:
- 384 dimensions
- Multilingual (50+ languages, critical for highlights in Spanish)
- ~470 MB in ONNX format
- ~50ms latency per text on CPU

## Alternatives considered

**OpenAI text-embedding-ada-002 / text-embedding-3-small:** high quality, zero infrastructure,
but cost per token that scales with usage, dependency on an external service, and user data
(their highlights, personal notes) would leave the system. Discarded for privacy and cost reasons.

**sentence-transformers (PyTorch):** same model but loaded with the Hugging Face library.
Requires PyTorch (~1.5 GB of dependencies). ONNX Runtime is the runtime without PyTorch:
the model is pre-converted to ONNX format. PyTorch discarded due to image size.

**Synchronous calls in the request:** generating the embedding at upload time
would block the request ~50ms per text. Discarded: embeddings are generated
asynchronously in Celery.

## Consequences

- User highlights never leave the system for processing. Full privacy.
- Embedding cost: zero per query.
- The Celery worker requires ~1 GB of extra RAM to load the model (configured with `mem_limit: 3g` in docker-compose).
- The model (~470 MB) is persisted in the `models_cache` volume to avoid downloading it on every restart.
- The `download_onnx_model` management command allows preloading it manually.
- If the model is unavailable (empty volume, first start), `EmbeddingModelUnavailable` is handled gracefully: the task returns a warning instead of failing. Highlights remain without an embedding until the model is available.
- Tokenization uses the Hugging Face `tokenizers` library (Rust, lightweight) without requiring PyTorch.
