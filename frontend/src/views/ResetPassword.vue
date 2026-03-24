<template>
  <div class="forgot-page">
    <div class="forgot-main">
      <div class="forgot-container">
        <header class="forgot-header">
          <router-link :to="localizedTo('login')" class="back-link">{{ i18n.t('reset_password.back') }}</router-link>
        </header>

        <form class="forgot-form" @submit.prevent="handleSubmit">
          <span class="brand">exogram</span>
          <p class="forgot-title">{{ i18n.t('reset_password.title') }}</p>
          <p class="forgot-description">{{ i18n.t('reset_password.description') }}</p>

          <p v-if="tokenError" class="token-error">{{ i18n.t('reset_password.invalid_token') }}</p>

          <template v-else>
            <label class="input-label" for="reset-password">{{ i18n.t('reset_password.password_label') }}</label>
            <input
              id="reset-password"
              v-model="password"
              type="password"
              :placeholder="i18n.t('reset_password.password_placeholder')"
              autocomplete="new-password"
              required
            />

            <label class="input-label" for="reset-password-confirm">{{ i18n.t('reset_password.password_confirm_label') }}</label>
            <input
              id="reset-password-confirm"
              v-model="passwordConfirm"
              type="password"
              :placeholder="i18n.t('reset_password.password_confirm_placeholder')"
              autocomplete="new-password"
              required
            />

            <button type="submit" class="btn-enter" :disabled="isSubmitting">
              {{ isSubmitting ? i18n.t('reset_password.btn_loading') : i18n.t('reset_password.btn') }}
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
const password = ref('')
const passwordConfirm = ref('')
const isSubmitting = ref(false)
const statusMessage = ref('')

const handleSubmit = async () => {
  if (tokenError.value) return
  if (!password.value || !passwordConfirm.value) {
    uiStore.showError(i18n.t('reset_password.error_empty'))
    return
  }
  if (password.value !== passwordConfirm.value) {
    uiStore.showError(i18n.t('reset_password.error_mismatch'))
    return
  }

  isSubmitting.value = true
  statusMessage.value = ''
  try {
    const result = await authService.resetPassword(token.value, password.value, passwordConfirm.value)
    statusMessage.value = result?.message || i18n.t('reset_password.success')
    window.setTimeout(() => {
      router.push(localizedTo('login'))
    }, 1200)
  } catch (error) {
    uiStore.showError(error.message || i18n.t('reset_password.error_generic'))
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

.forgot-description {
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

.token-error,
.status-message {
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
  margin: var(--space-xs) 0 0;
}
</style>
