# Frontend dependencies

Reference for the packages in `frontend/package.json`.

---

## Production dependencies

| Package | Purpose |
|---|---|
| `vue` | Reactive framework. Composition API. |
| `vue-router` | Client-side routing with navigation guards for authentication. |
| `pinia` | State management. Replaces Vuex. Simpler API, TypeScript-compatible without extra configuration. |

## Development / build dependencies

| Package | Purpose |
|---|---|
| `vite` | Build tool and dev server with HMR. Orders of magnitude faster than webpack. |
| `@vitejs/plugin-vue` | Vite plugin for compiling Single File Components (`.vue`). |
| `vitest` | Test runner compatible with the Vite API. Uses the same transformation pipeline as the build, without extra configuration. |
| `@vue/test-utils` | Utilities for mounting and testing Vue components in vitest. |
| `jsdom` | Browser DOM simulation for tests in Node.js (vitest environment). |

---

## npm scripts

| Script | Command | Description |
|---|---|---|
| `dev` | `vite` | Dev server on port 5173 with HMR and proxy to `/api/*` → backend. |
| `build` | `vite build` | Production build in `dist/`. Minified, tree-shaken. |
| `test` | `vitest run` | Runs tests once (no watch). Used in CI. |
| `preview` | `vite preview` | Serves the production build locally for verification before deploy. |

---

## Development proxy

`vite.config.js` configures a proxy so the dev server routes `/api/*` to the backend:

```js
proxy: {
  '/api': {
    target: 'http://backend:8000',
    changeOrigin: true,
  }
}
```

Inside Docker Compose, `backend` resolves to the Django container.
Outside Docker, change the target to `http://localhost:8000`.

---

## Security audit

CI runs `npm audit --audit-level=high` before the build.
If there are HIGH or CRITICAL vulnerabilities in the dependencies, the job fails.

To update dependencies with vulnerabilities:

```bash
npm audit fix          # automatically updates if a fix is available
npm audit fix --force  # forces breaking updates (review manually)
```
