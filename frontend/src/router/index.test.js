import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory } from 'vue-router'

vi.mock('../services/auth', () => ({
  authService: {
    getCurrentUser: vi.fn(),
    saveUser: vi.fn(),
  },
}))

import { authService } from '../services/auth'
import { createAppRouter } from './index'

describe('router auth guard', () => {
  beforeEach(() => {
    sessionStorage.clear()
    Object.defineProperty(window, 'localStorage', {
      value: {
        getItem: vi.fn(() => null),
        setItem: vi.fn(),
        removeItem: vi.fn(),
      },
      configurable: true,
    })
    vi.clearAllMocks()
  })

  it('redirects unauthenticated access to a protected route back to landing', async () => {
    authService.getCurrentUser.mockResolvedValue(null)

    const router = createAppRouter(createMemoryHistory())

    await router.push('/dashboard')
    await router.isReady()

    expect(router.currentRoute.value.fullPath).toBe('/')
    expect(authService.saveUser).not.toHaveBeenCalled()
  })
})
