import { apiRequest } from './api'
import { logger } from '../utils/logger'

export const socialService = {
    /**
     * Sigue a un usuario por nickname
     */
    async follow(nickname) {
        try {
            return await apiRequest(`/social/follow/${nickname}/`, {
                method: 'POST'
            })
        } catch (err) {
            logger.error('Error siguiendo usuario', err)
            throw err
        }
    },

    /**
     * Deja de seguir a un usuario por nickname
     */
    async unfollow(nickname) {
        try {
            return await apiRequest(`/social/unfollow/${nickname}/`, {
                method: 'POST'
            })
        } catch (err) {
            logger.error('Error dejando de seguir usuario', err)
            throw err
        }
    },

    /**
     * Verifica si sigues a un usuario
     */
    async checkFollow(nickname) {
        try {
            const resp = await apiRequest(`/social/check-follow/${nickname}/`)
            return resp.is_following
        } catch (err) {
            logger.warn('Error verificando estado de follow', err)
            return false
        }
    }
}
