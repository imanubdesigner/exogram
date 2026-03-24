# Architecture — Overview

---

## Component diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                          Internet                               │
└───────────────────────────┬─────────────────────────────────────┘
                            │ 80 / 443
                            ▼
                    ┌───────────────┐
                    │  Caddy 2      │  Automatic TLS (Let's Encrypt)
                    │  Reverse proxy│  Security headers
                    └──────┬────────┘
          ┌────────────────┼────────────────────┐
          │                │                    │
    /api/* /admin*    /static/* /media/*       /*
          │                │                    │
          ▼                ▼                    ▼
  ┌──────────────┐  ┌────────────┐    ┌──────────────────┐
  │   Gunicorn   │  │   Static   │    │  frontend/dist/  │
  │  4w × 2t     │  │   files    │    │  (SPA Vue 3)     │
  │  Django 5.2  │  │   on disk  │    │  index.html SPA  │
  └──────┬───────┘  └────────────┘    └──────────────────┘
         │
    ┌────┴──────────────────────────────────────┐
    │              Django Apps                   │
    │  accounts · books · social · threads       │
    │  affinity · discovery · articles           │
    └────┬──────────────────┬────────────────────┘
         │                  │
         ▼                  ▼
┌─────────────────┐  ┌─────────────┐
│  PostgreSQL 16  │  │  Redis 7    │
│  + pgvector     │  │  256 MB cap │
└─────────────────┘  └──────┬──────┘
                            │ broker
                    ┌───────┴──────────────┐
                    │     Celery           │
                    │  worker (concurrency=1)
                    │  beat (DatabaseScheduler)
                    └──────────────────────┘
                            │ embeddings
                    ┌───────┴──────────┐
                    │  ONNX Runtime    │
                    │  MiniLM-L12-v2   │
                    │  (~470 MB, local)│
                    └──────────────────┘

              ┌────────────────────────┐
              │  Postal 3 (profile:mail)│
              │  SMTP self-hosted       │
              │  MariaDB + Redis        │
              └────────────────────────┘
```

---

## Typical request flow

**Example: user searches highlights by semantic similarity**

```
Browser
  │ POST /api/discovery/search/ {query: "identidad y memoria"}
  │ Cookie: exo_access=<JWT>; csrftoken=<token>
  │ Header: X-CSRFToken: <token>
  ▼
Caddy
  │ Verifies that the host is correct
  │ Adds security headers (CSP, HSTS, etc.)
  │ Proxies to backend:8000
  ▼
Gunicorn
  │ Passes the request to Django
  ▼
Django middleware stack
  │ SecurityMiddleware → CorsMiddleware → CsrfViewMiddleware
  │ → SessionMiddleware → AuthenticationMiddleware → CSPMiddleware
  ▼
CookieJWTAuthentication
  │ Reads exo_access cookie, validates JWT, authenticates the user
  ▼
SimilaritySearchView
  │ Validates input
  │ Calls encode_text(query) → ONNX Runtime → 384-dim vector
  │ Executes cosine similarity query in pgvector
  │   SELECT ... ORDER BY embedding <=> $query_vector LIMIT 10
  ▼
Response JSON
  │ List of similar highlights with similarity score
  ▼
Browser
```

---

## Highlight import flow

```
Browser
  │ POST /api/books/import/ (.txt Kindle file)
  ▼
KindleParser
  │ Parses the text, extracts books and highlights
  ▼
Django ORM
  │ Creates Book (if not exists), Author, Highlight (without embedding)
  ▼
Celery task dispatch
  │ batch_generate_embeddings.delay([id1, id2, ...])
  │ (async: does not block the response to the user)
  ▼
HTTP 200 → Browser ("X highlights imported, processing embeddings...")

[Background, Celery worker]
  │ Reads highlights without embedding
  │ encode_batch(contents) → ONNX Runtime
  │ Saves embeddings in PostgreSQL
  │ update_user_cluster(profile) → recalculates centroid
```

---

## Design principles

**Single datastore.** PostgreSQL stores relational data, vectors (pgvector), and
the Celery schedule (django-celery-beat). There is no synchronization between systems.

**Privacy by default.** New highlights are `private`. Embeddings are
generated locally (ONNX), without sending data to external APIs.

**Graceful failure.** If the ONNX model is unavailable, highlights are saved
without an embedding. If the email cannot be sent, the invitation token is deleted
and a clear error is returned. If DB or Redis go down, the health check returns 503.

**Layered security.** TLS in Caddy, JWT in HttpOnly cookies, CSRF double-submit,
rate limiting on sensitive endpoints, non-root in Docker, security headers in both
Caddy and Django middleware.
