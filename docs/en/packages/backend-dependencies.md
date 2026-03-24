# Backend dependencies

Reference for all packages in `backend/requirements.txt`.

---

| Package | Version | Purpose | Why this and not another |
|---|---|---|---|
| `Django` | 5.2.12 | Main web framework | LTS until 2028. See [ADR 0008](../adr/0008-django-5-lts.md). |
| `djangorestframework` | 3.15.2 | REST API on top of Django | De facto standard for Django APIs. Native integration with authentication, permissions, throttling, and pagination. |
| `djangorestframework-simplejwt` | 5.5.1 | JWT: generation, validation, blacklist | Fixes CVE-2024-22513. Token blacklist included as an installable app. |
| `django-cors-headers` | 4.6.0 | CORS headers | The only dependency for CORS in Django, well maintained. |
| `django-celery-beat` | 2.9.0 | Task schedule in PostgreSQL | Persists schedule across restarts. See [ADR 0005](../adr/0005-celery-beat-postgresql.md). |
| `celery` | 5.4.0 | Asynchronous task queue | Standard for background tasks in Django. Retry, backoff, beat included. |
| `redis` | 5.2.1 | Python Redis client | Used as Celery broker and for the beat heartbeat. |
| `psycopg2` | 2.9.10 | Compiled PostgreSQL driver | The compiled version (not `psycopg2-binary`) is recommended for production for stability. Requires `libpq-dev` on the system. |
| `pgvector` | 0.3.6 | Django integration for pgvector | Provides `VectorField`, `HnswIndex`, and distance operators for the Django ORM. |
| `python-decouple` | 3.8 | Environment variable reading | Reads from `.env` and system environment variables. More explicit than `os.environ.get` throughout the codebase. |
| `Pillow` | 12.1.1 | Image processing | Used for validation and re-encoding of avatars. Version 12.x fixes malicious image parsing vulnerabilities. |
| `requests` | 2.32.4 | HTTP client | Used for calls to the OpenLibrary API. 2.32.x fixes CVE-2024-35195 and CVE-2024-47081. |
| `feedparser` | 6.0.11 | RSS/Atom parser | Used for Goodreads feed synchronization. Tolerant of malformed feeds. |
| `beautifulsoup4` | 4.12.3 | HTML parser | Used in the Goodreads scraper to parse external HTML tables. |
| `onnxruntime` | 1.20.1 | ONNX model runtime | Runs the embeddings model without PyTorch. ~50ms per text on CPU. See [ADR 0003](../adr/0003-onnx-runtime-local.md). |
| `numpy` | 1.26.4 | Vector operations | Required by onnxruntime. Pinned to 1.26.x for compatibility with the numpy arrays API. |
| `scikit-learn` | 1.5.2 | ML for clustering and moderation | Used in the comment moderation engine and for affinity clustering. |
| `tokenizers` | 0.21.0 | ONNX tokenization | Hugging Face Rust library for tokenizing text before passing it to the ONNX model. Lightweight: does not require PyTorch. |
| `python-dateutil` | 2.9.0 | Robust date parsing | Used in import parsers where dates come in variable formats. |
| `sentry-sdk` | 2.19.2 | Observability and error tracking | Integration with Django and Celery. Only active if `SENTRY_DSN` is configured. |
| `gunicorn` | 23.0.0 | Production WSGI server | Worker class `gthread` (multithreaded). 4 workers × 2 threads = 8 concurrent requests by default. |
| `coverage` | 7.6.10 | Test coverage measurement | Used in CI to verify that coverage does not drop below 60%. |

---

## Version management

Versions are pinned in `requirements.txt`. To update them:

```bash
# Install pip-tools if not available
pip install pip-tools

# Compile requirements.in to requirements.txt with updated versions
pip-compile requirements.in

# Check for new CVEs
pip-audit -r requirements.txt
```

If `requirements.in` does not exist, versions are updated by editing `requirements.txt` manually and running `pip-audit` to verify.
