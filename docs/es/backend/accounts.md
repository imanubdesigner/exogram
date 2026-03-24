# App: accounts

Gestiona todo lo relacionado con usuarios: registro, autenticación, perfil, invitaciones y lista de espera.

---

## Modelos

### `Profile`

Extiende el `User` de Django con campos propios de Exogram.
Se crea automáticamente con cada `User` vía señal `post_save`.

Campos relevantes:
- `nickname` — nombre público del usuario (único). También sincroniza con `User.username`.
- `bio` — descripción personal.
- `avatar` — imagen de perfil. Validada con magic bytes, re-codificada en el servidor para eliminar EXIF.
- `verified_email` — email verificado del usuario. Separado de `User.email`.
- `is_hermit_mode` — si está activo, el perfil no es visible públicamente. El usuario existe pero es invisible para otros. Se devuelve 404 a quienes consultan su perfil.
- `comment_allowance_depth` — trust level. `0` = usuario nuevo, `1` = promovido a los 30 días.
- `invitations_remaining` — cuántas invitaciones puede enviar aún.
- `trust_promoted_at` — timestamp de la última promoción automática.
- `created_at`

### `Invitation`

Invitación enviada por un usuario registrado a un email.

Campos:
- `email` — destinatario (único, no puede recibir dos invitaciones).
- `invited_by` → FK a `User`.
- `token_hash` — HMAC-SHA256 del token raw. El token raw nunca se almacena.
- `token_created_at` — timestamp de generación. La validación de 72h se calcula desde aquí.
- `expires_at` — expiración del acceso a la plataforma (30 días por defecto, configurable).
- `accepted_at` — timestamp del registro exitoso.
- `token` — UUID legacy (no usar en lógica nueva).

### `Waitlist`

Registro de interesados en unirse que aún no tienen invitación.

Campos:
- `email` (único)
- `message` — mensaje opcional del aspirante.
- `created_at`
- `activated_at` — timestamp si fue activado.
- `activated_by` → FK a `Profile` del usuario que lo activó.

Método `activate(activating_profile)`: marca la entrada como activa y descuenta una invitación del activador.

### `PasswordResetToken`

Token de un solo uso para restablecer contraseña.

Campos:
- `user` → FK a `User`.
- `token_hash` — HMAC-SHA256 del token raw.
- `expires_at` — TTL configurable via `PASSWORD_RESET_TOKEN_TTL_HOURS` (default: 2h).
- `used_at` — si no es null, el token ya fue consumido.

### Funciones de hash

```python
build_invitation_token_hash(raw_token) -> str
build_password_reset_token_hash(raw_token) -> str
```

Ambas usan `HMAC-SHA256` con `SECRET_KEY` como clave. Esto protege contra ataques de
rainbow table: sin la `SECRET_KEY`, un hash comprometido no puede revertirse al token original.

---

## Flujos principales

### Registro por invitación

1. Usuario A envía invitación a `email@ejemplo.com` → `POST /api/invitations/`
2. Sistema genera token raw (`secrets.token_urlsafe(32)`), almacena su hash HMAC.
3. Email con link `<FRONTEND_BASE_URL>/accept-invite/<raw_token>` enviado al destinatario.
4. Destinatario valida el token → `GET /api/invitations/validate/<token>/`
   - Devuelve `{valid: true, email: "..."}` si el token es válido y no expiró (< 72h).
   - Devuelve `{valid: false}` si expiró o no existe.
5. Destinatario completa el registro → `POST /api/auth/register/` con nickname, password y token.

### Login

`POST /api/auth/login/` con `nickname` y `password`.
- Si es correcto: emite cookies `exo_access` y `exo_refresh` (HttpOnly, SameSite=Lax).
- Devuelve datos del usuario.

El login se hace con **nickname**, no con email. Esto separa la identidad pública (nickname) de la privada (email).

### Refresh de token

`POST /api/auth/token/refresh/`
- Lee la cookie `exo_refresh`, valida y rota: emite nuevo `exo_access` y nuevo `exo_refresh`.
- El refresh token anterior queda en la blacklist de simplejwt (tabla en PostgreSQL).

### Logout

`POST /api/auth/logout/`
- Blacklistea el refresh token activo.
- Borra ambas cookies del cliente.

### Password reset

1. `POST /api/auth/password-reset/` con `email` → genera token, envía email.
2. `POST /api/auth/password-reset/confirm/` con `token`, `password`, `password_confirm` → cambia la contraseña.
- El token se invalida tras el uso (`used_at = now()`).
- Solo hay un token activo por usuario (los anteriores se eliminan antes de generar uno nuevo).

---

## Seguridad del avatar

La validación del avatar opera en dos capas:

1. **`validate_avatar`** (validador del modelo): verifica tamaño (máx 2 MB) y firma de bytes del archivo (magic bytes reales, no el Content-Type del cliente). SVG se rechaza explícitamente para evitar XSS embebido.

2. **Re-codificación con Pillow** (`accounts/image_utils.py`): tras la validación, el avatar se abre con `Image.open()` y se guarda nuevamente. Esto elimina cualquier metadata EXIF (incluidas coordenadas GPS) y neutraliza payloads maliciosos que Pillow pudiera haber ignorado al parsear pero que quedarían en el archivo binario.

---

## Endpoints

| Método | URL | Descripción |
|---|---|---|
| POST | `/api/auth/login/` | Login con nickname + password |
| POST | `/api/auth/logout/` | Logout, blacklistea refresh token |
| POST | `/api/auth/token/refresh/` | Renovar access token |
| GET | `/api/me/` | Datos del usuario autenticado |
| PATCH | `/api/me/profile/` | Actualizar perfil (bio, nickname, avatar) |
| GET | `/api/users/<nickname>/` | Perfil público (respeta hermit mode) |
| POST | `/api/waitlist/` | Anotarse en lista de espera |
| GET | `/api/waitlist/` | Listar waitlist (solo staff) |
| POST | `/api/invitations/` | Enviar invitación |
| GET | `/api/invitations/validate/<token>/` | Validar token de invitación |
| POST | `/api/auth/register/` | Registro con token de invitación |
| POST | `/api/auth/password-reset/` | Solicitar reset de contraseña |
| POST | `/api/auth/password-reset/confirm/` | Confirmar reset con token |

---

## Hermit mode

Cuando `Profile.is_hermit_mode = True`:
- `GET /api/users/<nickname>/` devuelve 404 a cualquier usuario que no sea el propio.
- El usuario no aparece en resultados de búsqueda ni descubrimiento.
- Sus propios datos siguen siendo accesibles para él mismo.

---

## Trust levels

| Nivel | `comment_allowance_depth` | Condición |
|---|---|---|
| Nuevo | 0 | Al registrarse |
| Establecido | 1 | ≥ 30 días de antigüedad, promovido por tarea Celery diaria |

La tarea `promote_trust_levels_task` (en `books/tasks.py`) corre diariamente y promueve
en bulk a todos los usuarios elegibles que no fueron promovidos manualmente.
