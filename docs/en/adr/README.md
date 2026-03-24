# Architecture Decision Records

ADRs document the significant design and architecture decisions made in the project:
what was decided, why, and what was discarded.

The goal is that anyone joining the project — or the team itself
six months later — can understand the reasoning behind the current structure
without having to reconstruct it from the code.

---

## Index

| # | Title | Status |
|---|---|---|
| [0001](./0001-jwt-httponly-cookies.md) | JWT in HttpOnly cookies instead of localStorage | Accepted |
| [0002](./0002-pgvector-embeddings.md) | pgvector as vector store instead of a dedicated service | Accepted |
| [0003](./0003-onnx-runtime-local.md) | Local ONNX Runtime for embeddings instead of an external API | Accepted |
| [0004](./0004-invitation-only-signup.md) | Invitation-only registration | Accepted |
| [0005](./0005-celery-beat-postgresql.md) | django-celery-beat with DatabaseScheduler | Accepted |
| [0006](./0006-caddy-reverse-proxy.md) | Caddy as reverse proxy and TLS server | Accepted |
| [0007](./0007-postal-self-hosted-smtp.md) | Postal as a self-hosted SMTP server | Accepted |
| [0008](./0008-django-5-lts.md) | Django 5.2 LTS | Accepted |

---

## Format

Each ADR follows this structure:

```markdown
# NNNN — Title

**Date:** YYYY-MM-DD
**Status:** Proposed | Accepted | Deprecated | Replaced by [NNNN]

## Context
What problem or need motivated this decision.

## Decision
What was decided.

## Alternatives considered
What other options were evaluated and why they were discarded.

## Consequences
What this decision entails: advantages, trade-offs, known limitations.
```
