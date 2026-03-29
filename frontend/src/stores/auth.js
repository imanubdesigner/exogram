/**
 * Auth Store - Gestiona autenticación y datos del usuario
 * Responsabilidades:
 * - Login/logout
 * - Sesión por cookies HttpOnly (sin tokens en storage)
 * - Datos del perfil del usuario
 * - Estado de autenticación
 * - Invitaciones (enviar, validar)
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authService } from '../services/auth'
import { logger } from '../utils/logger'

export const useAuthStore = defineStore('auth', () => {
  // State
  const user = ref(null)
  const isLoadingAuth = ref(false)
  const authError = ref(null)
  const isLoadingInvitation = ref(false)
  const invitationError = ref(null)
  const sentInvitations = ref([])
  const invitationStats = ref(null)

  // Computed
  const isAuthenticated = computed(() => !!user.value)
  const userName = computed(() => user.value?.nickname || '')
  const isHermitMode = computed(() => user.value?.is_hermit_mode || false)

  // Actions
  const login = async (nickname, password) => {
    isLoadingAuth.value = true
    authError.value = null
    try {
      const userData = await authService.login(nickname, password)
      user.value = userData
      authService.saveUser(userData)
      return userData
    } catch (error) {
      authError.value = error.message
      throw error
    } finally {
      isLoadingAuth.value = false
    }
  }

  const logout = async () => {
    user.value = null
    authError.value = null
    sentInvitations.value = []
    invitationStats.value = null
    sessionStorage.removeItem('must_change_credentials')
    await authService.logout()
  }

  const refreshCurrentUser = async () => {
    try {
      const userData = await authService.getCurrentUser()
      if (userData) {
        const mergedUser = { ...(user.value || {}), ...userData }
        if (
          typeof userData.is_discoverable !== 'boolean' &&
          typeof user.value?.is_discoverable === 'boolean'
        ) {
          mergedUser.is_discoverable = user.value.is_discoverable
        }
        user.value = mergedUser
        authService.saveUser(userData)
        applyDisplayPreferences(userData.font_scale, userData.content_max_width)
      } else {
        user.value = null
        sessionStorage.removeItem('auth_hint')
        sessionStorage.removeItem('must_change_credentials')
      }
      return userData
    } catch (error) {
      logger.error('Error refreshing user:', error)
      user.value = null
      sessionStorage.removeItem('auth_hint')
      sessionStorage.removeItem('must_change_credentials')
      return null
    }
  }

  const sendInvitation = async (email) => {
    isLoadingInvitation.value = true
    invitationError.value = null
    try {
      const result = await authService.sendInvitation(email)
      // Refrescar stats después de enviar
      await fetchInvitationStats()
      return result
    } catch (error) {
      invitationError.value = error.message
      throw error
    } finally {
      isLoadingInvitation.value = false
    }
  }

  const validateInvitation = async (token) => {
    try {
      const result = await authService.validateInvitation(token)
      return result
    } catch (error) {
      invitationError.value = error.message
      throw error
    }
  }

  const fetchMyInvitations = async () => {
    isLoadingInvitation.value = true
    invitationError.value = null
    try {
      const invitations = await authService.getMyInvitations()
      sentInvitations.value = invitations
      return invitations
    } catch (error) {
      invitationError.value = error.message
      throw error
    } finally {
      isLoadingInvitation.value = false
    }
  }

  const fetchInvitationStats = async () => {
    try {
      const stats = await authService.getInvitationStats()
      invitationStats.value = stats
      return stats
    } catch (error) {
      logger.error('Error fetching invitation stats:', error)
      throw error
    }
  }

  const updateProfile = async (profileData) => {
    try {
      const updated = await authService.updateProfile(profileData)
      user.value = { ...user.value, ...updated }
      return updated
    } catch (error) {
      authError.value = error.message
      throw error
    }
  }

  const updatePrivacy = async (privacySettings) => {
    try {
      const updated = await authService.updatePrivacy(privacySettings)
      user.value = { ...user.value, ...updated }
      return updated
    } catch (error) {
      authError.value = error.message
      throw error
    }
  }

  const updateDisplay = async (displayPreferences) => {
    try {
      const updated = await authService.updateDisplay(displayPreferences)
      user.value = { ...user.value, ...updated }
      applyDisplayPreferences(updated.font_scale, updated.content_max_width)
      return updated
    } catch (error) {
      authError.value = error.message
      throw error
    }
  }

  const applyDisplayPreferences = (fontScale, contentMaxWidth) => {
    const scale = fontScale ?? 1.0
    const width = contentMaxWidth ?? 640
    document.documentElement.style.fontSize = `${16 * scale}px`
    document.documentElement.style.setProperty('--max-width-content', `${width}px`)
  }

  const completeOnboarding = async () => {
    try {
      await authService.completeOnboarding()
      if (user.value) {
        user.value.onboarding_completed = true
      }
    } catch (error) {
      logger.error('Error completing onboarding:', error)
      throw error
    }
  }

  const exportData = async () => {
    try {
      return await authService.exportData()
    } catch (error) {
      authError.value = error.message
      throw error
    }
  }

  const getNetworkTree = async () => {
    try {
      return await authService.getNetworkTree()
    } catch (error) {
      authError.value = error.message
      throw error
    }
  }

  const getActivityHeatmap = async () => {
    try {
      return await authService.getActivityHeatmap()
    } catch (error) {
      logger.error('Error fetching activity:', error)
      throw error
    }
  }

  return {
    // State
    user,
    isLoadingAuth,
    authError,
    isLoadingInvitation,
    invitationError,
    sentInvitations,
    invitationStats,

    // Computed
    isAuthenticated,
    userName,
    isHermitMode,

    // Methods
    login,
    logout,
    refreshCurrentUser,
    sendInvitation,
    validateInvitation,
    fetchMyInvitations,
    fetchInvitationStats,
    updateProfile,
    updatePrivacy,
    updateDisplay,
    applyDisplayPreferences,
    completeOnboarding,
    exportData,
    getNetworkTree,
    getActivityHeatmap,
  }
})
