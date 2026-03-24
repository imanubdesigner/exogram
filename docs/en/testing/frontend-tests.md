# Frontend Tests

---

## Running the Tests

```bash
# From the host (with Docker)
docker compose exec frontend npm test

# From frontend/ directly
cd frontend
npm test          # single pass (CI mode)
npx vitest        # watch mode (development)
```

---

## Testing Stack

| Tool | Role |
|---|---|
| **Vitest** | Test runner. Same transformation pipeline as Vite: no extra configuration for `.vue` imports. |
| **jsdom** | Simulates the browser DOM in Node.js. Configured as `environment` in `vitest.config.js`. |
| `@vue/test-utils` | For component tests (if added). |

---

## Existing Tests

### `src/stores/auth.test.js`

Tests the auth store with the auth service completely mocked.

| Test | What it verifies |
|---|---|
| `sets auth state on login` | After `store.login()`, `isAuthenticated` is `true`, `user` has the data, `saveUser` was called. |
| `clears auth state on logout` | After `store.logout()`, `isAuthenticated` is `false`, `sentInvitations` is empty, `invitationStats` is null, the sessionStorage item was removed. |

### `src/services/api.test.js`

Tests the `resolveApiBase` function in isolation (without fetch or DOM).

| Test | What it verifies |
|---|---|
| `uses the configured env base url` | With a configured base URL, returns `<url>/api`. |
| `falls back to localhost when no env value is set` | With an empty string, returns `http://localhost:8000/api`. |

### `src/router/index.test.js`

Tests the router's authentication guard.

| Test | What it verifies |
|---|---|
| `redirects unauthenticated access to a protected route back to landing` | If `getCurrentUser` returns `null` and navigating to `/dashboard`, the router redirects to `/`. `saveUser` was not called. |

---

## Mocking Conventions

Tests fully mock the `../services/auth` service with `vi.mock()`:

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

This isolates the store from the real service and avoids HTTP requests in tests.
Each test configures the expected return value with `.mockResolvedValue(...)`.

---

## Adding New Tests

To add tests for a store or service:

```js
// src/stores/highlights.test.js
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('../services/highlights', () => ({
  // mock of the required methods
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

For Vue component tests, use `@vue/test-utils`:

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
