<template>
  <div class="forgot-page">
    <div class="forgot-main">
      <div class="forgot-container">
        <header class="forgot-header">
          <router-link :to="localizedTo('login')" class="back-link">{{ i18n.t('forgot_password.back') }}</router-link>
        </header>

        <form class="forgot-form" @submit.prevent="handleSubmit">
          <span class="brand">exogram</span>
          <p class="forgot-title">{{ i18n.t('forgot_password.title') }}</p>

          <label class="input-label" for="forgot-email">{{ i18n.t('forgot_password.email_label') }}</label>
          <input
            id="forgot-email"
            v-model="email"
            type="email"
            :placeholder="i18n.t('forgot_password.email_placeholder')"
            autocomplete="email"
            required
          />

          <button type="submit" class="btn-enter" :disabled="isSubmitting">
            {{ isSubmitting ? i18n.t('forgot_password.btn_loading') : i18n.t('forgot_password.btn') }}
          </button>

          <p v-if="statusMessage" class="status-message">{{ statusMessage }}</p>
        </form>
      </div>
    </div>

    <PublicFooter />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import PublicFooter from '../components/PublicFooter.vue'
import { useUIStore } from '../stores/ui'
import { useI18nStore } from '../stores/i18n'
import { authService } from '../services/auth'
import { getLocalizedPath } from '../router/localizedRoutes'
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

const email = ref('')
const isSubmitting = ref(false)
const statusMessage = ref('')

const handleSubmit = async () => {
  const normalizedEmail = (email.value || '').trim()
  if (!normalizedEmail) {
    uiStore.showError(i18n.t('forgot_password.error_email'))
    return
  }

  isSubmitting.value = true
  statusMessage.value = ''
  try {
    const result = await authService.forgotPassword(normalizedEmail)
    statusMessage.value = result?.message || i18n.t('forgot_password.success')
  } catch (error) {
    uiStore.showError(error.message || i18n.t('forgot_password.error_generic'))
  } finally {
    isSubmitting.value = false
  }
}
</script>

<style scoped>
.forgot-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  max-width: 720px;
  margin: 0 auto;
  padding: 0 var(--space-lg);
}

.forgot-main {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-md) 0 var(--space-xl);
}

.forgot-container {
  width: 100%;
  max-width: 320px;
  display: flex;
  flex-direction: column;
  gap: var(--space-xl);
}

.forgot-header {
  display: flex;
  margin-bottom: var(--space-xs);
}

.forgot-header .back-link {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  text-decoration: none;
  border-bottom: none;
  transition: color var(--transition-fast);
}

.forgot-header .back-link:hover {
  color: var(--text-primary);
}

.forgot-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.forgot-title {
  font-family: var(--font-display);
  font-size: var(--font-size-xl);
  font-weight: 400;
  letter-spacing: -0.02em;
  color: var(--text-primary);
  text-transform: capitalize;
  margin: 0;
}



.input-label {
  font-size: var(--font-size-xs);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-tertiary);
}

.forgot-form input {
  border: none;
  border-bottom: 1px solid var(--border-subtle);
  border-radius: 0;
  padding: var(--space-sm) 0;
  background: transparent;
  font-size: var(--font-size-base);
  font-weight: 300;
  transition: border-color var(--transition-fast);
}

.forgot-form input:focus {
  outline: none;
  border-bottom-color: var(--text-primary);
}

.status-message {
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
  margin: var(--space-xs) 0 0;
}

.btn-enter {
  background: none;
  border: none;
  padding: var(--space-md) 0;
  font-family: var(--font-ui);
  font-size: 11px;
  font-weight: 300;
  color: var(--text-tertiary);
  cursor: pointer;
  transition: color var(--transition-fast);
  letter-spacing: 0.05em;
  align-self: flex-end;
  margin-top: var(--space-md);
}

.btn-enter:hover {
  color: var(--text-primary);
}

.btn-enter:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
</style>
