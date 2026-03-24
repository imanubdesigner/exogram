# Autorización

Qué puede hacer cada tipo de usuario y cómo se aplican los controles.

---

## Niveles de acceso

### Anónimo (sin sesión)

Puede:
- Ver la landing, login, filosofía, lista de espera.
- Validar un token de invitación (`GET /api/invitations/validate/<token>/`).
- Registrarse con token de invitación (`POST /api/auth/register/`).
- Anotarse en la lista de espera (`POST /api/waitlist/`).
- Ver perfiles públicos de usuarios que no tienen hermit mode.
- Ver notas públicas de un usuario (`GET /api/books/public-notes/<nickname>/`).

No puede:
- Acceder a ningún endpoint que requiera `IsAuthenticated`.

### Usuario autenticado (depth=0, recién registrado)

Puede:
- Todo lo que puede el anónimo.
- Ver y editar su propio perfil, highlights, notas.
- Importar y exportar highlights.
- Ver su grafo de red y el feed de descubrimiento.
- Buscar por similitud semántica.
- Leer pero **no comentar** en highlights ajenos (restricción por trust level).

No puede (aún):
- Comentar en highlights de otros usuarios (requiere depth=1 o red compatible).
- Iniciar hilos privados con usuarios fuera de su red.

### Usuario establecido (depth=1, ≥30 días)

Puede todo lo anterior, más:
- Comentar en highlights de usuarios dentro de su red.
- Iniciar hilos privados con usuarios dentro de su red.

### Staff (`is_staff=True`)

Puede adicionalmente:
- Ver la lista completa de la waitlist (`GET /api/waitlist/`).
- Acceder al Django Admin (si conoce la URL configurada en `ADMIN_URL`).

### Superusuario (`is_superuser=True`)

Acceso completo al Django Admin. Gestión total de todas las entidades.

---

## Trust levels y distancia de red

El sistema de autorización para comentarios y mensajes privados no es solo por nivel
de confianza individual: también considera la **distancia en el grafo de red**.

`are_in_same_network(profile_a, profile_b)` verifica que la distancia entre los dos
perfiles en el grafo de invitaciones y follows esté dentro del límite permitido por
sus respectivos `comment_allowance_depth`.

Esto significa que un usuario con depth=1 puede comentar en highlights de usuarios
que están en su red, no en cualquier usuario de la plataforma.

---

## Hermit mode

Cuando `Profile.is_hermit_mode = True`:
- `GET /api/users/<nickname>/` devuelve 404 para cualquier usuario distinto al propietario.
- El perfil no aparece en resultados de descubrimiento ni en el grafo de otros.
- Los propios highlights y datos son accesibles normalmente para el usuario.

Esto permite a usuarios que quieren privacidad total mantenerse en la plataforma
sin ser visibles para el resto.

---

## `must_change_credentials`

Flag que se activa cuando un usuario necesita actualizar su nickname o contraseña
(por ejemplo, en el primer login después del registro).

Cuando está activo:
- El guard del router redirige al perfil en cada navegación.
- El usuario no puede ir a ninguna otra vista hasta completar el cambio.
- Una vez actualizado y `completeOnboarding()` llamado, el flag se limpia.

---

## Permisos en DRF

La configuración base en `settings.py`:

```python
'DEFAULT_PERMISSION_CLASSES': [
    'rest_framework.permissions.IsAuthenticatedOrReadOnly',
]
```

Endpoints de solo escritura (crear invitaciones, enviar mensajes) usan `IsAuthenticated` explícito.
Endpoints de staff usan `IsAdminUser`.
Endpoints públicos puros (health, waitlist POST, validar invitación) usan `AllowAny` explícito.
