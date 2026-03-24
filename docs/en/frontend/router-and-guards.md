# Router and Navigation Guards

---

## Router Creation

```js
// src/router/index.js
export const createAppRouter = (history = createWebHistory()) => {
    const router = createRouter({ history, routes })
    return installAuthGuard(router)
}
```

The `createAppRouter` factory accepts a `history` parameter to make the router testable:
tests pass `createMemoryHistory()` instead of the browser history.

---

## Routes

| Name | Path (es) | Path (en) | requiresAuth |
|---|---|---|---|
| `landing` | `/` | `/` | No |
| `login` | `/login` | `/login` | No |
| `accept_invite` | `/accept-invite` | `/accept-invite` | No |
| `forgot_password` | `/olvide-contrasena` | `/forgot-password` | No |
| `reset_password` | `/reset-password` | `/reset-password` | No |
| `waitlist` | `/lista-espera` | `/waitlist` | No |
| `philosophy` | `/filosofia` | `/philosophy` | No |
| `public_profile` | `/users/:nickname` | `/users/:nickname` | No |
| `dashboard` | `/dashboard` | `/dashboard` | Yes |
| `library` | `/biblioteca` | `/library` | Yes |
| `favorites` | `/favs` | `/favs` | Yes |
| `notes` | `/notas` | `/notes` | Yes |
| `discover` | `/descubrir` | `/discover` | Yes |
| `profile` | `/perfil` | `/profile` | Yes |
| `graph` | `/graph` | `/graph` | Yes |
| `thread` | `/hilos/:threadId` | `/threads/:threadId` | Yes |
| `waitlist_community` | `/red/comunidad` | `/network/community` | Yes |

Routes with two paths (es/en) are registered with the Spanish path as canonical
and the English path as an alias. Both paths work and respect the guard.

---

## Authentication Guard (`installAuthGuard`)

Runs on every navigation (`router.beforeEach`). Logic in order:

### For routes that do NOT require auth

1. **If the route is `/login` and the user is already authenticated:** redirects to dashboard.
   If they have `must_change_credentials`, redirects to profile.
2. **Locale normalization:** if the current URL is in a different locale than the preferred one,
   redirects to the correct localized version.
3. In any other case: lets the navigation through.

### For routes that DO require auth

1. Calls `authService.getCurrentUser()` to verify an active session
   (makes a request to `/api/me/`; the backend validates the JWT cookie).
2. **If there is no session:** clears `sessionStorage` and redirects to `landing` (`/`).
3. **If there is a session and `must_change_credentials`:** forces a redirect to profile
   (the user must change their nickname/password before navigating further).
4. **Locale normalization:** same as for public routes.
5. Lets the navigation through.

---

## Localized Routes

`localizedRoutes.js` defines the full map of paths by locale in `LOCALIZED_ROUTE_PATHS`.

Helper functions:

- `getStoredLocale()` — reads the preferred locale from `localStorage`.
- `getLocalizedPath(routeName, locale, params, query, hash)` — builds the localized path,
  interpolating dynamic parameters (`:nickname`, `:threadId`).
- `getRouteAliases(routeName, canonicalLocale)` — returns the alternative paths to
  register as aliases in Vue Router.

---

## Legacy Redirect

```js
{
    path: '/highlights',
    redirect: () => getLocalizedPath('library', getStoredLocale()) || '/biblioteca'
}
```

Redirects legacy paths (`/highlights`) to the current library route.
