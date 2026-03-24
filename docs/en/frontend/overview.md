# Frontend — Overview

SPA built with Vue 3, Vite, and Pinia. Served as a static build in production
(Caddy delivers it from `/srv/frontend/dist`). In development, the Vite dev server runs
with HMR and a proxy for `/api/*` → `backend:8000`.

---

## Stack

| Technology | Role |
|---|---|
| Vue 3 (Composition API) | Reactive framework, Single File components |
| Vite | Build tool and dev server |
| Pinia | State management |
| Vue Router | Client-side routing with guards |
| Vitest + jsdom | Unit tests |

---

## `src/` Structure

```
src/
├── main.js               ← Entry point: mounts the app, installs Pinia and Router
├── App.vue               ← Root component
├── style.css             ← Global styles
│
├── router/
│   ├── index.js          ← Route definitions, authentication guard
│   └── localizedRoutes.js ← Paths by locale (es/en), aliases
│
├── stores/
│   ├── auth.js           ← User session, invitations, profile
│   ├── highlights.js     ← Highlights library
│   ├── i18n.js           ← Lightweight internationalization (es/en)
│   └── ui.js             ← Toasts, modals, sidebar, loading states
│
├── services/
│   ├── api.js            ← Base HTTP client (apiFetch, apiRequest, auto-refresh)
│   ├── auth.js           ← Auth: login, logout, profile, invitations
│   ├── highlights.js     ← Highlights CRUD
│   ├── feed.js           ← Discovery feed
│   └── social.js         ← Comments, follows
│
├── views/                ← One view per route
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
├── components/           ← Reusable components shared across views
└── utils/
    └── logger.js         ← console wrapper (silences logs in production)
```

---

## Backend Communication

The frontend uses the native Fetch API (no Axios) through the centralized `api.js` client.

**Authentication:** HttpOnly cookies are sent automatically with `credentials: 'include'`.
The frontend never reads or stores the JWT. It only reads the `csrftoken` cookie (non-HttpOnly)
to include it as the `X-CSRFToken` header on mutating requests.

**Auto-refresh:** if a request returns 401, the client attempts to refresh the access token
via `/api/auth/token/refresh/` and retries the original request once. If the refresh
also fails, the local session is cleared.

---

## Internationalization

The app supports Spanish and English. It does not use `vue-i18n`: internationalization is implemented
in the `i18n.js` store with an in-memory dictionary and the `t('key')` hook.

The locale is persisted in `localStorage` under the key `exogram_locale`.
Routes have localized paths: `/biblioteca` in Spanish, `/library` in English
(with aliases so both work independently).
