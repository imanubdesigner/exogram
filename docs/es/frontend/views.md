# Vistas

Una vista por ruta. Todas se cargan de forma lazy (`() => import(...)`) para reducir
el bundle inicial. Las vistas con `requiresAuth: true` no son accesibles sin sesión activa.

---

## Vistas públicas

### `LandingPage.vue`
Página de bienvenida. Presenta el proyecto, sus valores y el sistema de invitación.
Links a registro (lista de espera), login y contenido de filosofía.
No requiere sesión.

### `Login.vue`
Formulario de login con nickname y contraseña.
Si el usuario ya tiene sesión (detectado por el guard), redirige al dashboard.
Link a recuperación de contraseña.

### `AcceptInvite.vue`
Flujo de registro con token de invitación.
1. Lee el token de la URL, llama a `validateInvitation(token)`.
2. Si el token es válido, muestra el formulario de registro (nickname, password).
3. Si expiró o no existe, muestra error.

### `ForgotPassword.vue` / `ResetPassword.vue`
Dos pasos del flujo de reset de contraseña:
- `ForgotPassword`: formulario de email → llama a `POST /api/auth/password-reset/`.
- `ResetPassword`: lee el token de la URL, formulario de nueva contraseña.

### `Waitlist.vue`
Formulario para anotarse en la lista de espera. Campos: email, mensaje opcional.

### `Philosophy.vue`
Muestra artículos del proyecto (filosofía, manifiesto). Consume la app `articles` del backend.
Acepta un parámetro opcional `articleId` para mostrar un artículo específico.

### `PublicProfile.vue`
Perfil público de un usuario (por nickname). Muestra highlights públicos, notas públicas y bio.
Si el usuario tiene hermit mode activo, el backend devuelve 404 y la vista lo gestiona.

---

## Vistas autenticadas

### `Dashboard.vue`
Vista principal post-login. Resumen de actividad: últimos highlights, actividad de la red,
heatmap de lectura. Punto de entrada a las demás secciones.

### `Library.vue`
Biblioteca personal. Lista de highlights con filtros (libro, favoritos, visibilidad).
La ruta `/favs` también usa este componente, pre-filtrado por `is_favorite=true`.
Desde aquí se puede editar la nota, cambiar visibilidad y marcar/desmarcar como favorito.

### `Notes.vue`
Vista enfocada en highlights con nota personal. Muestra el contenido del highlight
junto a la nota del usuario. Filtrado por highlights que tienen nota no vacía.

### `Import.vue`
Flujo de importación de highlights.
1. El usuario sube un archivo (Kindle `.txt` o Goodreads `.csv`).
2. Se muestra una previsualización de los highlights detectados.
3. Al confirmar, se envía a `/api/books/import/` y se disparan las tareas de embedding.

### `Discover.vue`
Búsqueda semántica y descubrimiento de lectores afines.
- Campo de búsqueda → query de similitud vectorial en los propios highlights o en la red.
- Lista de usuarios con afinidad lectora similar.
- Sugerencias de libros en común con otros lectores.

### `Profile.vue`
Perfil propio del usuario autenticado.
- Ver y editar nickname, bio, avatar.
- Configuración de privacidad (hermit mode, is_discoverable).
- Lista de invitaciones enviadas y stats.
- Export de datos personales.
- Onboarding flow si es el primer acceso.

### `Graph.vue`
Visualización del grafo de red del usuario.
Muestra los nodos (usuarios) y aristas (conexiones por invitación / afinidad).
Usa `v-network-graph` con layout de fuerza `d3-force`.
Consume `getNetworkTree()` del auth store.

### `ThreadView.vue`
Vista de un hilo de mensajes privados.
- Carga el hilo por ID y muestra el historial de mensajes.
- Formulario de respuesta en tiempo real.
- Paginación hacia atrás (cargar mensajes más antiguos) via el parámetro `before`.

### `CommunityWaitlist.vue`
Vista para que usuarios con invitaciones activen a personas de la lista de espera.
Lista los entries de la waitlist y permite activar uno a la vez consumiendo una invitación.
Solo accesible para usuarios con `invitations_remaining > 0`.
