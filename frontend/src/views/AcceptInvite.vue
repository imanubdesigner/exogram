<template>
  <div class="accept-page">
    <div class="accept-main">
      <div class="accept-container">
        <header class="accept-header">
          <router-link :to="localizedTo('login')" class="back-link">{{ i18n.t('accept_invite.back') }}</router-link>
        </header>

        <form class="accept-form" @submit.prevent="handleSubmit">
          <span class="brand">exogram</span>
          <p class="accept-title">{{ i18n.t('accept_invite.title') }}</p>
          <p class="accept-description">{{ i18n.t('accept_invite.description') }}</p>

          <p v-if="tokenError" class="token-error">{{ i18n.t('accept_invite.invalid_token') }}</p>

          <template v-else>
            <label class="input-label" for="accept-username">{{ i18n.t('accept_invite.username_label') }}</label>
            <input
              id="accept-username"
              v-model="username"
              type="text"
              :placeholder="i18n.t('accept_invite.username_placeholder')"
              autocomplete="username"
              required
            />

            <label class="input-label" for="accept-password">{{ i18n.t('accept_invite.password_label') }}</label>
            <input
              id="accept-password"
              v-model="password"
              type="password"
              :placeholder="i18n.t('accept_invite.password_placeholder')"
              autocomplete="new-password"
              required
            />

            <button type="submit" class="btn-enter" :disabled="isSubmitting">
              {{ isSubmitting ? i18n.t('accept_invite.btn_loading') : i18n.t('accept_invite.btn') }}
            </button>
          </template>

          <p v-if="statusMessage" class="status-message">{{ statusMessage }}</p>
        </form>
      </div>
    </div>

    <PublicFooter />
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PublicFooter from '../components/PublicFooter.vue'
import { useUIStore } from '../stores/ui'
import { useI18nStore } from '../stores/i18n'
import { authService } from '../services/auth'
import { getLocalizedPath } from '../router/localizedRoutes'

const route = useRoute()
const router = useRouter()
const uiStore = useUIStore()
const i18n = useI18nStore()
const currentLocale = computed(() => (
  typeof i18n.locale === 'string'
    ? i18n.locale
    : i18n.locale?.value
))

const localizedTo = (routeName, params = {}, query = {}, hash = '') => {
  return getLocalizedPath(routeName, currentLocale.value, params, query, hash) || '/'
}

const token = computed(() => (route.query.token || '').toString().trim())
const tokenError = computed(() => !token.value)
const username = ref('')
const password = ref('')
const isSubmitting = ref(false)
const statusMessage = ref('')

const handleSubmit = async () => {
  if (tokenError.value) return
  if (!username.value || !password.value) {
    uiStore.showError(i18n.t('accept_invite.error_empty'))
    return
  }

  isSubmitting.value = true
  statusMessage.value = ''
  try {
    const result = await authService.acceptInvitation(token.value, username.value, password.value)
    statusMessage.value = result?.message || i18n.t('accept_invite.success')
    window.setTimeout(() => {
      router.push(localizedTo('login'))
    }, 1200)
  } catch (error) {
    uiStore.showError(error.message || i18n.t('accept_invite.error_generic'))
  } finally {
    isSubmitting.value = false
  }
}
</script>

<style scoped>
.accept-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  max-width: 720px;
  margin: 0 auto;
  padding: 0 var(--space-lg);
}

.accept-main {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-md) 0 var(--space-xl);
}

.accept-container {
  width: 100%;
  max-width: 320px;
  display: flex;
  flex-direction: column;
  gap: var(--space-xl);
}

.accept-header {
  display: flex;
  margin-bottom: var(--space-xs);
}

.back-link {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  text-decoration: none;
  border-bottom: none;
  transition: color var(--transition-fast);
}

.back-link:hover {
  color: var(--text-primary);
}

.accept-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.brand {
  font-family: var(--font-display);
  font-size: var(--font-size-xl);
  font-weight: 400;
  letter-spacing: -0.02em;
  color: var(--text-tertiary);
  text-align: center;
  margin-bottom: var(--space-lg);
  user-select: none;
}

.accept-title {
  font-family: var(--font-display);
  font-size: var(--font-size-xl);
  font-weight: 400;
  letter-spacing: -0.02em;
  color: var(--text-primary);
  margin: 0;
}

.accept-description {
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
  margin: 0;
  line-height: 1.4;
}

.input-label {
  font-size: var(--font-size-xs);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-tertiary);
}

.accept-form input {
  border: none;
  border-bottom: 1px solid var(--border-subtle);
  border-radius: 0;
  padding: var(--space-sm) 0;
  background: transparent;
  font-size: var(--font-size-base);
  font-weight: 300;
  transition: border-color var(--transition-fast);
}

.accept-form input:focus {
  outline: none;
  border-bottom-color: var(--text-primary);
}

.btn-enter {
  background: none;
  border: none;
  padding: var(--space-md) 0;
  font-family: var(--font-ui);
  font-size: var(--font-size-sm);
  font-weight: 300;
  color: var(--text-tertiary);
  cursor: pointer;
  transition: color var(--transition-fast);
  letter-spacing: 0.05em;
  text-align: center;
  margin-top: var(--space-md);
}

.btn-enter:hover:not(:disabled) {
  color: var(--text-primary);
}

.btn-enter:disabled {
  opacity: 0.6;
  cursor: wait;
}

.token-error,
.status-message {
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
  margin: var(--space-xs) 0 0;
}
</style>
