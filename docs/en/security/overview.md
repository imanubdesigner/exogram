# Security — Overview

Map of the security controls implemented in Exogram.

---

## Attack surface and controls

| Area | Risk | Control |
|---|---|---|
| Authentication | Token theft | JWT in HttpOnly cookies (not accessible from JS) |
| Authentication | CSRF | Double Submit Cookie + `CsrfViewMiddleware` |
| Authentication | Brute force | `auth` throttle: 20 requests/hour on login and registration |
| Authentication | Refresh token replay | Rotation + blacklist in PostgreSQL |
| Invitation tokens | Rainbow table | HMAC-SHA256 with `SECRET_KEY` as key |
| Reset tokens | Infinite lifetime | 2-hour TTL, invalidated after use |
| Avatar upload | XSS via SVG | Rejection by magic bytes + re-encoding with Pillow |
| Avatar upload | Execution via Pillow | Re-encoding removes payloads in metadata |
| Passwords | Cracking speed | PBKDF2-SHA256 (Django default, high iterations) |
| API | User enumeration | Generic responses on reset and login endpoints |
| API | Data exposure | Profile hidden with hermit mode returns 404 |
| Infra | Port exposure | DB and Redis on `127.0.0.1` in production |
| Infra | RCE in container | Non-root user (`appuser`, uid=1000) in Docker |
| HTTP headers | Clickjacking | `X-Frame-Options: DENY` |
| HTTP headers | MIME sniffing | `X-Content-Type-Options: nosniff` |
| HTTP headers | XSS | Strict CSP in Caddy and Django middleware |
| HTTP headers | HTTPS downgrade | HSTS with preload (when `FORCE_HTTPS=True`) |
| Django Admin | Enumeration | Configurable admin URL (`ADMIN_URL`) |
| Moderation | Toxic content | Local toxicity analysis engine |
| Code | Known vulnerabilities | `pip-audit` in CI |
| Code | Security bugs | `bandit` SAST in CI |

---

## What is currently out of scope

- **Email verification**: registration does not require verifying the email. This is intentional for the MVP (the invitation system already acts as a quality filter). It is an account takeover risk if someone invites an email they do not control, but the damage is limited: the inviter knows the invitee.
- **2FA / MFA**: not implemented. A natural next step if the project grows.
- **Audit log**: actions are logged (INFO/ERROR in Django logs) but there is no persistent audit record in the database.
- **Rate limiting on read endpoints**: only write and auth endpoints have strict throttling. Read endpoints have the global user limit (500/hour).

---

## Related documents

- [Authentication in detail](./authentication.md)
- [Authorization and trust levels](./authorization.md)
- [CI scanning tools](./ci-scanning.md)
- [ADR 0001: JWT in cookies](../adr/0001-jwt-httponly-cookies.md)
