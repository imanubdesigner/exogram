import { createRouter, createWebHistory } from 'vue-router'
import { authService } from '../services/auth'
import { LOCALIZED_ROUTE_PATHS, getLocalizedPath, getRouteAliases, getStoredLocale } from './localizedRoutes'

const localizedRoute = ({ name, component, meta = {} }) => {
    const route = {
        path: LOCALIZED_ROUTE_PATHS[name].es,
        name,
        component
    }
    const aliases = getRouteAliases(name, 'es')
    if (aliases.length) route.alias = aliases
    if (Object.keys(meta).length > 0) route.meta = meta
    return route
}

export const routes = [
    localizedRoute({
        name: 'landing',
        component: () => import('../views/LandingPage.vue')
    }),
    localizedRoute({
        name: 'login',
        component: () => import('../views/Login.vue')
    }),
    localizedRoute({
        name: 'accept_invite',
        component: () => import('../views/AcceptInvite.vue')
    }),
    localizedRoute({
        name: 'forgot_password',
        component: () => import('../views/ForgotPassword.vue')
    }),
    localizedRoute({
        name: 'reset_password',
        component: () => import('../views/ResetPassword.vue')
    }),
    localizedRoute({
        name: 'dashboard',
        component: () => import('../views/Dashboard.vue'),
        meta: { requiresAuth: true }
    }),
    {
        path: '/highlights',
        redirect: () => getLocalizedPath('library', getStoredLocale()) || '/biblioteca'
    },
    localizedRoute({
        name: 'library',
        component: () => import('../views/Library.vue'),
        meta: { requiresAuth: true }
    }),
    localizedRoute({
        name: 'favorites',
        component: () => import('../views/Library.vue'),
        meta: { requiresAuth: true }
    }),
    localizedRoute({
        name: 'notes',
        component: () => import('../views/Notes.vue'),
        meta: { requiresAuth: true }
    }),
    localizedRoute({
        name: 'discover',
        component: () => import('../views/Discover.vue'),
        meta: { requiresAuth: true }
    }),
    localizedRoute({
        name: 'profile',
        component: () => import('../views/Profile.vue'),
        meta: { requiresAuth: true }
    }),
    localizedRoute({
        name: 'graph',
        component: () => import('../views/Graph.vue'),
        meta: { requiresAuth: true }
    }),
    localizedRoute({
        name: 'philosophy',
        component: () => import('../views/Philosophy.vue')
    }),
    localizedRoute({
        name: 'philosophy_article',
        component: () => import('../views/Philosophy.vue')
    }),
    localizedRoute({
        name: 'public_profile',
        component: () => import('../views/PublicProfile.vue')
    }),
    localizedRoute({
        name: 'thread',
        component: () => import('../views/ThreadView.vue'),
        meta: { requiresAuth: true }
    }),
    localizedRoute({
        name: 'waitlist',
        component: () => import('../views/Waitlist.vue')
    }),
    localizedRoute({
        name: 'waitlist_community',
        component: () => import('../views/CommunityWaitlist.vue'),
        meta: { requiresAuth: true }
    }),
    localizedRoute({
        name: 'changelog',
        component: () => import('../views/Changelog.vue')
    }),
]

export const installAuthGuard = (router) => {
    router.beforeEach(async (to, from, next) => {
        const preferredLocale = getStoredLocale()
        const requiresAuth = to.matched.some(record => record.meta.requiresAuth)
        const isLoginRoute = to.name === 'login'

        if (!requiresAuth) {
            if (isLoginRoute) {
                const currentUser = await authService.getCurrentUser()
                if (currentUser) {
                    authService.saveUser(currentUser)
                    if (currentUser.must_change_credentials) {
                        next(getLocalizedPath('profile', preferredLocale) || '/perfil')
                        return
                    }
                    next(getLocalizedPath('dashboard', preferredLocale) || '/dashboard')
                    return
                }
            }

            const localizedTarget = typeof to.name === 'string'
                ? getLocalizedPath(to.name, preferredLocale, to.params, to.query, to.hash)
                : null
            if (localizedTarget) {
                const resolvedTarget = router.resolve(localizedTarget).fullPath
                if (resolvedTarget !== to.fullPath) {
                    next(resolvedTarget)
                    return
                }
            }
            next()
            return
        }

        const currentUser = await authService.getCurrentUser()
        if (!currentUser) {
            sessionStorage.removeItem('auth_hint')
            sessionStorage.removeItem('must_change_credentials')
            next(getLocalizedPath('landing', preferredLocale) || '/')
            return
        }

        authService.saveUser(currentUser)
        if (currentUser.must_change_credentials && to.name !== 'profile') {
            next(getLocalizedPath('profile', preferredLocale) || '/perfil')
            return
        }

        const localizedTarget = typeof to.name === 'string'
            ? getLocalizedPath(to.name, preferredLocale, to.params, to.query, to.hash)
            : null
        if (localizedTarget) {
            const resolvedTarget = router.resolve(localizedTarget).fullPath
            if (resolvedTarget !== to.fullPath) {
                next(resolvedTarget)
                return
            }
        }

        next()
    })

    return router
}

export const createAppRouter = (history = createWebHistory()) => {
    const router = createRouter({
        history,
        routes,
    })

    return installAuthGuard(router)
}

const router = createAppRouter()

export default router
