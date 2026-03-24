# Autenticación

Cómo funciona el sistema de autenticación de Exogram en detalle.

---

## Esquema general

Exogram usa **JWT almacenado en cookies HttpOnly**. El flujo completo:

```
Login (POST /api/auth/login/)
    │
    ▼
Django valida nickname + password
    │
    ▼
Emite dos cookies:
    exo_access  (HttpOnly, SameSite=Lax, Path=/api/)         ← access token
    exo_refresh (HttpOnly, SameSite=Lax, Path=/api/auth/)    ← refresh token
    │
    ▼
Cada request a /api/* incluye exo_access automáticamente (navegador)
    │
    ▼
CookieJWTAuthentication valida el token y autentica al usuario
    │
    ▼ (cuando exo_access expira, ~20 min)
POST /api/auth/token/refresh/ → rota exo_refresh, emite nuevos tokens
```

---

## Access token (`exo_access`)

- **Lifetime:** 20 minutos (configurable con `JWT_ACCESS_TOKEN_MINUTES`)
- **Path:** `/api/` — el navegador solo lo envía en requests a esa ruta
- **Renovación:** automática vía refresh. El frontend detecta 401 y llama al endpoint de refresh antes de reintentar.

## Refresh token (`exo_refresh`)

- **Lifetime:** 7 días (configurable con `JWT_REFRESH_TOKEN_DAYS`)
- **Path:** `/api/auth/` — el navegador solo lo envía en requests a esa ruta
- **Rotación:** cada refresh genera un nuevo par de tokens. El token anterior queda en la blacklist.
- **Blacklist:** tabla `token_blacklist_outstandingtoken` / `token_blacklist_blacklistedtoken` en PostgreSQL (gestionada por `rest_framework_simplejwt.token_blacklist`).

## Por qué dos paths distintos

El access token tiene path `/api/` para que se envíe en todos los requests de la aplicación.
El refresh token tiene path `/api/auth/` — path más restringido — para que **no** se envíe
en cada request, solo cuando se necesita renovar. Esto minimiza la exposición del
token de mayor duración.

---

## CSRF

El login es con cookies, por lo que el navegador las envía automáticamente en requests
cross-site. Para evitar ataques CSRF, se implementa **Double Submit Cookie**:

1. Django emite una cookie `csrftoken` (legible desde JavaScript, **no** HttpOnly).
2. El frontend lee esa cookie y la incluye como header `X-CSRFToken` en cada request mutante (POST, PATCH, PUT, DELETE).
3. `CsrfViewMiddleware` valida que el valor del header coincida con la cookie. Un attacker externo no puede leer la cookie (Same-Origin Policy del navegador) y por tanto no puede construir el header correcto.

La cookie CSRF tiene `SameSite=Lax`, lo que ya bloquea la mayoría de ataques CSRF.
El double-submit agrega una capa adicional.

---

## Login con nickname

El login se hace con **nickname**, no con email. Esto separa:
- **Identidad pública** (nickname): lo que otros usuarios ven.
- **Identidad privada** (email): solo usada para comunicaciones del sistema.

El email no se expone en ningún endpoint público.

---

## Password reset

El flujo está diseñado para no exponer si un email existe en el sistema:

1. `POST /api/auth/password-reset/` con cualquier email → siempre devuelve el mismo mensaje genérico (`"Si el email está registrado, recibirás un link en breve"`).
2. Si el email corresponde a un usuario verificado, se genera un token HMAC y se envía el email.
3. El token se invalida tras el uso (`used_at` timestamp) y expira a las 2 horas.
4. Solo hay un token activo por usuario: al generar uno nuevo, los anteriores sin usar se eliminan.

---

## Seguridad de las cookies en producción

Cuando `FORCE_HTTPS=True`:
- `SESSION_COOKIE_SECURE = True`
- `CSRF_COOKIE_SECURE = True`
- `JWT_COOKIE_SECURE = True`
- `SECURE_HSTS_SECONDS = 31536000` (1 año)
- `SECURE_HSTS_INCLUDE_SUBDOMAINS = True`
- `SECURE_HSTS_PRELOAD = True`
- `SECURE_SSL_REDIRECT = True`

Todos los flags de Secure hacen que las cookies no se envíen por HTTP.

---

## Limpieza de la blacklist

Los tokens expirados permanecen en la blacklist de simplejwt indefinidamente por defecto.
Para limpiarlos periódicamente:

```bash
python manage.py flushexpiredtokens
```

Se recomienda agregar este comando a `CELERY_BEAT_SCHEDULE` para ejecución automática.
