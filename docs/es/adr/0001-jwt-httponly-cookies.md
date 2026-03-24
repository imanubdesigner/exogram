# 0001 — JWT en HttpOnly cookies en lugar de localStorage

## Contexto

La autenticación basada en JWT requiere almacenar el token en el cliente.
Las dos opciones habituales son `localStorage` y cookies HttpOnly.
Exogram es una aplicación SPA (Vue 3) que consume una API Django REST.

## Decisión

Los tokens JWT se almacenan exclusivamente en cookies HttpOnly con las siguientes propiedades:

- **HttpOnly:** el token no es accesible desde JavaScript. Un ataque XSS exitoso no puede robar el token.
- **SameSite=Lax:** la cookie no se envía en requests cross-site, mitigando CSRF en la mayoría de escenarios.
- **Secure** (en producción): la cookie solo viaja por HTTPS.
- **Path restringido:** el access token solo se envía en `/api/`, el refresh token solo en `/api/auth/`. Esto limita la superficie de exposición.

Se usa un esquema de **dos tokens**:
- `exo_access`: access token de corta duración (20 minutos). Enviado automáticamente en cada request a `/api/`.
- `exo_refresh`: refresh token de mayor duración (7 días). Solo enviado a `/api/auth/` para renovar el access token.

La **protección CSRF** se implementa con Double Submit Cookie: Django emite una cookie CSRF legible por JavaScript (no HttpOnly), y el frontend la lee e incluye como header en cada request mutante (POST, PATCH, DELETE). El backend valida que el valor del header coincida con la cookie.

## Alternativas consideradas

**localStorage:** más simple de implementar en el frontend, pero vulnerable a XSS. Cualquier script inyectado en la página puede leer y exfiltrar el token. Descartado por razones de seguridad.

**sessionStorage:** mismo vector de ataque que localStorage. Descartado.

**Cookies sin HttpOnly:** accesibles desde JavaScript, misma vulnerabilidad que localStorage. Sin beneficio. Descartado.

## Consecuencias

- El frontend no puede leer el token JWT directamente (esto es intencional: es la garantía de seguridad).
- El middleware CSRF de Django es obligatorio y está activo. Las requests mutantes desde el frontend deben incluir el header `X-CSRFToken`.
- En tests, el `APIClient` de DRF maneja cookies automáticamente.
- Las peticiones desde herramientas como curl o Postman requieren gestión manual de cookies y CSRF.
- La rotación automática de refresh tokens (con blacklist en PostgreSQL) protege contra reutilización de tokens comprometidos.
