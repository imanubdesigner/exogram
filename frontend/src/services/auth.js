/**
 * Auth service para Exogram.
 *
 * Seguridad:
 * - Sesión JWT en cookies HttpOnly configuradas por backend.
 * - El frontend no persiste access/refresh tokens en storage.
 */
import { apiFetch, apiRequest, API_BASE } from './api'

export const authService = {
    /**
     * Login con nickname + password.
     * Backend setea cookies HttpOnly en la respuesta.
     */
    async login(nickname, password) {
        const response = await fetch(`${API_BASE}/auth/login/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ nickname, password })
        })

        if (!response.ok) {
            const error = await response.json()
            throw new Error(error.error || 'Error al iniciar sesión')
        }

        const data = await response.json()
        return data.user
    },

    async forgotPassword(email) {
        return apiRequest('/auth/forgot-password/', {
            method: 'POST',
            body: JSON.stringify({ email })
        })
    },

    async resetPassword(token, password, passwordConfirm) {
        return apiRequest('/auth/reset-password/', {
            method: 'POST',
            body: JSON.stringify({
                token,
                password,
                password_confirm: passwordConfirm
            })
        })
    },

    async acceptInvitation(token, username, password) {
        return apiRequest('/accounts/accept-invite/', {
            method: 'POST',
            body: JSON.stringify({
                token,
                username,
                password
            })
        })
    },

    /**
     * Valida un token de invitación (legacy/diagnóstico).
     */
    async validateInvitation(token) {
        return apiRequest(`/invitations/validate/${token}/`)
    },

    /**
     * Obtiene el perfil del usuario autenticado.
     */
    async getCurrentUser() {
        try {
            return await apiRequest('/me/')
        } catch {
            return null
        }
    },

    /**
     * Envía una invitación por email.
     */
    async sendInvitation(email) {
        return apiRequest('/invitations/send/', {
            method: 'POST',
            body: JSON.stringify({ email })
        })
    },

    /**
     * Obtiene lista de invitaciones enviadas.
     */
    async getMyInvitations() {
        return apiRequest('/invitations/')
    },

    /**
     * Obtiene estadísticas de invitaciones.
     */
    async getInvitationStats() {
        return apiRequest('/invitations/stats/')
    },

    /**
     * Obtiene una página de usuarios en la lista de espera de la comunidad.
     */
    async getCommunityWaitlist(page = 1, seed = null) {
        const params = new URLSearchParams()
        params.set('page', String(page))
        if (seed) params.set('seed', String(seed))
        return apiRequest(`/waitlist/community/?${params.toString()}`)
    },

    /**
     * Usa una invitación para activar un usuario de la lista de espera.
     */
    async activateWaitlistEntry(entryId) {
        return apiRequest(`/waitlist/${entryId}/activate/`, {
            method: 'POST'
        })
    },

    /**
     * Actualiza el perfil del usuario.
     */
    async updateProfile(data) {
        return apiRequest('/me/profile/', {
            method: 'PATCH',
            body: JSON.stringify(data)
        })
    },

    /**
     * Actualiza nickname + contraseña.
     */
    async updateCredentials(data) {
        return apiRequest('/me/credentials/update/', {
            method: 'POST',
            body: JSON.stringify(data)
        })
    },

    /**
     * Actualiza configuraciones de privacidad.
     */
    async updatePrivacy(data) {
        return apiRequest('/me/privacy/', {
            method: 'PATCH',
            body: JSON.stringify(data)
        })
    },

    /**
     * Actualiza preferencias de visualización (fuente y ancho).
     */
    async updateDisplay(data) {
        return apiRequest('/me/display/', {
            method: 'PATCH',
            body: JSON.stringify(data)
        })
    },

    /**
     * Activa sincronización Goodreads y encola worker.
     */
    async activateGoodreads(goodreadsUsername) {
        return apiRequest('/me/goodreads/activate/', {
            method: 'POST',
            body: JSON.stringify({ goodreads_username: goodreadsUsername })
        })
    },

    /**
     * Obtiene lista de libros en lectura desde sync Goodreads.
     */
    async getGoodreadsReading() {
        return apiRequest('/me/goodreads/reading/')
    },

    /**
     * Marca onboarding como completado.
     */
    async completeOnboarding() {
        return apiRequest('/me/onboarding/complete/', {
            method: 'POST'
        })
    },

    /**
     * Exporta todos los datos del usuario.
     */
    async exportData() {
        return apiRequest('/me/export/')
    },

    /**
     * Obtiene el árbol de red (nodos y arcos).
     */
    async getNetworkTree(options = {}) {
        const params = new URLSearchParams()

        if (Number.isFinite(options.maxDepth)) {
            params.set('max_depth', String(options.maxDepth))
        }
        if (Number.isFinite(options.maxNodes)) {
            params.set('max_nodes', String(options.maxNodes))
        }

        const query = params.toString()
        return apiRequest(`/me/network-tree/${query ? `?${query}` : ''}`)
    },

    /**
     * Obtiene actividad de highlights agrupados por día.
     */
    async getActivityHeatmap() {
        return apiRequest('/me/activity/')
    },

    /**
     * Exporta highlights en formato Obsidian (ZIP).
     */
    async exportObsidian() {
        const response = await apiFetch('/me/export/obsidian/')
        if (!response.ok) throw new Error('Error al exportar')
        return response.blob()
    },

    /**
     * Elimina permanentemente la cuenta del usuario autenticado.
     */
    async deleteAccount() {
        return apiRequest('/me/delete/', {
            method: 'DELETE',
            body: JSON.stringify({ confirm: 'DELETE_MY_ACCOUNT' })
        })
    },

    /**
     * Persiste flags de sesión no sensibles.
     */
    saveUser(user) {
        if (user?.must_change_credentials) {
            sessionStorage.setItem('must_change_credentials', '1')
        } else {
            sessionStorage.removeItem('must_change_credentials')
        }
        sessionStorage.setItem('auth_hint', '1')
    },

    /**
     * Cierra sesión server-side y limpia flags locales.
     */
    async logout() {
        try {
            await apiFetch('/auth/logout/', {
                method: 'POST',
                body: JSON.stringify({})
            })
        } catch {
            // Ignorar error de red y limpiar estado local igualmente.
        }
        sessionStorage.removeItem('must_change_credentials')
        sessionStorage.removeItem('auth_hint')
        window.location.href = '/'
    },

    /**
     * Hint local para navegación. No representa un token real.
     */
    isAuthenticated() {
        return sessionStorage.getItem('auth_hint') === '1'
    }
}
