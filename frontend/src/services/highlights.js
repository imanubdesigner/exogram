/**
 * Highlight API service para Exogram.
 * Usa el API client centralizado.
 */
import { apiFetch, apiRequest } from './api'

export const highlightService = {
    /**
     * Upload y preview de archivo My Clippings.txt
     */
    async uploadFile(file) {
        const formData = new FormData()
        formData.append('file', file)

        return apiRequest('/highlights/upload/', {
            method: 'POST',
            body: formData
        })
    },

    /**
     * Importa highlights a la base de datos
     */
    async importHighlights(highlights) {
        return apiRequest('/highlights/import/', {
            method: 'POST',
            body: JSON.stringify({
                highlights
            })
        })
    },

    /**
     * Actualiza un highlight individual (visibilidad, nota, favorito)
     */
    async updateHighlight(highlightId, data) {
        return apiRequest(`/highlights/${highlightId}/`, {
            method: 'PATCH',
            body: JSON.stringify(data)
        })
    },

    /**
     * Obtiene highlights similares a uno dado
     */
    async getSimilar(highlightId, limit = 10) {
        return apiRequest(`/highlights/${highlightId}/similar/?limit=${limit}`)
    },

    /**
     * Revisa el estado de procesamiento de vectores matemáticos del usuario
     */
    async getEmbeddingStatus() {
        return apiRequest('/highlights/embedding-status/')
    },

    /**
     * Obtiene los highlights PÚBLICOS de un usuario (para el perfil público)
     */
    async getPublicHighlights(nickname) {
        return apiRequest(`/users/${nickname}/highlights/`)
    },

    /**
     * Obtiene los comentarios de un highlight público
     */
    async getComments(highlightId) {
        return apiRequest(`/highlights/${highlightId}/comments/`)
    },

    /**
     * Publica un comentario en un highlight
     */
    async postComment(highlightId, content) {
        return apiRequest(`/highlights/${highlightId}/comments/`, {
            method: 'POST',
            body: JSON.stringify({ content })
        })
    },

    /**
     * Exporta un libro individual a Markdown con frontmatter
     */
    async exportBookMarkdown(bookId) {
        const response = await apiFetch(`/me/export/books/${bookId}/markdown/`)
        if (!response.ok) {
            let msg = 'Error al exportar libro'
            try {
                const data = await response.json()
                msg = data.error || data.detail || msg
            } catch {
                // Ignore parse errors
            }
            throw new Error(msg)
        }

        const disposition = response.headers.get('content-disposition') || ''
        const filenameMatch = disposition.match(/filename\*?=(?:UTF-8''|")?([^";]+)/i)
        const rawFilename = filenameMatch ? filenameMatch[1].replace(/"/g, '') : `libro-${bookId}.md`
        const filename = decodeURIComponent(rawFilename)

        return {
            blob: await response.blob(),
            filename
        }
    }
}
