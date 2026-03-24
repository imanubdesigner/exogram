# Local Development

Guide to bring up the complete environment on your machine.

---

## Prerequisites

- Docker Engine 24+ and Docker Compose v2 (`docker compose`, not `docker-compose`)
- Git
- Python 3.12 (only if you want to run tests without Docker)

---

## 1. Clone the repository

```bash
git clone git@github.com:<org>/exogram.git
cd exogram
```

---

## 2. Create the backend variables file

```bash
cp backend/.env.example backend/.env   # if it exists, or create manually
```

Minimum content for development:

```env
SECRET_KEY=dev-secret-key-replace-in-production-min-50-chars-long-abc123
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,testserver
POSTGRES_PASSWORD=dev_password
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
DEFAULT_FROM_EMAIL=dev@localhost
```

With `EMAIL_BACKEND=console`, all emails (invitations, resets) are printed to
the backend container logs instead of being sent. Sufficient for development.

The remaining variables have reasonable defaults in `settings.py` for the local environment.
See the [complete variable reference](./environment-variables.md).

---

## 3. Start the services

```bash
docker compose up --build
```

This starts: **PostgreSQL** (with pgvector), **Redis**, **backend** (Django runserver),
**Celery worker**, **Celery beat**, and **frontend** (Vite dev server).

Postal (SMTP) does not start by default. It is activated with `--profile mail` only when needed.

Access points:

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000/api/ |
| Django Admin | http://localhost:8000/admin/ |
| Flower (Celery) | http://localhost:5555 |

---

## 4. Create the superuser

In a separate terminal, with the containers running:

```bash
docker compose exec backend python manage.py createsuperuser
```

The command will ask for username, email, and password.
With that user you can access the admin and manually create the first invitation.

---

## 5. Load article fixtures (optional)

The project articles (philosophy, manifesto) have preloadable fixtures:

```bash
docker compose exec backend python manage.py loaddata articles/fixtures/*.json
```

---

## 6. Download the ONNX model for embeddings

The Celery worker generates embeddings for highlights using a local ONNX model
(`paraphrase-multilingual-MiniLM-L12-v2`, ~470 MB). On the first run it is
downloaded automatically from HuggingFace to the `models_cache/` directory.

To preload it manually and avoid the download on the first import:

```bash
docker compose exec celery python manage.py download_onnx_model
```

The `models_cache/` directory is mounted as a shared volume between the
backend and the Celery worker, so the download only happens once.

---

## 7. Run the tests

Tests require PostgreSQL with the `pgvector` extension enabled.
The custom test runner (`PgVectorTestRunner`) enables it automatically.

**With Docker (recommended):**

```bash
docker compose exec backend coverage run --source='.' manage.py test --verbosity=2
docker compose exec backend coverage report
```

**Without Docker** (requires local PostgreSQL with pgvector and configured environment variables):

```bash
cd backend
pip install -r requirements.txt
DJANGO_SETTINGS_MODULE=exogram.settings_ci \
DATABASE_URL=postgres://exogram:test_password@localhost:5432/exogram_test \
coverage run --source='.' manage.py test --verbosity=2
```

The `settings_ci` configuration disables rate limiting and uses `FastPBKDF2PasswordHasher`
to speed up user creation in tests (iterations=1).

---

## 8. Run the linter and security analysis

```bash
# From backend/
flake8 .
isort --check-only .
bandit -r . -x ./migrations,./smoke_tests -ll -ii -c .bandit
pip-audit -r requirements.txt
```

```bash
# From frontend/
npm run build
npm test
```

---

## Typical development workflow

1. Make changes in `backend/` → Django runserver reloads them automatically.
2. Make changes in `frontend/src/` → Vite HMR reloads them in the browser.
3. Model changes → `docker compose exec backend python manage.py makemigrations <app>`.
4. Before committing → run flake8 and isort locally to avoid CI failures.

---

## Reset the database

To start from scratch (destroys all data):

```bash
docker compose down -v
docker compose up --build
```

The `-v` flag removes Docker volumes including `postgres_data`.

---

## Frequent issues

**`type "vector" does not exist` when running tests**
The `PgVectorTestRunner` test runner enables the extension automatically, but
it requires the PostgreSQL user to have superuser or `CREATE EXTENSION` permissions.
In the development environment, the compose `exogram` user already has those permissions.
In manual environments, run: `psql -U postgres -c "CREATE EXTENSION vector;" exogram_test`

**The Celery worker does not process tasks**
Verify that Redis is healthy: `docker compose ps redis`.
Check the worker logs: `docker compose logs celery -f`.

**The frontend does not connect to the API**
The Vite dev server has a proxy configured in `vite.config.js`:
`/api/*` → `http://backend:8000`. Inside Docker this works by service name.
Outside Docker, the API will be at `http://localhost:8000`.
