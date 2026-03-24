# Router y guards de navegación

---

## Creación del router

```js
// src/router/index.js
export const createAppRouter = (history = createWebHistory()) => {
    const router = createRouter({ history, routes })
    return installAuthGuard(router)
}
```

El factory `createAppRouter` acepta un parámetro `history` para hacer el router testeable:
los tests pasan `createMemoryHistory()` en lugar del history del browser.

---

## Rutas

| Nombre | Path (es) | Path (en) | requiresAuth |
|---|---|---|---|
| `landing` | `/` | `/` | No |
| `login` | `/login` | `/login` | No |
| `accept_invite` | `/accept-invite` | `/accept-invite` | No |
| `forgot_password` | `/olvide-contrasena` | `/forgot-password` | No |
| `reset_password` | `/reset-password` | `/reset-password` | No |
| `waitlist` | `/lista-espera` | `/waitlist` | No |
| `philosophy` | `/filosofia` | `/philosophy` | No |
| `public_profile` | `/users/:nickname` | `/users/:nickname` | No |
| `dashboard` | `/dashboard` | `/dashboard` | Sí |
| `library` | `/biblioteca` | `/library` | Sí |
| `favorites` | `/favs` | `/favs` | Sí |
| `notes` | `/notas` | `/notes` | Sí |
| `discover` | `/descubrir` | `/discover` | Sí |
| `profile` | `/perfil` | `/profile` | Sí |
| `graph` | `/graph` | `/graph` | Sí |
| `thread` | `/hilos/:threadId` | `/threads/:threadId` | Sí |
| `waitlist_community` | `/red/comunidad` | `/network/community` | Sí |

Las rutas con dos paths (es/en) se registran con el path en español como canónico
y el path en inglés como alias. Ambos paths funcionan y respetan el guard.

---

## Guard de autenticación (`installAuthGuard`)

Se ejecuta en cada navegación (`router.beforeEach`). La lógica en orden:

### Para rutas que NO requieren auth

1. **Si es `/login` y el usuario ya está autenticado:** redirige al dashboard.
   Si tiene `must_change_credentials`, redirige a perfil.
2. **Normalización de locale:** si la URL actual está en un idioma distinto al preferido,
   redirige a la versión localizada correcta.
3. En cualquier otro caso: deja pasar.

### Para rutas que SÍ requieren auth

1. Llama a `authService.getCurrentUser()` para verificar sesión activa
   (hace un request a `/api/me/`; el backend valida la cookie JWT).
2. **Si no hay sesión:** limpia `sessionStorage` y redirige a `landing` (`/`).
3. **Si hay sesión y `must_change_credentials`:** fuerza redirección a perfil
   (el usuario debe cambiar su nickname/contraseña antes de poder navegar).
4. **Normalización de locale:** igual que en rutas públicas.
5. Deja pasar.

---

## Rutas localizadas

`localizedRoutes.js` define el mapa completo de paths por idioma en `LOCALIZED_ROUTE_PATHS`.

Las funciones auxiliares:

- `getStoredLocale()` — lee el idioma preferido de `localStorage`.
- `getLocalizedPath(routeName, locale, params, query, hash)` — construye el path localizado,
  interpolando parámetros dinámicos (`:nickname`, `:threadId`).
- `getRouteAliases(routeName, canonicalLocale)` — devuelve los paths alternativos para
  registrarlos como alias en Vue Router.

---

## Redirect legacy

```js
{
    path: '/highlights',
    redirect: () => getLocalizedPath('library', getStoredLocale()) || '/biblioteca'
}
```

Redirige paths antiguos (`/highlights`) a la ruta actual de la biblioteca.
