<template>
  <nav class="nav-minimal">
    <div class="nav-left">
      <router-link :to="localizedTo('dashboard')" active-class="active">{{ i18n.t('navbar.home') }}</router-link>
      <router-link :to="localizedTo('library')" active-class="active">{{ i18n.t('navbar.library') }}</router-link>
      <router-link :to="localizedTo('favorites')" active-class="active">{{ i18n.t('navbar.favs') }}</router-link>
      <router-link :to="localizedTo('notes')" active-class="active">{{ i18n.t('navbar.notes') }}</router-link>
      <router-link v-if="showDiscoverLink" :to="localizedTo('discover')" active-class="active">{{ i18n.t('navbar.discover') }}</router-link>
      <router-link :to="localizedTo('graph')" active-class="active">{{ i18n.t('navbar.graph') }}</router-link>
      <router-link :to="localizedTo('profile')" active-class="active">{{ i18n.t('navbar.profile') }}</router-link>
    </div>
    
    <div class="nav-right">
      <router-link :to="localizedTo('philosophy')" active-class="active" class="link-philosophy">{{ i18n.t('navbar.philosophy') }}</router-link>
      <button class="lang-toggle nav-lang-toggle" @click="i18n.toggleLocale()">
        {{ i18n.t('navbar.lang') }}
      </button>
    </div>
  </nav>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import { authService } from '../services/auth'
import { useI18nStore } from '../stores/i18n'
import { getLocalizedPath } from '../router/localizedRoutes'
import { logger } from '../utils/logger'

const authStore = useAuthStore()
const i18n = useI18nStore()
const userResolved = ref(false)
const currentLocale = computed(() => (
  typeof i18n.locale === 'string'
    ? i18n.locale
    : i18n.locale?.value
))

const localizedTo = (routeName, params = {}, query = {}, hash = '') => {
  return getLocalizedPath(routeName, currentLocale.value, params, query, hash) || '/'
}

const showDiscoverLink = computed(() => {
  if (!authService.isAuthenticated()) return true
  if (!userResolved.value && !authStore.user) return false
  return authStore.user?.is_discoverable !== false
})

onMounted(async () => {
  if (authService.isAuthenticated() && !authStore.user) {
    try {
      await authStore.refreshCurrentUser()
    } catch (err) {
      logger.error('Error loading user for navbar:', err)
    } finally {
      userResolved.value = true
    }
    return
  }
  userResolved.value = true
})
</script>

<style scoped>
.nav-minimal {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-top: var(--space-xl);
  margin-bottom: var(--space-2xl);
  padding-bottom: var(--space-md);
  border-bottom: 1px solid var(--border-subtle);
}

.nav-left {
  display: flex;
  gap: var(--space-lg);
}

.nav-right {
  display: flex;
  align-items: center;
  gap: var(--space-md);
}

.nav-lang-toggle {
  font-family: var(--font-ui);
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  background: none;
  border: 1px solid var(--border-medium);
  border-radius: var(--border-radius);
  padding: 2px 8px;
  letter-spacing: 0.08em;
  cursor: pointer;
  transition: color var(--transition-fast), border-color var(--transition-fast);
  line-height: 1.6;
}

.nav-lang-toggle:hover {
  color: var(--text-primary);
  border-color: var(--text-secondary);
}

.nav-minimal a {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  text-decoration: none;
  border-bottom: none;
  letter-spacing: 0.03em;
  transition: color var(--transition-fast);
}

.nav-minimal a:hover,
.nav-minimal a.active {
  color: var(--text-primary);
}

.link-philosophy {
  font-style: italic;
}

@media (max-width: 640px) {
  .nav-minimal {
    flex-wrap: wrap;
    gap: var(--space-md);
  }
}
</style>
