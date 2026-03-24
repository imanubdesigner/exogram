# Exogram — Operational Runbook

Procedures for operating, monitoring, and recovering Exogram in production.

---

## Index

1. [Production stack](#1-production-stack)
2. [Getting started: initial deploy](#2-getting-started-initial-deploy)
3. [Secrets management](#3-secrets-management)
4. [Routine operations](#4-routine-operations)
5. [Backups and restore](#5-backups-and-restore)
6. [Monitoring and alerts](#6-monitoring-and-alerts)
7. [Incident response](#7-incident-response)
8. [Administrative tasks](#8-administrative-tasks)
9. [Secret rotation](#9-secret-rotation)
10. [Compliance / GDPR](#10-compliance--gdpr)

---

## 1. Production stack

| Component       | Image / Version             | Exposed port    |
|-----------------|-----------------------------|-----------------|
| Django + Gunicorn | Python 3.12-slim           | 8000 (internal) |
| Celery worker   | same Dockerfile             | —               |
| Celery beat     | same Dockerfile             | —               |
| PostgreSQL 16   | pgvector/pgvector:pg16      | 5432 (internal) |
| Redis 7         | redis:7-alpine              | 6379 (internal) |
| Caddy           | caddy:2-alpine              | 80, 443         |
| Flower          | mher/flower                 | 5555 (localhost)|

```
Internet → Caddy (TLS) → Django API (:8000)
                       → /static/, /media/ (served directly by Caddy)
Celery beat → Redis → Celery worker → PostgreSQL
```

---

## 2. Getting started: initial deploy

### 2.1 Clone and configure environment

```bash
git clone git@github.com:<org>/exogram.git
cd exogram

# Copy the environment variables template
cp backend/.env.example backend/.env

# Edit with the real production values (see section 3)
$EDITOR backend/.env
```

### 2.2 Required variables in `backend/.env`

| Variable              | Description                                              | How to generate                           |
|-----------------------|----------------------------------------------------------|-------------------------------------------|
| `SECRET_KEY`          | Django secret key. Minimum 50 chars, random.             | `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `DATABASE_URL`        | PostgreSQL connection string.                            | `postgres://user:pass@host:5432/dbname`   |
| `REDIS_URL`           | Redis URL.                                               | `redis://redis:6379/0`                    |
| `SENTRY_DSN`          | Sentry DSN for error tracking.                           | Sentry Dashboard → Settings → Client Keys |
| `FRONTEND_BASE_URL`   | Public frontend URL (for links in emails).               | `https://exogram.app`             |
| `FORCE_HTTPS`         | Enable HSTS and Secure cookies.                          | `True`                                    |
| `ALLOWED_HOSTS`       | Allowed domains separated by commas.                     | `exogram.app,www.exogram.app` |
| `CORS_ALLOWED_ORIGINS`| Allowed CORS origins.                                    | `https://exogram.app`             |
| `CSRF_TRUSTED_ORIGINS`| Same for CSRF.                                           | `https://exogram.app`             |
| `DEFAULT_FROM_EMAIL`  | Sender for transactional emails.                         | `Exogram <no-reply@exogram.app>`  |
| `EMAIL_HOST`          | SMTP server.                                             | Postal, SendGrid, SES, etc.               |
| `EMAIL_PORT`          | SMTP port (587 for STARTTLS).                            | `587`                                     |
| `EMAIL_HOST_USER`     | SMTP user.                                               | —                                         |
| `EMAIL_HOST_PASSWORD` | SMTP password.                                           | —                                         |

### 2.3 First startup

```bash
# Start all services
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Verify all containers are healthy
docker compose ps

# Create the initial superuser (genesis user)
docker compose exec backend python manage.py createsuperuser

# Verify health endpoint
curl https://exogram.app/api/health/
# Expected response: {"status": "ok", "db": "ok", "redis": "ok"}
```

### 2.4 Frontend build

```bash
cd frontend
npm ci
npm run build
# The frontend/dist directory is served by Caddy in production
```

---

## 3. Secrets management

### 3.1 Philosophy

- Secrets only in `backend/.env` (excluded from git by `.gitignore`).
- Never in source code, host shell environment variables, or logs.
- Access to the `.env` file restricted to the user running Docker.

### 3.2 Generate a new SECRET_KEY

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

### 3.3 Database credentials

```bash
# Generate a strong password
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Update in .env:
# DATABASE_URL=postgres://exogram:<new_pass>@db:5432/exogram

# Change in PostgreSQL:
docker compose exec db psql -U postgres -c "ALTER USER exogram PASSWORD '<new_pass>';"
```

### 3.4 View current secrets (emergency only)

```bash
# Only the authorized operator with SSH access to the server
cat backend/.env
```

---

## 4. Routine operations

### 4.1 Deploy a new version

```bash
git pull origin main

# Rebuild and restart
docker compose -f docker-compose.yml -f docker-compose.prod.yml build backend
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --no-deps backend celery celery-beat

# Check logs
docker compose logs -f backend --tail=50
```

### 4.2 Apply migrations

```bash
docker compose exec backend python manage.py migrate --noinput

# Verify status
docker compose exec backend python manage.py showmigrations
```

### 4.3 Restart a service

```bash
docker compose restart backend      # API
docker compose restart celery       # Embeddings worker
docker compose restart celery-beat  # Scheduler
docker compose restart redis        # Cache/broker
```

### 4.4 View logs in real time

```bash
docker compose logs -f backend         # Django + Gunicorn
docker compose logs -f celery          # Celery tasks
docker compose logs -f celery-beat     # Scheduling
docker compose logs -f caddy           # Proxy / TLS
```

### 4.5 Access the Django shell

```bash
docker compose exec backend python manage.py shell
```

---

## 5. Backups and restore

### 5.1 PostgreSQL backup

```bash
# Full backup
docker compose exec db pg_dump -U exogram exogram | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz

# Schema-only backup (no data)
docker compose exec db pg_dump -U exogram --schema-only exogram > schema.sql
```

**Recommended frequency:** daily automatic backup via cron or cloud service (RDS automated backups, etc.).

```bash
# Example cron on the host (daily at 03:00)
0 3 * * * docker compose -f /opt/exogram/docker-compose.yml exec -T db pg_dump -U exogram exogram | gzip > /backups/exogram_$(date +\%Y\%m\%d).sql.gz
```

### 5.2 PostgreSQL restore

```bash
# Stop the app (avoid writes during restore)
docker compose stop backend celery celery-beat

# Restore
gunzip -c backup_20260315_030000.sql.gz | docker compose exec -T db psql -U exogram exogram

# Restart
docker compose start backend celery celery-beat
```

### 5.3 Media backup (avatars)

```bash
# Avatars are stored in the Docker volume `media_data`
docker run --rm -v exogram_media_data:/media -v $(pwd)/backups:/backup \
  alpine tar czf /backup/media_$(date +%Y%m%d).tar.gz /media
```

### 5.4 ONNX model backup (models_cache)

The model is automatically downloaded from HuggingFace on first startup. No backup is required, but ensure that the `models_cache` volume persists between restarts (already configured in `docker-compose.prod.yml`).

---

## 6. Monitoring and alerts

### 6.1 Health check

```bash
curl https://exogram.app/api/health/
# {"status": "ok", "db": "ok", "redis": "ok"}  → HTTP 200
# {"status": "error", "db": "error", ...}       → HTTP 503
```

Configure an external monitor (UptimeRobot, Pingdom, Better Uptime) pointing to this endpoint.

### 6.2 Sentry

- Open [sentry.io](https://sentry.io) → Exogram project.
- Configure alerts for:
  - Error rate > 1% in a 5-minute window.
  - New issues with severity HIGH/CRITICAL.
  - P95 latency > 2s on API endpoints.

```python
# Already configured in settings.py with:
# traces_sample_rate=0.1  → 10% sample of transactions for performance
```

### 6.3 Beat heartbeat

Verify that the Celery Beat heartbeat is active:

```bash
docker compose exec redis redis-cli GET celerybeat:heartbeat
# Should return a recent Unix timestamp (< 120 s)
```

If the value is empty or old, beat or the worker are not running:

```bash
# Check status
docker compose ps celery-beat celery

# Restart if necessary
docker compose restart celery-beat celery
```

### 6.4 Embeddings queue

Verify that highlights without an embedding are not accumulating:

```bash
docker compose exec backend python manage.py shell -c "
from books.models import Highlight
pending = Highlight.objects.filter(embedding__isnull=True).count()
total = Highlight.objects.count()
print(f'Without embedding: {pending}/{total}')
"
```

### 6.5 Flower (Celery monitoring)

> ⚠️ **Flower has no authentication.** It is bound to `127.0.0.1:5555` in production
> (configured in `docker-compose.prod.yml`), so it is not accessible from the internet.
> Access only via SSH tunnel.

```bash
# On the local machine
ssh -L 5555:localhost:5555 user@server

# Open in the browser
open http://localhost:5555
```

---

## 7. Incident response

### 7.1 API returns 503 / health check fails

```bash
# 1. Check container status
docker compose ps

# 2. View backend logs
docker compose logs backend --tail=100

# 3. If DB is down
docker compose restart db
docker compose exec backend python manage.py migrate --noinput  # applies pending migrations if any

# 4. If Redis is down
docker compose restart redis
docker compose restart celery  # workers reconnect automatically
```

### 7.2 Celery worker not processing tasks

```bash
# 1. Check heartbeat
docker compose exec redis redis-cli GET celerybeat:heartbeat

# 2. Check task queue
docker compose exec redis redis-cli LLEN celery

# 3. View worker logs
docker compose logs celery --tail=100

# 4. Restart
docker compose restart celery

# 5. If the ONNX model could not be downloaded (EmbeddingModelUnavailable in logs)
# The worker logs the error and skips the task without retries.
# Restart the worker with internet access available.
```

### 7.3 ONNX model not available

```bash
# Verify the volume exists and has the model
docker volume ls | grep models_cache
docker run --rm -v exogram_models_cache:/models alpine ls -lh /models/

# If the file is corrupted or incomplete, delete it to force re-download
docker run --rm -v exogram_models_cache:/models alpine rm -f /models/paraphrase-multilingual-MiniLM-L12-v2.onnx
docker compose restart celery
```

### 7.4 Email sending failure

```bash
# Verify SMTP configuration
docker compose exec backend python manage.py shell -c "
from django.core.mail import send_mail
send_mail('Test', 'Test email', 'no-reply@exogram.app', ['admin@exogram.app'])
print('OK')
"

# If it fails, verify credentials in .env:
# EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD
```

### 7.5 Database full / slow

```bash
# Check size
docker compose exec db psql -U exogram -c "
SELECT pg_size_pretty(pg_database_size('exogram')) AS db_size;
SELECT relname, pg_size_pretty(pg_total_relation_size(relid)) AS size
FROM pg_stat_user_tables ORDER BY pg_total_relation_size(relid) DESC LIMIT 10;
"

# Manual vacuum if there is heavy fragmentation
docker compose exec db psql -U exogram -c "VACUUM ANALYZE;"
```

---

## 8. Administrative tasks

### 8.1 Create genesis user (superuser)

```bash
docker compose exec backend python manage.py createsuperuser
```

### 8.2 Manually generate missing embeddings

```bash
docker compose exec backend python manage.py shell -c "
from books.models import Highlight
from books.tasks import batch_generate_embeddings

pending = list(Highlight.objects.filter(embedding__isnull=True).values_list('id', flat=True))
print(f'Queuing {len(pending)} highlights...')
if pending:
    batch_generate_embeddings.delay(pending)
    print('Task queued.')
"
```

### 8.3 Reset a user's password (admin)

```bash
docker compose exec backend python manage.py changepassword <username>
```

### 8.4 Export a user's data (GDPR)

```bash
docker compose exec backend python manage.py shell -c "
from django.contrib.auth.models import User
user = User.objects.get(username='<nickname>')
# Use the /api/me/export/ endpoint or access via admin
print(user.profile.verified_email)
"
```

### 8.5 Delete a user account (GDPR)

```bash
# Use the authenticated endpoint DELETE /api/me/delete/
# Or from the shell:
docker compose exec backend python manage.py shell -c "
from django.contrib.auth.models import User
user = User.objects.get(username='<nickname>')
user.delete()  # Cascade deletes Profile, Highlights, etc.
print('Deleted.')
"
```

### 8.6 View the waitlist

```bash
docker compose exec backend python manage.py shell -c "
from accounts.models import Waitlist
entries = Waitlist.objects.filter(is_activated=False).order_by('requested_at')
for e in entries:
    print(f'{e.requested_at:%Y-%m-%d} | {e.email} | {e.message[:50]}')
print(f'Total: {entries.count()}')
"
```

### 8.7 Update TLS certificate (Caddy)

Caddy manages the certificate automatically via ACME (Let's Encrypt). No manual intervention required. If there are issues:

```bash
docker compose logs caddy | grep -i cert
docker compose restart caddy
```

---

## 9. Secret rotation

### 9.1 Rotate SECRET_KEY

> ⚠️ Changing `SECRET_KEY` invalidates all active sessions (JWT cookies) and all HMAC tokens for invitations and password resets stored in the database.

```bash
# 1. Generate a new key
NEW_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(64))")
echo "New SECRET_KEY: $NEW_KEY"

# 2. Invalidate active tokens before changing the key
docker compose exec backend python manage.py shell -c "
from accounts.models import InvitationToken, PasswordResetToken
# HMAC tokens calculated with the old key will become invalid.
# Clean them up before the change to avoid confusion.
InvitationToken.objects.all().delete()
PasswordResetToken.objects.filter(used_at__isnull=True).delete()
print('Tokens cleared.')
"

# 3. Update .env
sed -i "s/^SECRET_KEY=.*/SECRET_KEY=$NEW_KEY/" backend/.env

# 4. Restart services
docker compose restart backend celery celery-beat
```

### 9.2 Rotate database password

```bash
NEW_PASS=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

# Change in PostgreSQL
docker compose exec db psql -U postgres -c "ALTER USER exogram PASSWORD '$NEW_PASS';"

# Update .env
sed -i "s|DATABASE_URL=postgres://exogram:.*@|DATABASE_URL=postgres://exogram:$NEW_PASS@|" backend/.env

# Restart
docker compose restart backend celery celery-beat
```

### 9.3 Rotate SMTP credentials

```bash
# 1. Update EMAIL_HOST_PASSWORD in .env
# 2. Restart only the backend (Celery also uses the mailer)
docker compose restart backend celery
```

---

## 10. Compliance / GDPR

### 10.1 Data stored by Exogram per user

| Data                  | Location                | Visibility          |
|-----------------------|-------------------------|---------------------|
| Verified email        | `Profile.verified_email` | Admin only         |
| Nickname              | `Profile.nickname`      | Public              |
| Bio                   | `Profile.bio`           | Public              |
| Avatar                | `media/avatars/`        | Public              |
| Highlights            | `Highlight`             | According to visibility |
| Notes                 | `Note`                  | Private             |
| Invitation tree       | `Profile.invited_by`    | Admin only          |

### 10.2 Delete a user's data (right to erasure)

See section 8.5. `User.delete()` cascades and deletes all related objects thanks to `on_delete=CASCADE` in the models.

Avatars in `media/avatars/` must be deleted manually:

```bash
docker compose exec backend python manage.py shell -c "
from django.contrib.auth.models import User
user = User.objects.get(username='<nickname>')
if user.profile.avatar:
    user.profile.avatar.delete(save=False)
user.delete()
print('User and avatar deleted.')
"
```

### 10.3 Export a user's data (portability)

```bash
curl -X GET https://exogram.app/api/me/export/ \
  -H "Cookie: exo_access=<token>" \
  -H "X-CSRFToken: <csrf>"
```

The endpoint returns JSON with all the highlights, notes, and profile data of the authenticated user.

---

*Last updated: 2026-03-18*
