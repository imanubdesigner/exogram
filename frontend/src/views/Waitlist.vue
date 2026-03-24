<template>
  <div class="waitlist-layout">
    <div class="waitlist-page container-narrow">
      <header class="wl-header">
        <router-link :to="localizedTo('landing')" class="back-link">{{ i18n.t('waitlist_view.back') }}</router-link>
        <h1 class="wl-title">exogram</h1>
        <p class="wl-subtitle">{{ i18n.t('waitlist_view.subtitle') }}</p>
      </header>

      <div v-if="submitted" class="success-state">
        <p class="success-text">{{ i18n.t('waitlist_view.success_title') }}</p>
        <p class="success-sub">{{ i18n.t('waitlist_view.success_sub') }}</p>
      </div>

      <form v-else class="wl-form" @submit.prevent="submit">
        <p class="wl-intro">{{ i18n.t('waitlist_view.intro') }}</p>

        <div class="field-group">
          <label class="field-label" for="wl-email">{{ i18n.t('waitlist_view.email_label') }}</label>
          <input
            id="wl-email"
            v-model="email"
            type="email"
            class="field-input"
            :placeholder="i18n.t('waitlist_view.email_placeholder')"
            autocomplete="email"
            required
          />
        </div>

        <div class="field-group">
          <label class="field-label" for="wl-message">
            {{ i18n.t('waitlist_view.reason_label') }} <span class="optional">{{ i18n.t('waitlist_view.optional') }}</span>
          </label>
          <textarea
            id="wl-message"
            v-model="message"
            class="field-input field-textarea"
            rows="3"
            maxlength="500"
            :placeholder="i18n.t('waitlist_view.reason_placeholder')"
          />
          <span class="char-count">{{ message.length }}/500</span>
        </div>

        <p v-if="errorMsg" class="error-msg">{{ errorMsg }}</p>

        <button type="submit" class="btn-action" :disabled="loading">
          {{ loading ? i18n.t('waitlist_view.submitting') : i18n.t('waitlist_view.submit') }}
        </button>
      </form>
    </div>

    <PublicFooter />
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import PublicFooter from '../components/PublicFooter.vue'
import { feedService } from '../services/feed'
import { useI18nStore } from '../stores/i18n'
import { getLocalizedPath } from '../router/localizedRoutes'

const email = ref('')
const message = ref('')
const loading = ref(false)
const submitted = ref(false)
const errorMsg = ref('')
const i18n = useI18nStore()
const currentLocale = computed(() => (
  typeof i18n.locale === 'string'
    ? i18n.locale
    : i18n.locale?.value
))

const localizedTo = (routeName, params = {}, query = {}, hash = '') => {
  return getLocalizedPath(routeName, currentLocale.value, params, query, hash) || '/'
}

async function submit() {
  errorMsg.value = ''
  loading.value = true
  try {
    await feedService.joinWaitlist(email.value.trim(), message.value.trim())
    submitted.value = true
  } catch (err) {
    errorMsg.value = err.message || i18n.t('waitlist_view.error_fallback')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.waitlist-layout {
  min-height: 100vh;
  max-width: 720px;
  margin: 0 auto;
  padding: 0 var(--space-lg);
  display: flex;
  flex-direction: column;
}

.waitlist-page {
  flex: 1;
  width: 100%;
  max-width: 480px;
  margin: 0 auto;
  padding: var(--space-3xl) 0 var(--space-2xl);
  display: flex;
  flex-direction: column;
  gap: var(--space-2xl);
}

.wl-header {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}

.back-link {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  text-decoration: none;
  margin-bottom: var(--space-lg);
  display: inline-block;
}

.back-link:hover { color: var(--text-primary); }

.wl-title {
  font-family: var(--font-display);
  font-size: var(--font-size-xl);
  font-weight: 400;
  margin: 0;
  text-transform: lowercase;
}

.wl-subtitle {
  margin: 0;
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
}

.wl-intro {
  margin: 0;
  font-family: var(--font-display);
  font-size: var(--font-size-lg);
  color: var(--text-secondary);
  line-height: 1.6;
}

.wl-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
}

.field-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}

.field-label {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  text-transform: lowercase;
  letter-spacing: 0.03em;
}

.optional {
  font-style: italic;
  opacity: 0.7;
}

.field-input {
  background: transparent;
  border: 1px solid var(--border-subtle);
  border-radius: 0;
  padding: var(--space-sm) var(--space-md);
  font-family: var(--font-ui);
  font-size: var(--font-size-sm);
  color: var(--text-primary);
  outline: none;
  transition: border-color var(--transition-fast);
  width: 100%;
  box-sizing: border-box;
}

.field-input:focus {
  border-color: var(--text-primary);
}

.field-textarea {
  resize: vertical;
  min-height: 80px;
  line-height: 1.6;
}

.char-count {
  font-size: 10px;
  color: var(--text-tertiary);
  align-self: flex-end;
}

.error-msg {
  margin: 0;
  font-size: var(--font-size-xs);
  color: var(--color-error, #c0392b);
}

.btn-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 36px;
  background: transparent;
  border: 1px solid var(--border-subtle);
  border-radius: 0;
  padding: 0 var(--space-xl);
  font-family: var(--font-ui);
  font-size: var(--font-size-xs);
  font-weight: 300;
  color: var(--text-tertiary);
  cursor: pointer;
  transition: all var(--transition-fast);
  letter-spacing: 0.04em;
  text-transform: lowercase;
  align-self: flex-end;
}

.btn-action:hover {
  border-color: var(--text-primary);
  color: var(--text-primary);
}

.btn-action:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.success-state {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
  padding: var(--space-xl) 0;
}

.success-text {
  margin: 0;
  font-family: var(--font-display);
  font-size: var(--font-size-xl);
  font-weight: 300;
  color: var(--text-primary);
}

.success-sub {
  margin: 0;
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
}
</style>
