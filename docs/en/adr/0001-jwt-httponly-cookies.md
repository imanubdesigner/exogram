# 0001 — JWT in HttpOnly cookies instead of localStorage

## Context

JWT-based authentication requires storing the token on the client.
The two common options are `localStorage` and HttpOnly cookies.
Exogram is a SPA application (Vue 3) that consumes a Django REST API.

## Decision

JWT tokens are stored exclusively in HttpOnly cookies with the following properties:

- **HttpOnly:** the token is not accessible from JavaScript. A successful XSS attack cannot steal the token.
- **SameSite=Lax:** the cookie is not sent in cross-site requests, mitigating CSRF in most scenarios.
- **Secure** (in production): the cookie only travels over HTTPS.
- **Restricted Path:** the access token is only sent to `/api/`, the refresh token only to `/api/auth/`. This limits the exposure surface.

A **two-token** scheme is used:
- `exo_access`: short-lived access token (20 minutes). Automatically sent in every request to `/api/`.
- `exo_refresh`: longer-lived refresh token (7 days). Only sent to `/api/auth/` to renew the access token.

**CSRF protection** is implemented with Double Submit Cookie: Django issues a CSRF cookie readable by JavaScript (not HttpOnly), and the frontend reads it and includes it as a header in every mutating request (POST, PATCH, DELETE). The backend validates that the header value matches the cookie.

## Alternatives considered

**localStorage:** simpler to implement on the frontend, but vulnerable to XSS. Any script injected into the page can read and exfiltrate the token. Discarded for security reasons.

**sessionStorage:** same attack vector as localStorage. Discarded.

**Cookies without HttpOnly:** accessible from JavaScript, same vulnerability as localStorage. No benefit. Discarded.

## Consequences

- The frontend cannot read the JWT token directly (this is intentional: it is the security guarantee).
- Django's CSRF middleware is mandatory and active. Mutating requests from the frontend must include the `X-CSRFToken` header.
- In tests, DRF's `APIClient` handles cookies automatically.
- Requests from tools like curl or Postman require manual cookie and CSRF management.
- Automatic refresh token rotation (with a blacklist in PostgreSQL) protects against reuse of compromised tokens.
