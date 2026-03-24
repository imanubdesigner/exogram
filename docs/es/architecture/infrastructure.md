# Infraestructura

---

## Servicios Docker

El stack completo se define en `docker-compose.yml` (base) y `docker-compose.prod.yml` (override de producción).

| Servicio | Imagen | Rol |
|---|---|---|
| `db` | `pgvector/pgvector:pg16` | PostgreSQL 16 con extensión vector |
| `redis` | `redis:7-alpine` | Broker de Celery y cache |
| `backend` | build `./backend` | Django + Gunicorn |
| `celery` | build `./backend` | Worker de tareas async |
| `celery-beat` | build `./backend` | Scheduler de tareas periódicas |
| `flower` | `mher/flower` | UI de monitoreo de Celery |
| `caddy` | `caddy:2-alpine` | Reverse proxy + TLS (solo producción) |
| `postal` | `ghcr.io/postalserver/postal:3` | SMTP self-hosted (profile `mail`) |
| `postal-mariadb` | `mariadb:10.11` | Base de datos de Postal (profile `mail`) |
| `frontend` | build `./frontend` | Vite dev server (solo desarrollo) |

---

## Diferencias dev vs producción

| Aspecto | Desarrollo | Producción |
|---|---|---|
| Backend command | `runserver` con hot-reload | `./start-web.sh` → Gunicorn |
| Frontend | Vite dev server (puerto 5173) | Build estático servido por Caddy |
| Código fuente | Bind-mount `./backend:/app` | Imagen construida (sin mount) |
| Puertos DB/Redis | Expuestos en todas las interfaces | Solo `127.0.0.1` |
| TLS | No | Caddy + Let's Encrypt |
| `FORCE_HTTPS` | False | True |
| Caddy | No | Sí |
| Modelo ONNX | Bind-mount `./models_cache` | Volumen `models_cache` |

---

## Volúmenes

| Volumen | Contenido | Persistencia |
|---|---|---|
| `postgres_data` | Datos de PostgreSQL | Crítica — backup necesario |
| `static_data` | Archivos estáticos de Django | Regenerable con `collectstatic` |
| `media_data` | Avatares y uploads de usuarios | Importante — contiene archivos de usuarios |
| `models_cache` | Modelo ONNX (~470 MB) | Regenerable (se descarga de HuggingFace) |
| `caddy_data` | Certificados TLS | Importante — pérdida causa breve downtime en renovación |
| `caddy_config` | Configuración runtime de Caddy | Regenerable |
| `postal-config` | Config y signing key de Postal | Importante — contiene la clave de firma DKIM |
| `postal_db_data` | Datos de MariaDB de Postal | Importante para historial de emails |

---

## Caddy: routing y TLS

El `Caddyfile` define el routing completo en producción:

```
{$APP_DOMAIN}
    /static/*   → archivos estáticos Django (collectstatic)
    /media/*    → archivos subidos por usuarios (avatares)
    /api/*      → backend:8000 (Gunicorn)
    /admin*     → backend:8000
    /*          → /srv/frontend/dist/index.html (SPA fallback)

postal.{$APP_DOMAIN}
    → postal:5000 (UI web de Postal)

www.{$APP_DOMAIN}
    → redirect 301 a {$APP_DOMAIN}
```

Los certificados TLS se obtienen de Let's Encrypt vía ACME HTTP-01 automáticamente.
Se renuevan sin intervención manual. Los datos se persisten en el volumen `caddy_data`.

---

## Gunicorn en producción

`start-web.sh` configura Gunicorn con defaults ajustables por entorno:

| Variable | Default | Descripción |
|---|---|---|
| `GUNICORN_WORKERS` | `4` | Procesos worker. Ajustar a `(2 × CPU) + 1` en instancias grandes. |
| `GUNICORN_THREADS` | `2` | Threads por worker (worker class `gthread`). |
| `GUNICORN_TIMEOUT` | `20` | Timeout en segundos por request. |

Con 4 workers × 2 threads = 8 requests concurrentes. Para una instancia de 2 vCPU y 2-4 GB RAM,
esto es apropiado. Las tareas pesadas (embeddings) van a Celery, no al worker de Django.

---

## Celery: worker y beat

**Worker** (`concurrency=1`): un proceso, pool `prefork`. El modelo ONNX ocupa ~1 GB de RAM
al cargarse, por lo que una sola instancia es suficiente para el lanzamiento inicial.
Si la cola de embeddings crece, aumentar `CELERY_WORKER_CONCURRENCY`.

**Beat**: exactamente una instancia. El DatabaseScheduler persiste el estado en PostgreSQL.
El heartbeat (tarea `beat_heartbeat` cada 60s) escribe en Redis, permitiendo que el
healthcheck del contenedor valide que ambos procesos están vivos.

**Flower** (`:5555`): UI de monitoreo de Celery. Solo accesible en `127.0.0.1` en producción.
Para acceder: abrir un tunel SSH `ssh -L 5555:127.0.0.1:5555 usuario@servidor`.

---

## Postal: SMTP self-hosted

Postal corre como profile `mail`: no levanta por defecto.

En producción, levantarlo con:
```bash
docker compose --profile mail -f docker-compose.yml -f docker-compose.prod.yml up -d
```

Postal requiere configuración de DNS antes de enviar emails con buena deliverability:
- **SPF**: registro TXT en el dominio del remitente.
- **DKIM**: clave pública publicada en DNS, clave privada en el volumen `postal-config/signing.key`.
- **PTR/rDNS**: registro inverso de la IP del servidor apuntando al dominio de envío.
- **Puerto 25**: algunos proveedores de cloud lo bloquean por default. Verificar con el proveedor.
