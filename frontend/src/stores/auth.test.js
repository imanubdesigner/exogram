import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('../services/auth', () => ({
  authService: {
    login: vi.fn(),
    logout: vi.fn(),
    getCurrentUser: vi.fn(),
    saveUser: vi.fn(),
    sendInvitation: vi.fn(),
    validateInvitation: vi.fn(),
    getMyInvitations: vi.fn(),
    getInvitationStats: vi.fn(),
    updateProfile: vi.fn(),
    updatePrivacy: vi.fn(),
    completeOnboarding: vi.fn(),
    exportData: vi.fn(),
    getNetworkTree: vi.fn(),
    getActivityHeatmap: vi.fn(),
  },
}))

import { authService } from '../services/auth'
import { useAuthStore } from './auth'

describe('auth store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    sessionStorage.clear()
    vi.clearAllMocks()
  })

  it('sets auth state on login', async () => {
    authService.login.mockResolvedValue({ nickname: 'reader' })

    const store = useAuthStore()
    await store.login('reader', 'secretpass')

    expect(store.isAuthenticated).toBe(true)
    expect(store.user).toEqual({ nickname: 'reader' })
    expect(authService.saveUser).toHaveBeenCalledWith({ nickname: 'reader' })
  })

  it('clears auth state on logout', async () => {
    authService.logout.mockResolvedValue(undefined)

    const store = useAuthStore()
    store.user = { nickname: 'reader' }
    store.sentInvitations = [{ id: 1 }]
    store.invitationStats = { total_sent: 1 }
    sessionStorage.setItem('must_change_credentials', '1')

    await store.logout()

    expect(store.isAuthenticated).toBe(false)
    expect(store.sentInvitations).toEqual([])
    expect(store.invitationStats).toBeNull()
    expect(sessionStorage.getItem('must_change_credentials')).toBeNull()
    expect(authService.logout).toHaveBeenCalled()
  })
})
