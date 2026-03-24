# Services

Capa de acceso a la API. Cada service agrupa los requests relacionados a un dominio.
Todos usan las funciones `apiFetch` y `apiRequest` de `api.js`.

---

## `api.js` — Cliente base

El núcleo de la comunicación con el backend. Todo request pasa por aquí.

### `resolveApiBase(baseUrl?)`

Construye la URL base de la API:
- Si `VITE_API_URL` está definido en build time: `<VITE_API_URL>/api`
- Si no: `http://localhost:8000/api`

### `apiFetch(path, options)`

Wrapper sobre `fetch` con:
1. **`credentials: 'include'`** en todos los requests — envía cookies automáticamente.
2. **Header `X-CSRFToken`** en requests mutantes (POST, PUT, PATCH, DELETE) — lee la cookie
   `csrftoken` (no HttpOnly) y la incluye como header. Implementa Double Submit Cookie.
3. **Auto-refresh en 401** — si el request falla por sesión expirada, llama a
   `/api/auth/token/refresh/` y reintenta el request original una vez.
   No entra en bucle: el propio endpoint de refresh y el de login están excluidos del retry.
4. **`Content-Type: application/json`** por defecto, excepto cuando el body es `FormData`
   (en ese caso el browser pone el boundary correcto).

### `apiRequest(path, options)`

Wrapper sobre `apiFetch` que además parsea JSON y lanza un `Error` si `response.ok` es false.
Devuelve `null` en respuestas 204 No Content.

La mayoría de los services usan `apiRequest`. `apiFetch` se usa cuando se necesita
acceso directo a la `Response` (por ejemplo, para descargas binarias).

---

## `auth.js` — Autenticación y perfil

| Función | Endpoint | Descripción |
|---|---|---|
| `login(nickname, password)` | `POST /auth/login/` | Login. Devuelve datos del usuario. |
| `logout()` | `POST /auth/logout/` | Logout. Blacklistea el refresh token. |
| `getCurrentUser()` | `GET /me/` | Verifica sesión y devuelve datos del usuario o `null`. |
| `saveUser(user)` | — | Guarda `auth_hint` en sessionStorage (hint para el guard). |
| `sendInvitation(email)` | `POST /invitations/` | Envía invitación. |
| `validateInvitation(token)` | `GET /invitations/validate/<token>/` | Valida token. |
| `getMyInvitations()` | `GET /invitations/` | Lista mis invitaciones. |
| `getInvitationStats()` | `GET /invitations/stats/` | Stats de invitaciones. |
| `updateProfile(data)` | `PATCH /me/profile/` | Actualiza perfil (multipart si hay avatar). |
| `updatePrivacy(settings)` | `PATCH /me/privacy/` | Actualiza configuración de privacidad. |
| `completeOnboarding()` | `POST /me/onboarding/` | Marca onboarding completado. |
| `exportData()` | `GET /me/export/` | Exporta datos del usuario. |
| `getNetworkTree()` | `GET /affinity/graph/` | Grafo de red. |
| `getActivityHeatmap()` | `GET /me/activity/` | Heatmap de actividad. |

### Manejo de avatar en `updateProfile`

Si `profileData` contiene un campo `avatar` (File object), el service construye
un `FormData` en lugar de enviar JSON. Esto es necesario para subir binarios.
El resto de campos del perfil se incluyen en el mismo FormData.

---

## `highlights.js` — Biblioteca

| Función | Endpoint | Descripción |
|---|---|---|
| `fetchHighlights(params?)` | `GET /highlights/` | Lista highlights con filtros opcionales. |
| `updateHighlight(id, data)` | `PATCH /highlights/<id>/` | Actualiza nota, visibilidad, favorito. |
| `deleteHighlight(id)` | `DELETE /highlights/<id>/` | Elimina highlight. |
| `importHighlights(file, format)` | `POST /books/import/` | Importa archivo Kindle o Goodreads. |
| `exportHighlights(format?)` | `GET /books/export/` | Exporta highlights. |

---

## `feed.js` — Descubrimiento

| Función | Endpoint | Descripción |
|---|---|---|
| `searchHighlights(query, scope, limit)` | `POST /discovery/search/` | Búsqueda semántica. |
| `getSimilarUsers()` | `GET /discovery/users/` | Usuarios con afinidad similar. |

---

## `social.js` — Social

| Función | Endpoint | Descripción |
|---|---|---|
| `getComments(highlightId)` | `GET /highlights/<id>/comments/` | Comentarios de un highlight. |
| `postComment(highlightId, content)` | `POST /highlights/<id>/comments/` | Crear comentario. |
| `deleteComment(commentId)` | `DELETE /comments/<id>/` | Borrar comentario propio. |
| `followUser(nickname)` | `POST /users/<nickname>/follow/` | Seguir usuario. |
| `unfollowUser(nickname)` | `DELETE /users/<nickname>/follow/` | Dejar de seguir. |
