# Variables de entorno

Referencia exhaustiva de todas las variables que el proyecto consume.
Las variables del backend se leen con `python-decouple` desde `backend/.env`.
Las del frontend se pasan como argumentos de build (`VITE_*`).
Las del compose raíz se leen desde `.env` en el directorio del proyecto.

---

## Cómo funciona la jerarquía de archivos

```
exogram/
├── .env                ← Variables del compose raíz (APP_DOMAIN, ACME_EMAIL, Postal, Sentry)
└── backend/
    └── .env            ← Variables de Django/Celery (SECRET_KEY, DB, Redis, JWT, email, etc.)
```

En producción ambos archivos los genera el workflow de deploy a partir de los secrets de GitHub.
En desarrollo los creás manualmente (ver [Desarrollo local](./local-development.md)).

---

## Compose raíz — `.env`

Usadas por `docker-compose.yml` y `docker-compose.prod.yml`.

| Variable | Requerida | Ejemplo | Descripción |
|---|---|---|---|
| `APP_DOMAIN` | Sí (prod) | `exogram.app` | Dominio principal. Caddy lo usa para TLS y rutas. |
| `ACME_EMAIL` | Sí (prod) | `admin@exogram.app` | Email para Let's Encrypt. Recibe avisos de expiración. |
| `SENTRY_DSN` | No | `https://abc@sentry.io/123` | DSN de Sentry. Vacío = Sentry deshabilitado. |
| `REDIS_URL` | No | `redis://redis:6379/0` | URL de Redis. Default interno al compose. |
| `VITE_DONATION_ALIAS` | No | `@alias` | Alias de donación que aparece en la UI. |
| `POSTAL_DB_ROOT_PASSWORD` | Solo si usás Postal | `s3cr3t` | Root password de MariaDB para Postal. |
| `POSTAL_DB_PASSWORD` | Solo si usás Postal | `s3cr3t` | Password del usuario `postal` en MariaDB. |
| `POSTAL_RAILS_SECRET_KEY` | Solo si usás Postal | cadena larga | Secret key de Rails interno de Postal. |

---

## Backend — `backend/.env`

Usadas por Django, Celery y Gunicorn.

### Seguridad y Django

| Variable | Requerida | Ejemplo | Descripción |
|---|---|---|---|
| `SECRET_KEY` | **Sí** | cadena 50+ chars | Clave maestra de Django. Usada para firmar sesiones, tokens CSRF y HMAC de invitaciones. Nunca reutilizar entre entornos. Generar con `python -c "import secrets; print(secrets.token_urlsafe(50))"`. |
| `DEBUG` | No | `False` | `True` solo en desarrollo. En producción debe ser `False`. |
| `ALLOWED_HOSTS` | **Sí** | `exogram.app,www.exogram.app` | Hosts aceptados por Django. Separados por coma. Incluir el dominio y sus variantes. |
| `DJANGO_SETTINGS_MODULE` | No | `exogram.settings` | Módulo de settings a usar. Default: `exogram.settings`. |
| `ADMIN_URL` | No | `gestion-secreta/` | Path del admin de Django. Ofuscar para evitar enumeración. Default: `admin/`. |
| `FORCE_HTTPS` | No | `True` | Activa HSTS, SSL redirect y cookies Secure. Solo en producción con TLS. |

### Base de datos

Se puede proveer como `DATABASE_URL` (forma compacta) o como variables individuales.
Si ambas están presentes, `DATABASE_URL` tiene precedencia.

| Variable | Requerida | Ejemplo | Descripción |
|---|---|---|---|
| `DATABASE_URL` | No* | `postgres://user:pass@db:5432/exogram` | URL completa de conexión. |
| `POSTGRES_DB` | No* | `exogram` | Nombre de la base de datos. |
| `POSTGRES_USER` | No* | `exogram` | Usuario de PostgreSQL. |
| `POSTGRES_PASSWORD` | No* | `s3cr3t` | Password de PostgreSQL. |
| `DB_HOST` | No | `db` | Host de PostgreSQL. Default: `db` (nombre del servicio Docker). |
| `DB_PORT` | No | `5432` | Puerto de PostgreSQL. Default: `5432`. |

*Una de las dos formas es requerida.

### Redis y Celery

| Variable | Requerida | Ejemplo | Descripción |
|---|---|---|---|
| `CELERY_BROKER_URL` | No | `redis://redis:6379/0` | URL del broker de Celery. Default: `redis://redis:6379/0`. |
| `CELERY_RESULT_BACKEND` | No | `redis://redis:6379/0` | Backend de resultados de Celery. Default igual al broker. |
| `REDIS_URL` | No | `redis://redis:6379/0` | Usado por el heartbeat de Celery Beat y el health check. |

### JWT y cookies de autenticación

| Variable | Requerida | Ejemplo | Descripción |
|---|---|---|---|
| `JWT_ACCESS_TOKEN_MINUTES` | No | `20` | Duración del access token en minutos. Default: `20`. |
| `JWT_REFRESH_TOKEN_DAYS` | No | `7` | Duración del refresh token en días. Default: `7`. |
| `JWT_ACCESS_COOKIE_NAME` | No | `exo_access` | Nombre de la cookie del access token. Default: `exo_access`. |
| `JWT_REFRESH_COOKIE_NAME` | No | `exo_refresh` | Nombre de la cookie del refresh token. Default: `exo_refresh`. |
| `JWT_ACCESS_COOKIE_PATH` | No | `/api/` | Path de la cookie de acceso. Default: `/api/`. |
| `JWT_REFRESH_COOKIE_PATH` | No | `/api/auth/` | Path de la cookie de refresh. Restringir al mínimo. Default: `/api/auth/`. |
| `JWT_COOKIE_SECURE` | No | `True` | Marca las cookies como Secure (solo HTTPS). Se hereda de `FORCE_HTTPS` si no se define. |
| `JWT_COOKIE_SAMESITE` | No | `Lax` | Política SameSite de las cookies JWT. Default: `Lax`. |
| `JWT_COOKIE_DOMAIN` | No | `.exogram.app` | Dominio de las cookies. Vacío = mismo dominio que el request. |

### CORS y CSRF

| Variable | Requerida | Ejemplo | Descripción |
|---|---|---|---|
| `CORS_ALLOWED_ORIGINS` | No | `https://exogram.app` | Orígenes CORS permitidos. Separados por coma. Default: `localhost:5173`. |
| `CSRF_TRUSTED_ORIGINS` | No | `https://exogram.app` | Orígenes de confianza para CSRF. Separados por coma. |

### Email (Postal / SMTP)

| Variable | Requerida | Ejemplo | Descripción |
|---|---|---|---|
| `EMAIL_HOST` | No | `postal` | Host SMTP. Default: `postal` (nombre del servicio Docker). |
| `EMAIL_PORT` | No | `587` | Puerto SMTP. Default: `587`. |
| `EMAIL_HOST_USER` | No | `noreply@exogram.app` | Usuario SMTP. |
| `EMAIL_HOST_PASSWORD` | No | `s3cr3t` | Password SMTP. |
| `EMAIL_USE_TLS` | No | `True` | Usar STARTTLS. Default en settings: `True`. |
| `EMAIL_USE_SSL` | No | `False` | Usar SSL directo (puerto 465). Incompatible con `EMAIL_USE_TLS`. |
| `DEFAULT_FROM_EMAIL` | No | `Exogram <noreply@exogram.app>` | Remitente por defecto en todos los emails. |
| `EMAIL_BACKEND` | No | `django.core.mail.backends.smtp.EmailBackend` | Backend de email. Cambiar a `locmem` o `console` para debug local. |

### URLs y frontend

| Variable | Requerida | Ejemplo | Descripción |
|---|---|---|---|
| `FRONTEND_BASE_URL` | No | `https://exogram.app` | Base URL del frontend. Usada para construir links en emails de invitación y reset de contraseña. Default: `http://localhost:5173`. |
| `OPENLIBRARY_API_URL` | No | `https://openlibrary.org/api` | Base URL de OpenLibrary para enriquecimiento de metadatos. Default: el valor indicado. |
| `PASSWORD_RESET_TOKEN_TTL_HOURS` | No | `2` | Validez del token de reset de contraseña en horas. Default: `2`. |

### Observabilidad

| Variable | Requerida | Ejemplo | Descripción |
|---|---|---|---|
| `SENTRY_DSN` | No | `https://abc@sentry.io/123` | DSN de Sentry para el backend. Vacío = deshabilitado. |

---

## Frontend — variables de build (`VITE_*`)

Se pasan en tiempo de build como `VITE_API_URL=https://... npm run build`.
El workflow de deploy las inyecta automáticamente desde los secrets de GitHub.

| Variable | Requerida | Ejemplo | Descripción |
|---|---|---|---|
| `VITE_API_URL` | No | `https://exogram.app` | Base URL del backend. El frontend concatena `/api`. Vacío = `http://localhost:8000/api`. |
| `VITE_DONATION_ALIAS` | No | `@alias` | Alias de donación visible en la UI. Opcional. |

---

## Secrets requeridos en GitHub para el deploy automático

El workflow `deploy.yml` requiere que estos secrets estén configurados en
**Settings → Secrets and variables → Actions** del repositorio.

```
SECRET_KEY
ALLOWED_HOSTS
ADMIN_URL
FORCE_HTTPS
DJANGO_SETTINGS_MODULE
POSTGRES_DB
POSTGRES_USER
POSTGRES_PASSWORD
DB_HOST
DB_PORT
DATABASE_URL
REDIS_URL
CELERY_BROKER_URL
CELERY_RESULT_BACKEND
JWT_ACCESS_TOKEN_MINUTES
JWT_REFRESH_TOKEN_DAYS
JWT_ACCESS_COOKIE_NAME
JWT_REFRESH_COOKIE_NAME
JWT_ACCESS_COOKIE_PATH
JWT_REFRESH_COOKIE_PATH
JWT_COOKIE_SECURE
JWT_COOKIE_SAMESITE
JWT_COOKIE_DOMAIN
CORS_ALLOWED_ORIGINS
CSRF_TRUSTED_ORIGINS
FRONTEND_BASE_URL
OPENLIBRARY_API_URL
PASSWORD_RESET_TOKEN_TTL_HOURS
EMAIL_BACKEND
EMAIL_HOST
EMAIL_PORT
EMAIL_HOST_USER
EMAIL_HOST_PASSWORD
EMAIL_USE_TLS
EMAIL_USE_SSL
DEFAULT_FROM_EMAIL
SENTRY_DSN
APP_DOMAIN
ACME_EMAIL
DEPLOY_SSH_KEY
DEPLOY_HOST
DEPLOY_USER
DEPLOY_PATH
```
