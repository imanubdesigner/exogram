# Arquitectura — Visión general

---

## Diagrama de componentes

```
┌─────────────────────────────────────────────────────────────────┐
│                          Internet                               │
└───────────────────────────┬─────────────────────────────────────┘
                            │ 80 / 443
                            ▼
                    ┌───────────────┐
                    │  Caddy 2      │  TLS automático (Let's Encrypt)
                    │  Reverse proxy│  Security headers
                    └──────┬────────┘
          ┌────────────────┼────────────────────┐
          │                │                    │
    /api/* /admin*    /static/* /media/*       /*
          │                │                    │
          ▼                ▼                    ▼
  ┌──────────────┐  ┌────────────┐    ┌──────────────────┐
  │   Gunicorn   │  │  Archivos  │    │  frontend/dist/  │
  │  4w × 2t     │  │  estáticos │    │  (SPA Vue 3)     │
  │  Django 5.2  │  │  en disco  │    │  index.html SPA  │
  └──────┬───────┘  └────────────┘    └──────────────────┘
         │
    ┌────┴──────────────────────────────────────┐
    │              Apps Django                   │
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

## Flujo de un request típico

**Ejemplo: usuario busca highlights por similitud semántica**

```
Browser
  │ POST /api/discovery/search/ {query: "identidad y memoria"}
  │ Cookie: exo_access=<JWT>; csrftoken=<token>
  │ Header: X-CSRFToken: <token>
  ▼
Caddy
  │ Verifica que el host es el correcto
  │ Agrega security headers (CSP, HSTS, etc.)
  │ Proxea a backend:8000
  ▼
Gunicorn
  │ Pasa el request a Django
  ▼
Django middleware stack
  │ SecurityMiddleware → CorsMiddleware → CsrfViewMiddleware
  │ → SessionMiddleware → AuthenticationMiddleware → CSPMiddleware
  ▼
CookieJWTAuthentication
  │ Lee exo_access cookie, valida JWT, autentica al usuario
  ▼
SimilaritySearchView
  │ Valida el input
  │ Llama a encode_text(query) → ONNX Runtime → vector de 384 dims
  │ Ejecuta query de similitud coseno en pgvector
  │   SELECT ... ORDER BY embedding <=> $query_vector LIMIT 10
  ▼
Response JSON
  │ Lista de highlights similares con score de similitud
  ▼
Browser
```

---

## Flujo de importación de highlights

```
Browser
  │ POST /api/books/import/ (archivo .txt Kindle)
  ▼
KindleParser
  │ Parsea el texto, extrae libros y highlights
  ▼
Django ORM
  │ Crea Book (si no existe), Author, Highlight (sin embedding)
  ▼
Celery task dispatch
  │ batch_generate_embeddings.delay([id1, id2, ...])
  │ (async: no bloquea el response al usuario)
  ▼
HTTP 200 → Browser ("X highlights importados, procesando embeddings...")

[Background, Celery worker]
  │ Lee highlights sin embedding
  │ encode_batch(contents) → ONNX Runtime
  │ Guarda embeddings en PostgreSQL
  │ update_user_cluster(profile) → recalcula centroide
```

---

## Principios de diseño

**Un solo datastore.** PostgreSQL almacena datos relacionales, vectores (pgvector) y
el schedule de Celery (django-celery-beat). No hay sincronización entre sistemas.

**Privacidad por defecto.** Los highlights nuevos son `private`. Los embeddings se
generan localmente (ONNX), sin enviar datos a APIs externas.

**Fallo graceful.** Si el modelo ONNX no está disponible, los highlights se guardan
sin embedding. Si el email no puede enviarse, el token de invitación se elimina
y se devuelve un error claro. Si DB o Redis caen, el health check devuelve 503.

**Seguridad en capas.** TLS en Caddy, JWT en cookies HttpOnly, CSRF double-submit,
rate limiting en endpoints sensibles, non-root en Docker, security headers tanto
en Caddy como en Django middleware.
