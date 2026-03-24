# Frontend — Visión general

SPA construida con Vue 3, Vite y Pinia. Se sirve como build estático en producción
(Caddy lo entrega desde `/srv/frontend/dist`). En desarrollo corre el dev server de Vite
con HMR y un proxy a `/api/*` → `backend:8000`.

---

## Stack

| Tecnología | Rol |
|---|---|
| Vue 3 (Composition API) | Framework reactivo, componentes Single File |
| Vite | Build tool y dev server |
| Pinia | State management |
| Vue Router | Routing client-side con guards |
| Vitest + jsdom | Tests unitarios |

---

## Estructura de `src/`

```
src/
├── main.js               ← Punto de entrada: monta la app, instala Pinia y Router
├── App.vue               ← Componente raíz
├── style.css             ← Estilos globales
│
├── router/
│   ├── index.js          ← Definición de rutas, guard de autenticación
│   └── localizedRoutes.js ← Paths por idioma (es/en), aliases
│
├── stores/
│   ├── auth.js           ← Sesión del usuario, invitaciones, perfil
│   ├── highlights.js     ← Biblioteca de highlights
│   ├── i18n.js           ← Internacionalización liviana (es/en)
│   └── ui.js             ← Toasts, modales, sidebar, loading states
│
├── services/
│   ├── api.js            ← Cliente HTTP base (apiFetch, apiRequest, auto-refresh)
│   ├── auth.js           ← Auth: login, logout, perfil, invitaciones
│   ├── highlights.js     ← CRUD de highlights
│   ├── feed.js           ← Feed de descubrimiento
│   └── social.js         ← Comentarios, follows
│
├── views/                ← Una vista por ruta
│   ├── LandingPage.vue
│   ├── Login.vue
│   ├── Dashboard.vue
│   ├── Library.vue
│   ├── Notes.vue
│   ├── Discover.vue
│   ├── Profile.vue
│   ├── PublicProfile.vue
│   ├── Graph.vue
│   ├── ThreadView.vue
│   ├── Import.vue
│   ├── AcceptInvite.vue
│   ├── ForgotPassword.vue
│   ├── ResetPassword.vue
│   ├── Philosophy.vue
│   ├── Waitlist.vue
│   └── CommunityWaitlist.vue
│
├── components/           ← Componentes reutilizables entre vistas
└── utils/
    └── logger.js         ← Wrapper de console (silencia logs en producción)
```

---

## Comunicación con el backend

El frontend usa la Fetch API nativa (sin Axios) a través del cliente centralizado `api.js`.

**Autenticación:** las cookies HttpOnly se envían automáticamente con `credentials: 'include'`.
El frontend nunca lee ni almacena el JWT. Solo lee la cookie `csrftoken` (no HttpOnly)
para incluirla como header `X-CSRFToken` en requests mutantes.

**Auto-refresh:** si un request devuelve 401, el cliente intenta refrescar el access token
con `/api/auth/token/refresh/` y reintenta el request original una vez. Si el refresh
también falla, se limpia la sesión local.

---

## Internacionalización

La app soporta español e inglés. No usa `vue-i18n`: la internacionalización está implementada
en el store `i18n.js` con un diccionario en memoria y el hook `t('clave')`.

El idioma se persiste en `localStorage` bajo la clave `exogram_locale`.
Las rutas tienen paths localizados: `/biblioteca` en español, `/library` en inglés
(con alias para que ambas funcionen independientemente).
