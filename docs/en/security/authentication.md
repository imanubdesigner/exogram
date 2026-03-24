# Authentication

How Exogram's authentication system works in detail.

---

## General scheme

Exogram uses **JWT stored in HttpOnly cookies**. The complete flow:

```
Login (POST /api/auth/login/)
    │
    ▼
Django validates nickname + password
    │
    ▼
Issues two cookies:
    exo_access  (HttpOnly, SameSite=Lax, Path=/api/)         ← access token
    exo_refresh (HttpOnly, SameSite=Lax, Path=/api/auth/)    ← refresh token
    │
    ▼
Each request to /api/* includes exo_access automatically (browser)
    │
    ▼
CookieJWTAuthentication validates the token and authenticates the user
    │
    ▼ (when exo_access expires, ~20 min)
POST /api/auth/token/refresh/ → rotates exo_refresh, issues new tokens
```

---

## Access token (`exo_access`)

- **Lifetime:** 20 minutes (configurable with `JWT_ACCESS_TOKEN_MINUTES`)
- **Path:** `/api/` — the browser only sends it in requests to that path
- **Renewal:** automatic via refresh. The frontend detects 401 and calls the refresh endpoint before retrying.

## Refresh token (`exo_refresh`)

- **Lifetime:** 7 days (configurable with `JWT_REFRESH_TOKEN_DAYS`)
- **Path:** `/api/auth/` — the browser only sends it in requests to that path
- **Rotation:** each refresh generates a new token pair. The previous token is added to the blacklist.
- **Blacklist:** table `token_blacklist_outstandingtoken` / `token_blacklist_blacklistedtoken` in PostgreSQL (managed by `rest_framework_simplejwt.token_blacklist`).

## Why two different paths

The access token has path `/api/` so it is sent in all application requests.
The refresh token has path `/api/auth/` — a more restricted path — so it is **not** sent
on every request, only when renewal is needed. This minimizes the exposure of
the longer-lived token.

---

## CSRF

Login uses cookies, so the browser sends them automatically in cross-site requests.
To prevent CSRF attacks, **Double Submit Cookie** is implemented:

1. Django issues a `csrftoken` cookie (readable from JavaScript, **not** HttpOnly).
2. The frontend reads that cookie and includes it as the `X-CSRFToken` header in every mutating request (POST, PATCH, PUT, DELETE).
3. `CsrfViewMiddleware` validates that the header value matches the cookie. An external attacker cannot read the cookie (browser Same-Origin Policy) and therefore cannot construct the correct header.

The CSRF cookie has `SameSite=Lax`, which already blocks most CSRF attacks.
The double-submit adds an additional layer.

---

## Login with nickname

Login uses **nickname**, not email. This separates:
- **Public identity** (nickname): what other users see.
- **Private identity** (email): used only for system communications.

The email is not exposed in any public endpoint.

---

## Password reset

The flow is designed to avoid exposing whether an email exists in the system:

1. `POST /api/auth/password-reset/` with any email → always returns the same generic message (`"If the email is registered, you will receive a link shortly"`).
2. If the email belongs to a verified user, an HMAC token is generated and the email is sent.
3. The token is invalidated after use (`used_at` timestamp) and expires after 2 hours.
4. Only one active token per user: when a new one is generated, previous unused ones are deleted.

---

## Cookie security in production

When `FORCE_HTTPS=True`:
- `SESSION_COOKIE_SECURE = True`
- `CSRF_COOKIE_SECURE = True`
- `JWT_COOKIE_SECURE = True`
- `SECURE_HSTS_SECONDS = 31536000` (1 year)
- `SECURE_HSTS_INCLUDE_SUBDOMAINS = True`
- `SECURE_HSTS_PRELOAD = True`
- `SECURE_SSL_REDIRECT = True`

All Secure flags prevent cookies from being sent over HTTP.

---

## Blacklist cleanup

Expired tokens remain in the simplejwt blacklist indefinitely by default.
To clean them up periodically:

```bash
python manage.py flushexpiredtokens
```

It is recommended to add this command to `CELERY_BEAT_SCHEDULE` for automatic execution.
