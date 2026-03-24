# Módulo core: exogram

El módulo raíz del proyecto Django. Contiene configuración, middleware, autenticación,
throttling, health check e infraestructura de tests.

---

## Settings

### `settings.py`

Configuración principal. Todas las variables sensibles se leen con `python-decouple`
desde `backend/.env`. No hay valores hardcodeados.

Aspectos destacados:
- `SECRET_KEY` no tiene default: si no está configurado, Django falla al arrancar. Intencional.
- `DEBUG=False` por default. Hay que habilitarlo explícitamente en desarrollo.
- `CONN_MAX_AGE=600`: las conexiones a PostgreSQL se reutilizan 10 minutos en lugar de abrirse y cerrarse por request.
- `DATABASE_URL` tiene precedencia sobre las variables individuales de DB.
- Logging: JSON estructurado en producción (`DEBUG=False`), formato legible en desarrollo.
- Sentry se inicializa solo si `SENTRY_DSN` está configurado y empieza con `https://`.

### `settings_ci.py`

Override para el entorno de CI. Hereda de `settings.py` con dos cambios:
1. `DEFAULT_THROTTLE_CLASSES = []`: desactiva el throttling para evitar falsos negativos por rate limiting en tests que hacen muchos requests.
2. `PASSWORD_HASHERS`: usa `FastPBKDF2PasswordHasher` (iterations=1) para acelerar la creación de usuarios en tests.

---

## Autenticación: `CookieJWTAuthentication`

Backend de autenticación custom en `accounts/authentication.py`.
Extiende `JWTAuthentication` de simplejwt para leer el access token desde la cookie
`exo_access` en lugar del header `Authorization: Bearer`.

Django REST Framework lo usa como `DEFAULT_AUTHENTICATION_CLASSES`.

---

## Middleware: `ContentSecurityPolicyMiddleware`

Emite el header `Content-Security-Policy` en todas las respuestas Django.
El valor es configurable via `settings.CONTENT_SECURITY_POLICY`.

En producción, Caddy también emite CSP. La doble capa cubre el admin de Django
y cualquier escenario en que el backend se acceda directamente (desarrollo, debugging).

---

## Throttling

`exogram/throttles.py` define `DefaultUserRateThrottle` que usa el scope `default_user`.

Scopes configurados en `settings.py`:
| Scope | Límite (prod) | Uso |
|---|---|---|
| `anon` | 20/hora | Endpoints públicos sin auth |
| `default_user` | 500/hora | Endpoints autenticados genéricos |
| `chat_polling` | 2000/hora | Polling de mensajes en threads |
| `auth` | 20/hora | Login, register, password reset |
| `search` | 200/hora | Búsqueda semántica (costosa en CPU) |

---

## Health check

`GET /api/health/`

Verifica conectividad con PostgreSQL y Redis. Devuelve:
- `200 OK` con `{"status":"ok","db":"ok","redis":"ok"}` si ambos responden.
- `503 Service Unavailable` con detalle del fallo si alguno no responde.

Usado por el workflow de deploy para verificar que el servidor quedó operativo tras el update.

---

## Infraestructura de tests

### `PgVectorTestRunner`

Test runner custom en `exogram/test_runner.py`. Extiende `DiscoverRunner`.

El problema que resuelve: Django crea la base de datos de tests con `CREATE DATABASE`
y luego corre `migrate`. Pero `migrate` necesita que la extensión `vector` exista primero.
Sin este runner, los modelos con `VectorField` fallan con `type "vector" does not exist`.

La solución: monkey-patch de `_create_test_db` para inyectar `CREATE EXTENSION IF NOT EXISTS vector`
justo después de crear la DB y antes de migrar.

### `FastPBKDF2PasswordHasher`

En `exogram/test_hashers.py`. Subclase de `PBKDF2PasswordHasher` con `iterations=1`.
Reduce el tiempo de hashing de ~100ms a <1ms por password en tests.
**Nunca usar en producción.**
