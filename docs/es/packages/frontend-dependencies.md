# Dependencias del frontend

Referencia de los paquetes en `frontend/package.json`.

---

## Dependencias de producción

| Paquete | Propósito |
|---|---|
| `vue` | Framework reactivo. Composition API. |
| `vue-router` | Routing client-side con guards de navegación para autenticación. |
| `pinia` | State management. Reemplaza Vuex. API más simple y compatible con TypeScript sin configuración extra. |

## Dependencias de desarrollo / build

| Paquete | Propósito |
|---|---|
| `vite` | Build tool y dev server con HMR. Ordenes de magnitud más rápido que webpack. |
| `@vitejs/plugin-vue` | Plugin de Vite para compilar Single File Components (`.vue`). |
| `vitest` | Test runner compatible con la API de Vite. Usa el mismo pipeline de transformación que el build, sin configuración extra. |
| `@vue/test-utils` | Utilidades para montar y testear componentes Vue en vitest. |
| `jsdom` | Simulación del DOM del navegador para tests en Node.js (environment de vitest). |

---

## Scripts npm

| Script | Comando | Descripción |
|---|---|---|
| `dev` | `vite` | Dev server en puerto 5173 con HMR y proxy a `/api/*` → backend. |
| `build` | `vite build` | Build de producción en `dist/`. Minificado, tree-shaken. |
| `test` | `vitest run` | Corre los tests una vez (sin watch). Usado en CI. |
| `preview` | `vite preview` | Sirve el build de producción localmente para verificar antes de deploy. |

---

## Proxy en desarrollo

`vite.config.js` configura un proxy para que el dev server enrute `/api/*` al backend:

```js
proxy: {
  '/api': {
    target: 'http://backend:8000',
    changeOrigin: true,
  }
}
```

Dentro de Docker Compose, `backend` resuelve al contenedor Django.
Fuera de Docker, cambiar el target a `http://localhost:8000`.

---

## Auditoría de seguridad

El CI corre `npm audit --audit-level=high` antes del build.
Si hay vulnerabilidades HIGH o CRITICAL en las dependencias, el job falla.

Para actualizar dependencias con vulnerabilidades:

```bash
npm audit fix          # actualiza automáticamente si hay fix disponible
npm audit fix --force  # fuerza actualizaciones breaking (revisar manualmente)
```
