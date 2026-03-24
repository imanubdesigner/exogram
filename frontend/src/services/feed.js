/**
 * Servicio para el feed de descubrimiento, afinidad y hilos privados.
 *
 * Usa apiRequest/apiFetch de api.js (soporta JWT y auto-refresh automático).
 */
import { apiFetch, apiRequest } from './api'

export const feedService = {
    // ── Discovery & Affinity ──────────────────────────────────────────────────

    /** Feed semántico: highlights recientes de lectores afines */
    async getDiscoveryFeed(page = 1) {
        return apiRequest(`/discovery/feed/?page=${page}`)
    },

    /** Feed de mis seguidos */
    async getFollowingFeed(page = 1) {
        return apiRequest(`/discovery/feed/following/?page=${page}`)
    },

    /** Lista de mis seguidos */
    async getFollowingUsers() {
        return apiRequest(`/social/following/`)
    },

    /** Lectores con intereses similares (centroide pgvector) */
    async getSimilarReaders(limit = 5) {
        return apiRequest(`/affinity/similar-readers/?limit=${limit}`)
    },

    /** Otros lectores del mismo libro */
    async getAlsoReading(bookId) {
        try {
            return await apiRequest(`/affinity/also-reading/${bookId}/`)
        } catch (err) {
            // 404 = libro sin lectores registrados: respuesta vacía esperada
            if (err?.message?.includes('404')) return { readers: [], count: 0 }
            // Otros errores (red, 5xx): propagar para que el caller decida
            throw err
        }
    },

    // ── Threads (mini-foro privado) ───────────────────────────────────────────

    /** Lista mis hilos */
    async getThreads() {
        return apiRequest('/threads/')
    },

    /** Crea un hilo con otro usuario */
    async createThread(otherNickname, contextBookTitle = '') {
        return apiRequest('/threads/', {
            method: 'POST',
            body: JSON.stringify({
                other_nickname: otherNickname,
                context_book_title: contextBookTitle,
            }),
        })
    },

    /** Detalle de un hilo con mensajes */
    async getThread(threadId, beforeId = null, signal = null) {
        const qs = beforeId ? `?before=${beforeId}` : ''
        const options = signal ? { signal } : {}
        const response = await apiFetch(`/threads/${threadId}/${qs}`, options)
        const data = await response.json().catch(() => ({}))
        if (!response.ok) {
            const error = new Error(data.error || data.detail || `Error ${response.status}`)
            error.status = response.status
            throw error
        }
        return data
    },

    /** Envía un mensaje a un hilo */
    async sendMessage(threadId, content) {
        return apiRequest(`/threads/${threadId}/messages/`, {
            method: 'POST',
            body: JSON.stringify({ content }),
        })
    },

    // ── Waitlist ──────────────────────────────────────────────────────────────

    /** Anotar email en la lista de espera (público, sin auth) */
    async joinWaitlist(email, message = '') {
        const res = await apiFetch('/waitlist/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, message }),
        })
        const data = await res.json()
        if (!res.ok) throw new Error(data.error || 'Error al anotarse')
        return data
    },

}
