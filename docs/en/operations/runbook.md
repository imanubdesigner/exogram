# Operational Runbook

Quick command reference for common production situations.
For complete procedures (secret management, GDPR, credential rotation),
see the [complete runbook](../runbook.md).

All commands assume you are on the server, in the project directory.

---

## Severity levels

| Level | Description | Response time |
|-------|-------------|---------------|
| **P0** | Service completely unreachable or data loss in progress | Immediate |
| **P1** | Critical functionality degraded (login, invitations, emails) | < 30 min |
| **P2** | Non-critical functionality degraded (embeddings, discovery) | < 4 hours |

---

## Incident playbooks

### P0 — Database down

**Symptoms:** `{"status":"error","db":"error"}` at `/api/health/`, widespread 500 errors.

```bash
# 1. Check container status
dc ps db

# 2. View logs
dc logs db --tail=50

# 3. If the container is stopped, restart it
dc start db

# 4. If it fails to start (corrupted data), restore from backup
# See "Restore from backup" section below

# 5. Verify connectivity from backend
dc exec backend python manage.py dbshell -- --command="SELECT 1;"

# 6. Confirm recovery
curl -s http://127.0.0.1:8000/api/health/ | python3 -m json.tool
```

**Escalation:** If `postgres_data` volume is corrupted → restore from the latest backup.

---

### P0 — Redis down

**Symptoms:** Celery workers disconnected, JWT sessions unable to refresh, throttling errors.

```bash
# 1. Check status
dc ps redis
dc logs redis --tail=30

# 2. Restart (Redis is stateless in this stack; in-memory data will be lost)
dc restart redis

# 3. Verify it responds
dc exec redis redis-cli ping  # should respond PONG

# 4. Restart workers to reconnect
dc restart celery celery-beat

# 5. Check health
curl -s http://127.0.0.1:8000/api/health/ | python3 -m json.tool
```

**Expected impact:** Rate limits reset (they are in-memory). JWT access tokens remain valid until expiry; refresh requires Redis.

---

### P1 — Celery queue stuck

**Symptoms:** Tasks stuck in `PENDING` for more than 10 minutes, embeddings not generated, emails not sent.

```bash
# 1. Check worker status
dc exec celery celery -A exogram inspect ping
dc exec celery celery -A exogram inspect active
dc exec celery celery -A exogram inspect stats

# 2. View pending queue
dc exec celery celery -A exogram inspect reserved

# 3. Check beat heartbeat (if 0 or very old, beat is not running)
dc exec redis redis-cli get celerybeat:heartbeat

# 4. Restart worker (pending tasks return to the queue)
dc restart celery

# 5. If the queue has corrupted tasks blocking the worker, purge
dc exec celery celery -A exogram purge
# ⚠️ Purging removes all pending tasks. Assess impact before running.
```

---

### P1 — Emails not delivered

**Symptoms:** Invitations and password resets not arriving, logs show SMTP errors.

```bash
# 1. View backend logs for SMTP errors
dc logs backend --tail=100 | grep -i "smtp\|email\|postal\|SMTPException"

# 2. Verify Postal is running (if using the mail profile)
dc --profile mail ps postal
dc --profile mail logs postal --tail=30

# 3. Manual test from Django
dc exec backend python manage.py shell -c "
from django.core.mail import send_mail
send_mail('P1 Test', 'Diagnostic', 'no-reply@exogram.app', ['you@email.com'])
print('Sent')
"

# 4. If Postal is down, restart it
dc --profile mail restart postal
```

---

## Post-deploy verification

Run immediately after each deploy:

```bash
# 1. All containers in Up state
dc ps

# 2. Backend health check
curl -s http://127.0.0.1:8000/api/health/ | python3 -m json.tool
# Expected: {"status":"ok","db":"ok","redis":"ok"}

# 3. No recent errors in logs
dc logs backend --tail=20 | grep -E "ERROR|CRITICAL" || echo "No errors"

# 4. Celery worker responds
dc exec celery celery -A exogram inspect ping

# 5. Migrations applied
dc exec backend python manage.py showmigrations | grep '\[ \]' || echo "No pending migrations"
```

---

## Minimum observable metrics

| Metric | Source | Alert threshold |
|--------|--------|----------------|
| HTTP 5xx rate | `dc logs backend` | > 1% of requests in 5 min |
| Backend p95 latency | `dc logs backend` | > 2 s sustained |
| Pending Celery queue | Flower / `inspect reserved` | > 100 tasks for > 5 min |
| Celery Beat heartbeat | Redis `celerybeat:heartbeat` | More than 120 s without update |
| Disk space | `df -h /var/lib/docker` | > 80% |
| Container memory | `docker stats --no-stream` | backend > 1.8 GB, celery > 2.5 GB |

---

```bash
ssh user@server
cd /srv/exogram
```

The compose alias in production is:

```bash
alias dc='docker compose -f docker-compose.yml -f docker-compose.prod.yml'
```

---

## View logs

```bash
# Backend (Django/Gunicorn)
dc logs backend -f

# Celery worker
dc logs celery -f

# Beat (periodic tasks)
dc logs celery-beat -f

# All at once
dc logs -f

# Last 100 lines of a service
dc logs backend --tail=100
```

---

## Service restart

```bash
# Restart a service without rebuilding the image
dc restart backend
dc restart celery
dc restart celery-beat

# Restart all
dc restart

# Forced restart (stops and brings back up)
dc stop backend && dc up -d backend
```

---

## Application status

```bash
# Health check (expects {"status":"ok","db":"ok","redis":"ok"})
curl -s http://127.0.0.1:8000/api/health/ | python3 -m json.tool

# Container status
dc ps

# Resource usage
docker stats --no-stream

# Disk space (Docker volumes)
docker system df
```

---

## Celery tasks

### Check worker status

```bash
# From Flower (web UI, only accessible on localhost)
# ⚠️ Flower has no authentication. It is bound to 127.0.0.1:5555 in production,
# so it is not accessible from the internet. Access only via SSH tunnel:
# Open an SSH tunnel: ssh -L 5555:127.0.0.1:5555 user@server
# Then open: http://localhost:5555

# From the command line
dc exec celery celery -A exogram inspect active
dc exec celery celery -A exogram inspect stats
```

### Verify the beat heartbeat

The beat writes a timestamp to Redis every 60 seconds as a liveness signal.

```bash
dc exec redis redis-cli get celerybeat:heartbeat
# Returns the Unix timestamp of the last execution
# If empty or very stale, the beat is not running
```

### Trigger a task manually

```bash
dc exec backend python manage.py shell -c "
from books.tasks import batch_generate_embeddings
batch_generate_embeddings.delay([1, 2, 3])
print('Task sent')
"
```

### Purge the pending task queue

```bash
dc exec celery celery -A exogram purge
```

---

## Database

### Connect to the PostgreSQL shell

```bash
dc exec db psql -U exogram -d exogram
```

### Manual backup

```bash
dc exec db pg_dump -U exogram exogram | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

### Restore from backup

```bash
gunzip < backup_20260318_120000.sql.gz | dc exec -T db psql -U exogram -d exogram
```

### Run migrations manually

Migrations run automatically on every deploy via `start-web.sh`.
To run them manually:

```bash
dc exec backend python manage.py migrate --noinput
```

### View pending migrations

```bash
dc exec backend python manage.py showmigrations | grep '\[ \]'
```

---

## Django Admin

### Create superuser

```bash
dc exec backend python manage.py createsuperuser
```

### Change a user's password

```bash
dc exec backend python manage.py changepassword <username>
```

### Django shell

```bash
dc exec backend python manage.py shell
```

---

## JWT — Token Blacklist

Rotated refresh tokens are stored in the simplejwt blacklist in PostgreSQL.
Over time the table can grow. Django simplejwt includes a management command
to clean up expired tokens:

```bash
dc exec backend python manage.py flushexpiredtokens
```

It is recommended to schedule this periodically (can be added to `CELERY_BEAT_SCHEDULE`).

---

## SECRET_KEY — Rotation

Rotating `SECRET_KEY` invalidates all active sessions, CSRF cookies, and
pending invitation/reset tokens. Users will need to log in again.

1. Generate new key: `python3 -c "import secrets; print(secrets.token_urlsafe(50))"`
2. Update the `SECRET_KEY` secret in GitHub
3. Update `backend/.env` on the server
4. `dc restart backend celery celery-beat`

---

## TLS certificates

Caddy obtains and renews Let's Encrypt certificates automatically.
Certificate data is persisted in the `caddy_data` volume.

To check certificate status:

```bash
dc exec caddy caddy version
# Caddy logs show automatic renewals
dc logs caddy | grep -i "certificate\|tls\|acme"
```

If the certificate does not renew (edge case), restarting Caddy is sufficient in
most cases: `dc restart caddy`.

---

## Disk space cleanup

```bash
# Unused Docker images
docker image prune -f

# Stopped containers, networks, and unused build cache
docker system prune -f

# With volumes (CAUTION: removes data if not actively in use)
docker system prune --volumes -f
```

---

## Diagnosing frequent errors

### Backend returns 500

```bash
dc logs backend --tail=100 | grep ERROR
dc exec backend python manage.py check
```

### Celery does not process tasks

```bash
# Verify connection with Redis
dc exec celery celery -A exogram inspect ping

# Verify Redis is up
dc exec redis redis-cli ping   # should respond PONG

# Restart worker
dc restart celery
```

### Emails are not being sent

```bash
# Check backend logs for SMTP errors
dc logs backend | grep -i "email\|smtp\|postal"

# Verify Postal is running (if using the mail profile)
dc --profile mail ps postal

# Manual test from Django
dc exec backend python manage.py shell -c "
from django.core.mail import send_mail
send_mail('Test', 'Body', 'from@exogram.app', ['to@example.com'])
print('Sent')
"
```
