# 0006 — Caddy como reverse proxy y servidor TLS


## Contexto

En producción se necesita un reverse proxy que termine TLS, sirva archivos estáticos
y enrute tráfico entre el frontend (build estático) y el backend (Gunicorn).

## Decisión

Usar Caddy 2. El `Caddyfile` define:
- TLS automático vía Let's Encrypt (ACME HTTP-01)
- Redirect de `www.` al dominio raíz
- Compresión `zstd` y `gzip`
- Security headers globales (CSP, Referrer-Policy, Permissions-Policy, X-Content-Type-Options, X-Frame-Options)
- Rutas: `/api/*` y `/admin*` → backend, `/static/*` y `/media/*` → archivos, `/*` → SPA con fallback a `index.html`
- Panel de Postal en `postal.<dominio>`

## Alternativas consideradas

**nginx:** más conocido y con mayor documentación comunitaria, pero requiere configuración
manual de certbot, cron de renovación, y la sintaxis es más verbose. El TLS automático
de Caddy elimina toda esa superficie operacional.

**Traefik:** buena integración con Docker labels, pero la configuración dinámica es
más compleja para un stack simple. Overkill para este caso de uso.

**Sin reverse proxy (Gunicorn directo en 443):** Gunicorn no maneja TLS eficientemente,
y mezcla servicio de archivos estáticos con aplicación. Descartado.

## Consecuencias

- Cero configuración de certbot o cron de renovación. Caddy gestiona todo.
- Los certificados se persisten en el volumen `caddy_data`. Si el volumen se pierde, Caddy los renueva automáticamente en el próximo start (con un breve período de downtime).
- Los security headers se emiten desde Caddy para todas las rutas, incluyendo archivos estáticos. Django también los emite vía middleware propio, por lo que hay cobertura doble (útil si Django se expone directamente en dev).
- El Server header de Caddy se suprime para no exponer información de versión.
- `ACME_EMAIL` es obligatorio en producción. Sin él, Let's Encrypt no puede notificar sobre expiración inminente.
