# Seguridad — Visión general

Mapa de los controles de seguridad implementados en Exogram.

---

## Superficie de ataque y controles

| Área | Riesgo | Control |
|---|---|---|
| Autenticación | Robo de token | JWT en HttpOnly cookies (no accesible desde JS) |
| Autenticación | CSRF | Double Submit Cookie + `CsrfViewMiddleware` |
| Autenticación | Fuerza bruta | Throttle `auth`: 20 requests/hora en login y registro |
| Autenticación | Replay de refresh token | Rotación + blacklist en PostgreSQL |
| Tokens de invitación | Rainbow table | HMAC-SHA256 con `SECRET_KEY` como clave |
| Tokens de reset | Tiempo infinito | TTL de 2 horas, invalidación tras uso |
| Avatar upload | XSS via SVG | Rechazo por magic bytes + re-codificación con Pillow |
| Avatar upload | Ejecución via Pillow | Re-encoding elimina payloads en metadata |
| Passwords | Velocidad de cracking | PBKDF2-SHA256 (Django default, iterations altas) |
| API | Enumeración de usuarios | Responses genéricas en endpoints de reset y login |
| API | Exposición de datos | Perfil oculto con hermit mode devuelve 404 |
| Infra | Exposición de puertos | DB y Redis en `127.0.0.1` en producción |
| Infra | RCE en contenedor | Usuario no-root (`appuser`, uid=1000) en Docker |
| Headers HTTP | Clickjacking | `X-Frame-Options: DENY` |
| Headers HTTP | MIME sniffing | `X-Content-Type-Options: nosniff` |
| Headers HTTP | XSS | CSP estricto en Caddy y Django middleware |
| Headers HTTP | HTTPS downgrade | HSTS con preload (cuando `FORCE_HTTPS=True`) |
| Admin Django | Enumeración | URL del admin configurable (`ADMIN_URL`) |
| Moderación | Contenido tóxico | Motor local de análisis de toxicidad |
| Código | Vulnerabilidades conocidas | `pip-audit` en CI |
| Código | Bugs de seguridad | `bandit` SAST en CI |

---

## Lo que está fuera del scope actual

- **Verificación de email**: el registro no requiere verificar el email. Esto es intencional para el MVP (el sistema de invitaciones ya actúa como filtro de calidad). Es un riesgo de account takeover si alguien invita a un email que no controla, pero el daño está acotado: el invitador conoce al invitado.
- **2FA / MFA**: no implementado. Camino natural si el proyecto crece.
- **Audit log**: las acciones se loguean (INFO/ERROR en los logs de Django) pero no hay un registro de auditoría persistente en base de datos.
- **Rate limiting en endpoints de lectura**: solo los endpoints de escritura y auth tienen throttle estricto. Los de lectura tienen el límite global de usuario (500/hora).

---

## Documentos relacionados

- [Autenticación en detalle](./authentication.md)
- [Autorización y trust levels](./authorization.md)
- [Herramientas de scanning en CI](./ci-scanning.md)
- [ADR 0001: JWT en cookies](../adr/0001-jwt-httponly-cookies.md)
