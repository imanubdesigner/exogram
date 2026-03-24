/**
 * API client centralizado para Exogram.
 *
 * - Usa VITE_API_URL en vez de URL hardcodeada
 * - Sesión JWT por cookies HttpOnly
 * - Refresh automático en 401
 * - Helper reutilizable para todos los services
 */

function resolveApiBase(baseUrl = import.meta.env.VITE_API_URL) {
    const normalizedBase = (baseUrl || 'http://localhost:8000').replace(/\/$/, '')
    return `${normalizedBase}/api`
}

const API_BASE = resolveApiBase()
const MUTATING_METHODS = new Set(['POST', 'PUT', 'PATCH', 'DELETE'])

function getCookieValue(name) {
    const cookies = document.cookie ? document.cookie.split('; ') : []
    const match = cookies.find((cookie) => cookie.startsWith(`${name}=`))
    if (!match) return null
    return decodeURIComponent(match.substring(name.length + 1))
}

/**
 * Intenta refrescar la sesión usando refresh cookie HttpOnly.
 * @returns {boolean} true si refrescó correctamente
 */
async function refreshAccessToken() {
    try {
        const csrfToken = getCookieValue('csrftoken')
        const headers = { 'Content-Type': 'application/json' }
        if (csrfToken) headers['X-CSRFToken'] = csrfToken

        const response = await fetch(`${API_BASE}/auth/token/refresh/`, {
            method: 'POST',
            headers,
            credentials: 'include',
            body: JSON.stringify({})
        })

        if (!response.ok) {
            sessionStorage.removeItem('auth_hint')
            sessionStorage.removeItem('must_change_credentials')
            return false
        }
        return response.ok
    } catch {
        sessionStorage.removeItem('auth_hint')
        sessionStorage.removeItem('must_change_credentials')
        return false
    }
}

/**
 * Fetch wrapper con autenticación JWT y auto-refresh.
 *
 * @param {string} path - Ruta relativa al API_BASE (ej: '/highlights/')
 * @param {object} options - Opciones de fetch (method, body, headers, etc.)
 * @returns {Response}
 */
export async function apiFetch(path, options = {}) {
    const method = (options.method || 'GET').toUpperCase()
    const headers = {
        ...(options.headers || {}),
    }

    // No agregar Content-Type si es FormData (el browser lo maneja)
    if (!(options.body instanceof FormData) && !headers['Content-Type']) {
        headers['Content-Type'] = 'application/json'
    }

    if (MUTATING_METHODS.has(method)) {
        // Cliente Double Submit Cookie: enviamos X-CSRFToken (leído de cookie)
        // para que el backend lo compare contra la cookie CSRF.
        const csrfToken = getCookieValue('csrftoken')
        if (csrfToken) headers['X-CSRFToken'] = csrfToken
    }

    let response = await fetch(`${API_BASE}${path}`, {
        ...options,
        method,
        headers,
        // Con credenciales incluidas el browser envía cookies entre orígenes/puertos;
        // sin esto se rompe tanto autenticación como CSRF en dev con frontend/backend separados.
        credentials: 'include'
    })

    const isRefreshEndpoint = path.startsWith('/auth/token/refresh/')
    const isLoginEndpoint = path.startsWith('/auth/login/')
    const canRetryWithRefresh = !isRefreshEndpoint && !isLoginEndpoint

    // Si 401, intentar refrescar y reintentar una vez
    if (response.status === 401 && canRetryWithRefresh) {
        const refreshed = await refreshAccessToken()
        if (refreshed) {
            response = await fetch(`${API_BASE}${path}`, {
                ...options,
                method,
                headers,
                credentials: 'include'
            })
        }
    }

    return response
}

/**
 * Helper: apiFetch + parse JSON + manejo de errores
 */
export async function apiRequest(path, options = {}) {
    const response = await apiFetch(path, options)

    if (!response.ok) {
        let errorMsg = `Error ${response.status}`
        try {
            const data = await response.json()
            errorMsg = data.error || data.detail || errorMsg
        } catch { /* ignore parse errors */ }
        throw new Error(errorMsg)
    }

    // 204 No Content
    if (response.status === 204) return null

    return response.json()
}

export { API_BASE, resolveApiBase }
