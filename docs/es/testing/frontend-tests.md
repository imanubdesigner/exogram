# Tests del frontend

---

## Ejecutar los tests

```bash
# Desde el host (con Docker)
docker compose exec frontend npm test

# Desde frontend/ directamente
cd frontend
npm test          # una sola pasada (modo CI)
npx vitest        # modo watch (desarrollo)
```

---

## Stack de testing

| Herramienta | Rol |
|---|---|
| **Vitest** | Test runner. Mismo pipeline de transformación que Vite: sin configuración extra para imports de `.vue`. |
| **jsdom** | Simula el DOM del navegador en Node.js. Configurado como `environment` en `vitest.config.js`. |
| `@vue/test-utils` | Para tests de componentes (si se agregan). |

---

## Tests existentes

### `src/stores/auth.test.js`

Testa el auth store con el servicio de auth completamente mockeado.

| Test | Qué verifica |
|---|---|
| `sets auth state on login` | Después de `store.login()`, `isAuthenticated` es `true`, `user` tiene los datos, `saveUser` fue llamado. |
| `clears auth state on logout` | Después de `store.logout()`, `isAuthenticated` es `false`, `sentInvitations` está vacío, `invitationStats` es null, el item de sessionStorage fue removido. |

### `src/services/api.test.js`

Testa la función `resolveApiBase` de forma aislada (sin fetch ni DOM).

| Test | Qué verifica |
|---|---|
| `uses the configured env base url` | Con una URL base configurada, devuelve `<url>/api`. |
| `falls back to localhost when no env value is set` | Con string vacío, devuelve `http://localhost:8000/api`. |

### `src/router/index.test.js`

Testa el guard de autenticación del router.

| Test | Qué verifica |
|---|---|
| `redirects unauthenticated access to a protected route back to landing` | Si `getCurrentUser` devuelve `null` y se navega a `/dashboard`, el router redirige a `/`. `saveUser` no fue llamado. |

---

## Convenciones de mocking

Los tests mockean completamente el servicio `../services/auth` con `vi.mock()`:

```js
vi.mock('../services/auth', () => ({
  authService: {
    login: vi.fn(),
    logout: vi.fn(),
    getCurrentUser: vi.fn(),
    // ...
  },
}))
```

Esto aísla el store del servicio real y evita requests HTTP en los tests.
Cada test configura el retorno esperado con `.mockResolvedValue(...)`.

---

## Agregar tests nuevos

Para agregar tests de un store o service:

```js
// src/stores/highlights.test.js
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('../services/highlights', () => ({
  // mock de los métodos necesarios
}))

import { useHighlightsStore } from './highlights'

describe('highlights store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('fetches highlights', async () => {
    // ...
  })
})
```

Para tests de componentes Vue, usar `@vue/test-utils`:

```js
import { mount } from '@vue/test-utils'
import MiComponente from '../components/MiComponente.vue'

it('renders correctly', () => {
  const wrapper = mount(MiComponente, {
    props: { title: 'Test' }
  })
  expect(wrapper.text()).toContain('Test')
})
```
