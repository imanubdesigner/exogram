<template>
  <div class="landing">
    <nav class="landing-nav">
      <span class="landing-brand">exogram</span>
      <button class="lang-toggle" @click="i18n.toggleLocale()">
        <Transition name="lang-swap" mode="out-in">
          <span :key="i18n.locale">{{ i18n.t('landing.footer.lang') }}</span>
        </Transition>
      </button>
    </nav>

    <main class="hero">
      <Transition name="locale-fade" mode="out-in">
        <div :key="i18n.locale" class="hero-content">
          <h1 class="hero-tagline">{{ i18n.t('landing.hero.tagline') }}</h1>
          <p class="hero-sub">{{ i18n.t('landing.hero.sub') }}</p>
          <router-link :to="localizedTo('login')" class="cta-primary">{{ i18n.t('landing.hero.cta') }}</router-link>
          <div class="hero-links">
            <router-link :to="localizedTo('waitlist')" class="minor-link">{{ i18n.t('landing.hero.waitlist') }}</router-link>
            <router-link :to="localizedTo('changelog')" class="minor-link">{{ i18n.t('nav.changelog') }}</router-link>
            <router-link :to="localizedTo('philosophy')" class="minor-link" target="_blank" rel="noopener noreferrer">
              {{ i18n.t('nav.philosophy') }}
            </router-link>
          </div>
        </div>
      </Transition>
    </main>

    <PublicFooter />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import PublicFooter from '../components/PublicFooter.vue'
import { useI18nStore } from '../stores/i18n'
import { getLocalizedPath } from '../router/localizedRoutes'

const i18n = useI18nStore()
const currentLocale = computed(() => (
  typeof i18n.locale === 'string'
    ? i18n.locale
    : i18n.locale?.value
))

const localizedTo = (routeName, params = {}, query = {}, hash = '') => {
  return getLocalizedPath(routeName, currentLocale.value, params, query, hash) || '/'
}
</script>

<style scoped>
.landing {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  max-width: 720px;
  margin: 0 auto;
  padding: 0 var(--space-lg);
}

.landing-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-xl) 0;
}

.landing-brand {
  font-family: var(--font-display);
  font-size: var(--font-size-base);
  font-weight: 400;
  letter-spacing: -0.02em;
  color: var(--text-primary);
  user-select: none;
}

.hero {
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: flex-start;
  gap: var(--space-lg);
  max-width: 540px;
  padding-bottom: var(--space-2xl);
}

.hero-content {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--space-lg);
}

.hero-links {
  display: flex;
  align-items: center;
  gap: var(--space-lg);
}

.hero-tagline {
  font-family: var(--font-display);
  font-size: clamp(2rem, 5vw, 3.2rem);
  font-weight: 400;
  line-height: 1.12;
  color: var(--text-primary);
  margin: 0;
  letter-spacing: -0.02em;
}

.hero-sub {
  font-family: var(--font-display);
  font-size: var(--font-size-base);
  color: var(--text-secondary);
  line-height: 1.7;
  margin: 0;
}

.cta-primary {
  font-family: var(--font-ui);
  font-size: var(--font-size-sm);
  font-weight: 400;
  color: var(--text-primary);
  text-decoration: none;
  border-bottom: 1px solid var(--text-primary);
  letter-spacing: 0.02em;
  padding-bottom: 1px;
  transition: color var(--transition-fast), border-color var(--transition-fast), opacity var(--transition-fast);
}

.cta-primary:hover {
  color: var(--text-secondary);
  border-bottom-color: var(--text-secondary);
  opacity: 0.9;
}

.minor-link {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  text-decoration: none;
  transition: color var(--transition-fast);
}

.minor-link:hover {
  color: var(--text-primary);
}

.lang-toggle {
  font-family: var(--font-ui);
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  background: none;
  border: none;
  padding: 0;
  letter-spacing: 0.08em;
  cursor: pointer;
  transition: color var(--transition-fast), opacity var(--transition-fast);
  line-height: 1.4;
}

.lang-toggle:hover {
  color: var(--text-primary);
  opacity: 0.9;
}

.locale-fade-enter-active,
.locale-fade-leave-active {
  transition: opacity 180ms ease, transform 180ms ease;
}

.locale-fade-enter-from,
.locale-fade-leave-to {
  opacity: 0;
  transform: translateY(4px);
}

.lang-swap-enter-active,
.lang-swap-leave-active {
  transition: opacity 140ms ease;
}

.lang-swap-enter-from,
.lang-swap-leave-to {
  opacity: 0;
}

@media (max-width: 640px) {
  .landing-nav {
    padding-top: var(--space-lg);
  }
}
</style>
