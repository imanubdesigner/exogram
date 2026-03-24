<template>
  <footer class="public-footer">
    <span class="footer-credit">{{ i18n.t('landing.footer.developer_credit') }}</span>
    <span class="footer-sep" aria-hidden="true">·</span>
    <a
      class="footer-link"
      href="https://github.com/matzalazar"
      target="_blank"
      rel="noopener noreferrer"
    >
      {{ i18n.t('landing.footer.developer_github') }}
    </a>
    <span class="footer-sep" aria-hidden="true">·</span>
    <a
      class="footer-link"
      href="https://www.linkedin.com/in/matzalazar"
      target="_blank"
      rel="noopener noreferrer"
    >
      {{ i18n.t('landing.footer.developer_linkedin') }}
    </a>
    <span class="footer-sep" aria-hidden="true">·</span>
    <a
      class="footer-link"
      href="https://x.com/matzalazar_"
      target="_blank"
      rel="noopener noreferrer"
    >
      {{ i18n.t('landing.footer.developer_twitter') }}
    </a>
    <template v-if="donationAlias">
      <span class="footer-sep" aria-hidden="true">·</span>
      <span class="footer-credit">
        {{ i18n.t('landing.footer.donate', { alias: donationAlias }) }}
      </span>
    </template>
  </footer>
</template>

<script setup>
import { useI18nStore } from '../stores/i18n'

const i18n = useI18nStore()
const donationAlias = import.meta.env.VITE_DONATION_ALIAS || ''
</script>

<style scoped>
.public-footer {
  padding: var(--space-xl) 0;
  border-top: 1px solid var(--border-subtle);
  display: flex;
  justify-content: center;
  align-items: baseline;
  flex-wrap: wrap;
  gap: var(--space-xs);
  text-align: center;
}

.footer-credit {
  font-family: var(--font-display);
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  user-select: none;
  letter-spacing: 0.03em;
  line-height: 1.2;
}

.footer-sep {
  font-family: var(--font-display);
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  line-height: 1.2;
}

.footer-link {
  font-family: var(--font-display);
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  text-decoration: none;
  letter-spacing: 0.03em;
  line-height: 1.2;
  transition: color var(--transition-fast);
}

.footer-link:hover {
  color: var(--text-primary);
}
</style>
