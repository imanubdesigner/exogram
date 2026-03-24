# Infrastructure

---

## Docker services

The full stack is defined in `docker-compose.yml` (base) and `docker-compose.prod.yml` (production override).

| Service | Image | Role |
|---|---|---|
| `db` | `pgvector/pgvector:pg16` | PostgreSQL 16 with vector extension |
| `redis` | `redis:7-alpine` | Celery broker and cache |
| `backend` | build `./backend` | Django + Gunicorn |
| `celery` | build `./backend` | Async task worker |
| `celery-beat` | build `./backend` | Periodic task scheduler |
| `flower` | `mher/flower` | Celery monitoring UI |
| `caddy` | `caddy:2-alpine` | Reverse proxy + TLS (production only) |
| `postal` | `ghcr.io/postalserver/postal:3` | Self-hosted SMTP (profile `mail`) |
| `postal-mariadb` | `mariadb:10.11` | Postal database (profile `mail`) |
| `frontend` | build `./frontend` | Vite dev server (development only) |

---

## Dev vs production differences

| Aspect | Development | Production |
|---|---|---|
| Backend command | `runserver` with hot-reload | `./start-web.sh` → Gunicorn |
| Frontend | Vite dev server (port 5173) | Static build served by Caddy |
| Source code | Bind-mount `./backend:/app` | Built image (no mount) |
| DB/Redis ports | Exposed on all interfaces | `127.0.0.1` only |
| TLS | No | Caddy + Let's Encrypt |
| `FORCE_HTTPS` | False | True |
| Caddy | No | Yes |
| ONNX model | Bind-mount `./models_cache` | Volume `models_cache` |

---

## Volumes

| Volume | Contents | Persistence |
|---|---|---|
| `postgres_data` | PostgreSQL data | Critical — backup required |
| `static_data` | Django static files | Regenerable with `collectstatic` |
| `media_data` | Avatars and user uploads | Important — contains user files |
| `models_cache` | ONNX model (~470 MB) | Regenerable (downloaded from HuggingFace) |
| `caddy_data` | TLS certificates | Important — loss causes brief downtime on renewal |
| `caddy_config` | Caddy runtime configuration | Regenerable |
| `postal-config` | Postal config and signing key | Important — contains the DKIM signing key |
| `postal_db_data` | Postal MariaDB data | Important for email history |

---

## Caddy: routing and TLS

The `Caddyfile` defines the full routing in production:

```
{$APP_DOMAIN}
    /static/*   → Django static files (collectstatic)
    /media/*    → user-uploaded files (avatars)
    /api/*      → backend:8000 (Gunicorn)
    /admin*     → backend:8000
    /*          → /srv/frontend/dist/index.html (SPA fallback)

postal.{$APP_DOMAIN}
    → postal:5000 (Postal web UI)

www.{$APP_DOMAIN}
    → 301 redirect to {$APP_DOMAIN}
```

TLS certificates are obtained from Let's Encrypt via ACME HTTP-01 automatically.
They are renewed without manual intervention. The data is persisted in the `caddy_data` volume.

---

## Gunicorn in production

`start-web.sh` configures Gunicorn with environment-adjustable defaults:

| Variable | Default | Description |
|---|---|---|
| `GUNICORN_WORKERS` | `4` | Worker processes. Adjust to `(2 × CPU) + 1` on larger instances. |
| `GUNICORN_THREADS` | `2` | Threads per worker (worker class `gthread`). |
| `GUNICORN_TIMEOUT` | `20` | Timeout in seconds per request. |

With 4 workers × 2 threads = 8 concurrent requests. For a 2 vCPU, 2-4 GB RAM instance,
this is appropriate. Heavy tasks (embeddings) go to Celery, not to the Django worker.

---

## Celery: worker and beat

**Worker** (`concurrency=1`): one process, `prefork` pool. The ONNX model uses ~1 GB of RAM
when loaded, so a single instance is sufficient for the initial launch.
If the embeddings queue grows, increase `CELERY_WORKER_CONCURRENCY`.

**Beat**: exactly one instance. The DatabaseScheduler persists state in PostgreSQL.
The heartbeat (task `beat_heartbeat` every 60s) writes to Redis, allowing the
container healthcheck to validate that both processes are alive.

**Flower** (`:5555`): Celery monitoring UI. Only accessible at `127.0.0.1` in production.
To access: open an SSH tunnel `ssh -L 5555:127.0.0.1:5555 user@server`.

---

## Postal: self-hosted SMTP

Postal runs as profile `mail`: it does not start by default.

In production, start it with:
```bash
docker compose --profile mail -f docker-compose.yml -f docker-compose.prod.yml up -d
```

Postal requires DNS configuration before sending emails with good deliverability:
- **SPF**: TXT record on the sender's domain.
- **DKIM**: public key published in DNS, private key in the `postal-config/signing.key` volume.
- **PTR/rDNS**: reverse record of the server IP pointing to the sending domain.
- **Port 25**: some cloud providers block it by default. Check with your provider.
