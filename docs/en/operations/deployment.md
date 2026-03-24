# Deployment

How the automated deploy flow works and how to run it.

---

## Production architecture

```
Internet
   │
   ▼
Caddy (80/443) ── automatic TLS via Let's Encrypt
   │
   ├── /api/*  ──────► backend:8000  (Gunicorn, 4 workers × 2 threads)
   ├── /admin* ──────► backend:8000
   ├── /static/* ────► /srv/static   (files served directly by Caddy)
   ├── /media/* ─────► /srv/media
   └── /* ───────────► /srv/frontend/dist  (Vue SPA, with fallback to index.html)

backend ──► PostgreSQL 16 + pgvector
backend ──► Redis 7
Celery worker ──► Redis (broker) ──► PostgreSQL (results)
Celery beat ──► Redis + PostgreSQL (schedule persisted with django-celery-beat)
Postal ──► MariaDB + Redis  (self-hosted SMTP, "mail" profile)
```

PostgreSQL and Redis ports are restricted to `127.0.0.1` in production
(defined in `docker-compose.prod.yml`). They are only accessible from the internal Docker
network and from the host itself.

---

## CI/CD flow

The deploy is fully automated. Every push to `main` triggers this flow:

```
push to main
    │
    ▼
CI (.github/workflows/ci.yml)
    ├── backend-lint  ─── (parallel) → flake8 + isort + bandit + pip-audit
    ├── backend-test  ─── (after lint) → migrate + tests + coverage ≥ 70%
    ├── frontend      ─── (parallel) → npm audit + eslint + build + vitest
    └── ci            ─── (status gate) → pass/fail verdict
    │
    ▼ (if all pass)
Deploy (.github/workflows/deploy.yml)
    ├── build frontend (with VITE_API_URL injected)
    ├── rsync repository to server
    ├── upload backend/.env and .env to server
    ├── docker compose build + up -d
    └── curl /api/health/ → verifies the deploy responded
```

The deploy only runs if CI passed **and** the branch is `main`.

---

## Server prerequisites

- Docker Engine 24+ and Docker Compose v2
- User with SSH access and permissions to run `docker compose`
- Ports 80 and 443 open in the firewall
- Ports 25 and 587 open if using Postal for email

---

## Setting up the deploy for the first time

### 1. Generate an SSH key pair for deploy

On your local machine:

```bash
ssh-keygen -t ed25519 -C "exogram-deploy" -f ~/.ssh/exogram_deploy
```

Copy the public key to the server:

```bash
ssh-copy-id -i ~/.ssh/exogram_deploy.pub user@your-server.com
```

### 2. Load the secrets in GitHub

Go to **Settings → Secrets and variables → Actions** in the repository and create
each secret from the [complete list](./environment-variables.md#secrets-required-in-github-for-automatic-deploy).

The four deploy infrastructure secrets:

| Secret | Value |
|---|---|
| `DEPLOY_SSH_KEY` | Content of `~/.ssh/exogram_deploy` (private key) |
| `DEPLOY_HOST` | Server IP or hostname |
| `DEPLOY_USER` | SSH user |
| `DEPLOY_PATH` | Absolute path on the server, e.g. `/srv/exogram` |

### 3. Configure database credentials

Before activating the deploy, make sure `POSTGRES_PASSWORD` is defined
as a GitHub Secret (see step 2). The `docker-compose.yml` uses `${POSTGRES_PASSWORD:-dev_password}`:
**if the secret does not exist, the DB starts with `dev_password`, which is insecure in production.**

To generate a strong password:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Add the result as the `POSTGRES_PASSWORD` secret in GitHub. Also add
`POSTGRES_DB` (default: `exogram`) and `POSTGRES_USER` (default: `exogram`) if
you want to customize them.

> **Note:** If a `postgres_data` volume already exists with the previous password,
> changing `POSTGRES_PASSWORD` also requires rotating the credential inside
> PostgreSQL (see the Secret Rotation section in the Runbook).

### 3.b Configure the Django admin URL

The value of `ADMIN_URL` in the GitHub Secrets determines the Django admin path.
Changing it is a useful obscurity measure, but **requires synchronizing the Caddyfile**:

If `ADMIN_URL=my-secret-panel/`, update in `Caddyfile`:

```
handle /my-secret-panel* {
    reverse_proxy backend:8000
}
```

Without this update, Caddy will not route the new path to the backend.

### 4. Enable the deploy workflow

The file `deploy.yml.disabled` contains the ready workflow. Rename it to activate:

```bash
mv .github/workflows/deploy.yml.disabled .github/workflows/deploy.yml
git add .github/workflows/deploy.yml
git rm .github/workflows/deploy.yml.disabled
git commit -m "enable production deploy workflow"
git push
```

From that commit onwards, every push to `main` that passes CI will trigger the deploy.

### 5. First server initialization

The first deploy creates the containers and runs migrations automatically.
After it finishes, create the superuser:

```bash
ssh user@your-server.com
cd /srv/exogram
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec backend python manage.py createsuperuser
```

Load the article fixtures if applicable:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec backend python manage.py loaddata articles/fixtures/*.json
```

---

## Subsequent deploys

With the workflow active, every `git push origin main` is a deploy if CI passes.
No manual steps required.

To force a redeploy without code changes:

```bash
git commit --allow-empty -m "chore: force redeploy"
git push
```

---

## Verifying the deploy status

```bash
# Application health check
curl https://exogram.app/api/health/

# Expected response (200 OK):
# {"status": "ok", "db": "ok", "redis": "ok"}

# Backend logs
ssh user@server 'cd /srv/exogram && docker compose logs backend --tail=50'

# Status of all containers
ssh user@server 'cd /srv/exogram && docker compose ps'
```

---

## Rollback

The deploy uses `rsync` over the server directory. To revert to a previous version:

```bash
ssh user@server
cd /srv/exogram

# View the last deployed commits (deploy checks out the exact commit)
git log --oneline -10

# Revert to a previous commit on the server
git checkout <previous-hash>
docker compose -f docker-compose.yml -f docker-compose.prod.yml build
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

For a clean rollback it is recommended to do a `git revert` on the `main` branch and let
CI/CD handle the deploy, rather than intervening manually on the server.

---

## Dependency updates

After modifying `backend/requirements.txt` or `frontend/package.json`:

1. CI validates the new dependencies with `pip-audit` and `npm audit`
2. The deploy automatically rebuilds the Docker images (`docker compose build`)
3. No manual steps required

---

## ONNX model in production

The ONNX model for embeddings (~470 MB) is persisted in the `models_cache` volume
(defined in `docker-compose.prod.yml`). It is downloaded from HuggingFace the first
time the Celery worker needs it. It is not included in the Docker image.

If the volume is lost (e.g. by `docker compose down -v`), the model is downloaded
on the first highlight that requires an embedding. To preload it:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec celery \
  python manage.py download_onnx_model
```

---

## Release candidate and Go/No-Go

### How to create an RC tag

```bash
git tag -a v1.0.0-rc1 -m "Release candidate 1"
git push origin v1.0.0-rc1
```

The tag triggers the deploy workflow if configured with `on: push: tags`.

### Preflight checklist (before deploy)

- [ ] CI green on `main` (tests, lint, bandit, pip-audit, npm audit, build)
- [ ] Environment variables updated in GitHub Secrets
- [ ] `ADMIN_URL` changed from the default value and synced with Caddyfile
- [ ] `SECRET_KEY` generated with `secrets.token_urlsafe(50)` (not the example value)
- [ ] `POSTGRES_PASSWORD` is secure and saved as a Secret
- [ ] DB backup is current (if upgrading an existing version)
- [ ] CHANGELOG.md updated with the changes for this version
- [ ] `SECURITY.md` reviewed with a valid contact email

### Postflight checklist (after deploy)

- [ ] `curl -s https://<domain>/api/health/` returns `{"status":"ok","db":"ok","redis":"ok"}`
- [ ] Login works with a test user
- [ ] Invitation email arrives correctly
- [ ] No `ERROR` or `CRITICAL` in `dc logs backend --tail=50`
- [ ] Celery responds: `dc exec celery celery -A exogram inspect ping`
- [ ] HTTPS active and certificate valid (Caddy issues automatically)
- [ ] Admin accessible at `https://<domain>/<ADMIN_URL>`

### Go/No-Go criteria

| Condition | Decision |
|-----------|----------|
| All postflight checks green | ✅ Go |
| Health check fails | 🔴 No-Go → immediate rollback |
| Errors in logs or Celery not responding | 🔴 No-Go → investigate before continuing |
| TLS certificate not issued (> 5 min) | 🟡 Wait 10 min, if it persists → rollback |

### Rollback

```bash
# Option 1: revert in git (preferred — leaves traceability)
git revert HEAD --no-edit
git push origin main

# Option 2: manual rollback on the server (if deploy broke something critical)
ssh user@server
cd /srv/exogram
git checkout <previous-commit>
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```
