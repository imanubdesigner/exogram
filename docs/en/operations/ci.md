# CI Pipeline

How the CI pipeline works, why it is structured this way, and how to reproduce
each check locally.

---

## Overview

The CI runs on every push and pull request targeting `main` or `develop`,
but only when files under `backend/`, `frontend/`, or the workflow itself change.
This avoids unnecessary runs when editing only documentation or configuration
that does not affect the application.

```
push / pull_request
        │
        ├──────────────────────┬──────────────────────┐
        ▼                      ▼                      │
  backend-lint           frontend                     │
  (lint + security,      (audit + lint +              │
   no services)           build + tests)              │
        │                      │                      │
        ▼ (if passes)          │                      │
  backend-test                 │                      │
  (postgres + redis,           │                      │
   migrate + tests)            │                      │
        │                      │                      │
        └──────────┬───────────┘                      │
                   ▼                                  │
                   ci                                 │
            (status gate) ◄────────────────────────────
```

`backend-lint` and `frontend` start immediately and run in parallel.
`backend-test` waits for `backend-lint`: there is no point spinning up
PostgreSQL and Redis if the code has a lint error or a known CVE.
`ci` always runs last and produces a single pass/fail verdict, which is
what branch protection rules should check.

---

## Jobs

### `backend-lint` — Lint & Security

**Timeout:** 10 minutes | **Services:** none

| Step | Tool | What it checks |
|------|------|----------------|
| flake8 | `flake8 .` | Syntax errors, unused imports, undefined names |
| isort | `isort --check-only .` | Import order consistency |
| bandit | `bandit -r . -ll -ii -c .bandit` | Insecure code patterns (SAST) |
| pip-audit | `pip-audit -r requirements.txt` | Known CVEs in Python dependencies |

Configuration lives in `backend/setup.cfg` (flake8, isort) and `backend/.bandit` (bandit).

### `backend-test` — Tests & Coverage

**Timeout:** 20 minutes | **Services:** PostgreSQL 16 + pgvector, Redis 7

Runs only after `backend-lint` succeeds.

| Step | What it does |
|------|-------------|
| Enable pgvector | Creates the `vector` extension before migrations |
| Django system checks | `manage.py check` — validates settings and app config |
| Detect unapplied migrations | `makemigrations --check --dry-run` — fails if a model change has no migration |
| Apply migrations | `migrate --noinput` |
| Tests + coverage | Django test runner with coverage; fails if coverage drops below 70% |
| Upload artifact | `backend/coverage.xml` retained for 14 days |

**Environment used:**

| Variable | Value in CI |
|----------|-------------|
| `DJANGO_SETTINGS_MODULE` | `exogram.settings_ci` |
| `DATABASE_URL` | `postgres://exogram:test_password@localhost:5432/exogram_test` |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` |
| `SECRET_KEY` | Fixed test value (not used in production) |

`exogram/settings_ci.py` extends the base settings with:
- Rate limiting disabled (thresholds set to 100 000/h)
- `FastPBKDF2PasswordHasher` to speed up password hashing in tests

### `frontend` — Audit, Lint, Build & Tests

**Timeout:** 15 minutes | **Services:** none

Runs in parallel with `backend-lint`, fully independent of the backend.

| Step | Tool | What it checks |
|------|------|----------------|
| npm audit | `npm audit --audit-level=high` | Known CVEs in JS dependencies |
| ESLint | `npm run lint` | Code quality and security rules |
| Build | `npm run build` | Vite production build (catches import errors) |
| Tests | `npm test` | Vitest unit tests |

### `ci` — Status Gate

**Timeout:** 5 minutes | **Depends on:** all three jobs above

Runs with `if: always()` so it produces a result even when upstream jobs fail
or are cancelled. Exits 1 if any job did not succeed.

This is the only job that should be listed in branch protection rules.
Listing individual jobs would require updating the protection rule every time
a job is added or renamed.

---

## Concurrency

```yaml
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true
```

If a new commit is pushed to a branch while CI is still running, the old run
is cancelled automatically. This saves GitHub Actions minutes on fast-moving
branches and Dependabot queues.

---

## Caching

| Layer | Strategy |
|-------|----------|
| Python packages | `setup-python@v5` built-in cache, keyed on `backend/requirements.txt` |
| Node modules | `setup-node@v4` built-in cache, keyed on `frontend/package-lock.json` |

Both caches are scoped to the OS and invalidated automatically when the
lock file changes.

---

## Running checks locally

### Backend lint

```bash
cd backend
pip install flake8 isort bandit pip-audit
flake8 .
isort --check-only .
bandit -r . -x ./migrations,./smoke_tests -ll -ii -c .bandit
pip-audit -r requirements.txt
```

### Backend tests

Requires local PostgreSQL with pgvector and Redis running (use `docker compose up db redis`).

```bash
cd backend
export DJANGO_SETTINGS_MODULE=exogram.settings_ci
export DATABASE_URL=postgres://exogram:dev_password@localhost:5432/exogram
export SECRET_KEY=any-value-for-local-testing
export CELERY_BROKER_URL=redis://localhost:6379/0
export CELERY_RESULT_BACKEND=redis://localhost:6379/0
export ALLOWED_HOSTS=localhost,127.0.0.1,testserver

coverage run --source='.' manage.py test --verbosity=2
coverage report --fail-under=70
```

### Frontend

```bash
cd frontend
npm ci
npm audit --audit-level=high
npm run lint
npm run build
npm test
```

---

## Branch protection setup

In **Settings → Branches → Branch protection rules** for `main`:

- Enable **Require status checks to pass before merging**
- Add only the `CI — All checks passed` job as required check
- Enable **Require branches to be up to date before merging**

Do not add `backend-lint`, `backend-test`, or `frontend` individually —
the status gate covers all of them.

---

## Adding a new check

1. Add the step to the appropriate job (`backend-lint`, `backend-test`, or `frontend`).
2. If the new check needs its own services or has a very different timeout,
   consider a new job that feeds into `ci` via `needs`.
3. Update this document and `docs/en/security/ci-scanning.md` if the check is security-related.
