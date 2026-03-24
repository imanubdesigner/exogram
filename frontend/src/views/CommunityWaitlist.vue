<template>
  <div class="community-waitlist container">
    <Navbar />

    <header class="community-header">
      <div class="header-back">
        <router-link :to="getLocalizedPath('graph', i18n.locale)" class="back-link">
          {{ i18n.t('community_waitlist.back') }}
        </router-link>
      </div>

      <div class="title-group">
        <h1 class="page-title">{{ i18n.t('community_waitlist.title') }}</h1>
        <p class="subtitle">{{ i18n.t('community_waitlist.subtitle') }}</p>
      </div>

      <div class="invitations-badge" v-if="invitationsRemaining !== null">
        <span class="badge-label">{{ i18n.t('community_waitlist.invitations_left') }}</span>
        <span class="badge-count">{{ invitationsRemaining }}</span>
      </div>
    </header>

    <div class="community-intro">
      <p>{{ i18n.t('community_waitlist.description') }}</p>
    </div>

    <section class="waitlist-grid" v-if="entries.length > 0">
      <div class="waitlist-card" v-for="entry in entries" :key="entry.id">
        <div class="card-header">
          <span class="entry-email">{{ entry.email }}</span>
          <span class="entry-date">{{ formatDate(entry.requested_at) }}</span>
        </div>
        <div class="card-body">
          <p class="entry-message" :class="{'no-message': !entry.message}">
            {{ entry.message || i18n.t('community_waitlist.no_message') }}
          </p>
        </div>
        <div class="card-footer">
          <button 
            class="btn-action btn-donate" 
            :disabled="donating[entry.id] || (invitationsRemaining !== null && invitationsRemaining <= 0)"
            @click="donateInvitation(entry)"
          >
            {{ donating[entry.id] ? i18n.t('community_waitlist.donating_btn') : i18n.t('community_waitlist.donate_btn') }}
          </button>
        </div>
      </div>
    </section>

    <div v-else-if="!loading && entries.length === 0" class="empty-state">
      <p>{{ i18n.t('community_waitlist.empty_state') }}</p>
    </div>

    <div class="load-more-container" v-if="hasMore">
      <button 
        class="btn-action btn-secondary" 
        :disabled="loading" 
        @click="loadMore"
      >
        {{ loading ? i18n.t('community_waitlist.loading') : i18n.t('community_waitlist.load_more') }}
      </button>
    </div>

    <div v-if="loading && entries.length === 0" class="state-msg">
      {{ i18n.t('community_waitlist.loading') }}
    </div>

  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { authService } from '../services/auth'
import { useI18nStore } from '../stores/i18n'
import { useUIStore } from '../stores/ui'
import { getLocalizedPath } from '../router/localizedRoutes'
import Navbar from '../components/Navbar.vue'

const i18n = useI18nStore()
const ui = useUIStore()

const entries = ref([])
const loading = ref(true)
const hasMore = ref(false)
const currentPage = ref(1)
const invitationsRemaining = ref(null)
const donating = ref({})

const waitlistSeed = (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function')
  ? crypto.randomUUID()
  : Math.random().toString(36).slice(2)

const loadWaitlist = async (page = 1) => {
  loading.value = true
  try {
    const response = await authService.getCommunityWaitlist(page, waitlistSeed)
    if (page === 1) {
      entries.value = response.results
    } else {
      entries.value = [...entries.value, ...response.results]
    }
    hasMore.value = !!response.next
    currentPage.value = page
  } catch {
    ui.showNotification(i18n.t('community_waitlist.error_generic'), 'error')
  } finally {
    loading.value = false
  }
}

const loadStats = async () => {
  try {
    const stats = await authService.getInvitationStats()
    invitationsRemaining.value = stats.remaining
  } catch {
    // Silently fail stats load
  }
}

const loadMore = () => {
  if (!loading.value && hasMore.value) {
    loadWaitlist(currentPage.value + 1)
  }
}

const donateInvitation = async (entry) => {
  if (invitationsRemaining.value !== null && invitationsRemaining.value <= 0) return

  donating.value[entry.id] = true
  try {
    const result = await authService.activateWaitlistEntry(entry.id)
    ui.showNotification(i18n.t('community_waitlist.success_msg'), 'success')
    if (typeof result?.invitations_remaining === 'number') {
      invitationsRemaining.value = result.invitations_remaining
    } else if (typeof invitationsRemaining.value === 'number') {
      invitationsRemaining.value = Math.max(0, invitationsRemaining.value - 1)
    }
    // Eliminar la tarjeta de la lista actual
    entries.value = entries.value.filter(e => e.id !== entry.id)
  } catch (err) {
    ui.showNotification(err.message || i18n.t('community_waitlist.error_generic'), 'error')
  } finally {
    donating.value[entry.id] = false
  }
}

const formatDate = (isoString) => {
  if (!isoString) return ''
  const date = new Date(isoString)
  return new Intl.DateTimeFormat(i18n.locale === 'es' ? 'es-AR' : 'en-US', {
    dateStyle: 'medium'
  }).format(date)
}

onMounted(() => {
  loadWaitlist(1)
  loadStats()
})
</script>

<style scoped>
.community-waitlist {
  padding-bottom: var(--space-3xl);
}

.community-header {
  margin: 0 0 var(--space-2xl);
  display: grid;
  grid-template-columns: 1fr auto;
  grid-template-areas:
    "back back"
    "title badge";
  gap: var(--space-md) var(--space-xl);
  align-items: start;
}

.header-back {
  grid-area: back;
}

.back-link {
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
  text-decoration: none;
  border-bottom: 1px solid transparent;
  transition: color var(--transition-fast), border-color var(--transition-fast);
}
.back-link:hover {
  color: var(--text-primary);
  border-bottom-color: var(--text-primary);
}

.title-group {
  grid-area: title;
}

.title-group .page-title {
  margin: 0 0 var(--space-xs);
  font-family: var(--font-display);
  font-size: var(--font-size-xl);
  font-weight: 400;
  color: var(--text-primary);
  text-transform: lowercase;
}

.title-group .subtitle {
  margin: 0;
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
}

.invitations-badge {
  grid-area: badge;
  display: inline-flex;
  align-items: center;
  gap: var(--space-xs);
  background-color: var(--bg-tertiary);
  padding: var(--space-sm) var(--space-md);
  border-radius: var(--border-radius);
  border: 1px solid var(--border-subtle);
  white-space: nowrap;
}

.badge-label {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  letter-spacing: 0.03em;
  text-transform: lowercase;
}

.badge-count {
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--text-primary);
}

.community-intro {
  margin: 0 0 var(--space-2xl);
  max-width: 560px;
}

.community-intro p {
  margin: 0;
  font-family: var(--font-display);
  font-size: var(--font-size-lg);
  color: var(--text-secondary);
  line-height: 1.6;
}

.waitlist-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: var(--space-lg);
  margin-bottom: var(--space-2xl);
}

.waitlist-card {
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-subtle);
  border-radius: var(--border-radius);
  padding: var(--space-lg);
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
  transition: border-color var(--transition-fast), background-color var(--transition-fast), box-shadow var(--transition-fast);
}

.waitlist-card:hover {
  border-color: var(--border-medium);
  background-color: var(--bg-tertiary);
  box-shadow: 0 10px 24px rgba(0, 0, 0, 0.04);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: var(--space-md);
  border-bottom: 1px dashed var(--border-subtle);
  padding-bottom: var(--space-sm);
}

.entry-email {
  font-family: var(--font-ui);
  font-size: var(--font-size-sm);
  color: var(--text-primary);
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
}

.entry-date {
  font-size: 11px;
  color: var(--text-tertiary);
  white-space: nowrap;
}

.card-body {
  flex-grow: 1;
}

.entry-message {
  margin: 0;
  font-family: var(--font-display);
  font-size: var(--font-size-sm);
  line-height: 1.6;
  color: var(--text-secondary);
  white-space: pre-wrap;
}

.entry-message.no-message {
  color: var(--text-tertiary);
  font-style: italic;
}

.card-footer {
  margin-top: auto;
  padding-top: var(--space-sm);
  display: flex;
}

.btn-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 34px;
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
  text-decoration: none;
}

.btn-action:hover {
  border-color: var(--text-primary);
  color: var(--text-primary);
}

.btn-action:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.btn-secondary {
  border-color: var(--border-medium);
}

.btn-donate {
  width: 100%;
}

.load-more-container {
  display: flex;
  justify-content: center;
  margin-top: var(--space-xl);
}

.empty-state,
.state-msg {
  text-align: center;
  padding: var(--space-2xl) 0;
  color: var(--text-tertiary);
  font-size: var(--font-size-sm);
}

.empty-state p {
  margin: 0;
  font-family: var(--font-display);
  font-size: var(--font-size-lg);
  font-style: italic;
  color: var(--text-tertiary);
}

@media (max-width: 640px) {
  .community-header {
    grid-template-columns: 1fr;
    grid-template-areas:
      "back"
      "title"
      "badge";
  }
}
</style>
