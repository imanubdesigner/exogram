# Core module: exogram

The root module of the Django project. Contains configuration, middleware, authentication,
throttling, health check, and test infrastructure.

---

## Settings

### `settings.py`

Main configuration. All sensitive variables are read with `python-decouple`
from `backend/.env`. No values are hardcoded.

Notable aspects:
- `SECRET_KEY` has no default: if not configured, Django fails to start. This is intentional.
- `DEBUG=False` by default. Must be explicitly enabled in development.
- `CONN_MAX_AGE=600`: PostgreSQL connections are reused for 10 minutes instead of being opened and closed per request.
- `DATABASE_URL` takes precedence over individual DB variables.
- Logging: structured JSON in production (`DEBUG=False`), human-readable format in development.
- Sentry is initialized only if `SENTRY_DSN` is configured and starts with `https://`.

### `settings_ci.py`

Override for the CI environment. Inherits from `settings.py` with two changes:
1. `DEFAULT_THROTTLE_CLASSES = []`: disables throttling to avoid false negatives from rate limiting in tests that make many requests.
2. `PASSWORD_HASHERS`: uses `FastPBKDF2PasswordHasher` (iterations=1) to speed up user creation in tests.

---

## Authentication: `CookieJWTAuthentication`

Custom authentication backend in `accounts/authentication.py`.
Extends simplejwt's `JWTAuthentication` to read the access token from the `exo_access` cookie
instead of the `Authorization: Bearer` header.

Django REST Framework uses it as `DEFAULT_AUTHENTICATION_CLASSES`.

---

## Middleware: `ContentSecurityPolicyMiddleware`

Emits the `Content-Security-Policy` header on all Django responses.
The value is configurable via `settings.CONTENT_SECURITY_POLICY`.

In production, Caddy also emits CSP. The double layer covers the Django admin
and any scenario where the backend is accessed directly (development, debugging).

---

## Throttling

`exogram/throttles.py` defines `DefaultUserRateThrottle` using the `default_user` scope.

Scopes configured in `settings.py`:
| Scope | Limit (prod) | Usage |
|---|---|---|
| `anon` | 20/hour | Public endpoints without auth |
| `default_user` | 500/hour | Generic authenticated endpoints |
| `chat_polling` | 2000/hour | Message polling in threads |
| `auth` | 20/hour | Login, register, password reset |
| `search` | 200/hour | Semantic search (CPU-intensive) |

---

## Health check

`GET /api/health/`

Verifies connectivity with PostgreSQL and Redis. Returns:
- `200 OK` with `{"status":"ok","db":"ok","redis":"ok"}` if both respond.
- `503 Service Unavailable` with failure details if either does not respond.

Used by the deploy workflow to verify the server is operational after an update.

---

## Test infrastructure

### `PgVectorTestRunner`

Custom test runner in `exogram/test_runner.py`. Extends `DiscoverRunner`.

The problem it solves: Django creates the test database with `CREATE DATABASE`
and then runs `migrate`. But `migrate` requires the `vector` extension to exist first.
Without this runner, models with `VectorField` fail with `type "vector" does not exist`.

The solution: monkey-patching `_create_test_db` to inject `CREATE EXTENSION IF NOT EXISTS vector`
right after creating the DB and before migrating.

### `FastPBKDF2PasswordHasher`

In `exogram/test_hashers.py`. Subclass of `PBKDF2PasswordHasher` with `iterations=1`.
Reduces hashing time from ~100ms to <1ms per password in tests.
**Never use in production.**
