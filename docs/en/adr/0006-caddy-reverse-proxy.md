# 0006 — Caddy as reverse proxy and TLS server

## Context

In production, a reverse proxy is needed to terminate TLS, serve static files,
and route traffic between the frontend (static build) and the backend (Gunicorn).

## Decision

Use Caddy 2. The `Caddyfile` defines:
- Automatic TLS via Let's Encrypt (ACME HTTP-01)
- Redirect from `www.` to the root domain
- `zstd` and `gzip` compression
- Global security headers (CSP, Referrer-Policy, Permissions-Policy, X-Content-Type-Options, X-Frame-Options)
- Routes: `/api/*` and `/admin*` → backend, `/static/*` and `/media/*` → files, `/*` → SPA with fallback to `index.html`
- Postal panel at `postal.<domain>`

## Alternatives considered

**nginx:** better known and with greater community documentation, but requires manual
certbot configuration, renewal cron, and the syntax is more verbose. Caddy's automatic TLS
eliminates all of that operational surface.

**Traefik:** good integration with Docker labels, but dynamic configuration is
more complex for a simple stack. Overkill for this use case.

**No reverse proxy (Gunicorn directly on 443):** Gunicorn does not handle TLS efficiently,
and it mixes static file serving with the application. Discarded.

## Consequences

- Zero certbot or renewal cron configuration. Caddy manages everything.
- Certificates are persisted in the `caddy_data` volume. If the volume is lost, Caddy renews them automatically on the next start (with a brief downtime period).
- Security headers are emitted from Caddy for all routes, including static files. Django also emits them via its own middleware, providing double coverage (useful if Django is exposed directly in dev).
- Caddy's Server header is suppressed to avoid exposing version information.
- `ACME_EMAIL` is mandatory in production. Without it, Let's Encrypt cannot notify about imminent expiration.
