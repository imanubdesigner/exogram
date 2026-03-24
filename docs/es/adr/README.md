# Architecture Decision Records

Los ADRs documentan las decisiones de diseño y arquitectura significativas tomadas en el proyecto:
qué se decidió, por qué, y qué se descartó.

El objetivo es que cualquier persona que se incorpore al proyecto —o el propio equipo
seis meses después— pueda entender el razonamiento detrás de la estructura actual
sin tener que reconstruirlo desde el código.

---

## Índice

| # | Título | Estado |
|---|---|---|
| [0001](./0001-jwt-httponly-cookies.md) | JWT en HttpOnly cookies en lugar de localStorage | Aceptado |
| [0002](./0002-pgvector-embeddings.md) | pgvector como vector store en lugar de servicio dedicado | Aceptado |
| [0003](./0003-onnx-runtime-local.md) | ONNX Runtime local para embeddings en lugar de API externa | Aceptado |
| [0004](./0004-invitation-only-signup.md) | Registro solo por invitación | Aceptado |
| [0005](./0005-celery-beat-postgresql.md) | django-celery-beat con DatabaseScheduler | Aceptado |
| [0006](./0006-caddy-reverse-proxy.md) | Caddy como reverse proxy y servidor TLS | Aceptado |
| [0007](./0007-postal-self-hosted-smtp.md) | Postal como servidor SMTP self-hosted | Aceptado |
| [0008](./0008-django-5-lts.md) | Django 5.2 LTS | Aceptado |

---

## Formato

Cada ADR sigue esta estructura:

```markdown
# NNNN — Título

**Fecha:** YYYY-MM-DD
**Estado:** Propuesto | Aceptado | Deprecado | Reemplazado por [NNNN]

## Contexto
Qué problema o necesidad motivó esta decisión.

## Decisión
Qué se decidió hacer.

## Alternativas consideradas
Qué otras opciones se evaluaron y por qué se descartaron.

## Consecuencias
Qué implica esta decisión: ventajas, compromisos, limitaciones conocidas.
```
