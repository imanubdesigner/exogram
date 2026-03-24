<template>
  <div class="discover container">
    <Navbar />

    <section class="feed-header">
      <h1 class="feed-title">{{ i18n.t('discover.title') }}</h1>
    </section>

    <!-- Feed desactivado -->
    <div v-if="isDiscoverDisabled" class="hermit-notice">
      <p class="hermit-text">
        {{ i18n.t('discover.disabled_text') }}
      </p>
      <router-link to="/perfil" class="hermit-link">{{ i18n.t('discover.disabled_link') }}</router-link>
    </div>

    <!-- Hermit mode -->
    <div v-else-if="isHermit" class="hermit-notice">
      <p class="hermit-text">
        {{ i18n.t('discover.hermit_text') }}
      </p>
      <router-link to="/perfil" class="hermit-link">{{ i18n.t('discover.hermit_link') }}</router-link>
    </div>

    <template v-else>
      <!-- Cargando -->
      <div v-if="loading" class="skeleton-block">
        <div class="skeleton-line skeleton-line--wide" />
        <div class="skeleton-line skeleton-line--mid" />
        <div class="skeleton-line skeleton-line--narrow" />
      </div>

      <div v-else class="feed-body">

        <!-- ═══ Sección superior: también leyendo + lectores afines ══════════ -->
        <div
          v-if="hasTopSections"
          :class="['feed-top-grid', { 'feed-top-grid--single': isTopGridSingle }]"
        >

          <!-- Siguiendo (Usuarios) -->
          <section v-if="followingUsers.length > 0" class="feed-section">
            <h2 class="section-label">{{ i18n.t('discover.section_following') }}</h2>
            <div class="compact-list">
              <div
                v-for="user in followingUsers"
                :key="`following-${user.nickname}`"
                class="compact-row"
              >
                <div class="compact-row-main">
                  <span class="nickname-tag">@{{ user.nickname }}</span>
                </div>
                <!-- Mostrar lo último publicado -->
                <p v-if="user.latest_highlight" class="row-bio">
                  <span class="activity-label">{{ i18n.t('discover.activity_latest') }}</span> 
                  <span class="activity-quote">"{{ user.latest_highlight.slice(0, 70) }}{{ user.latest_highlight.length > 70 ? '...' : '' }}"</span>
                  <br />
                  <span class="activity-book" v-if="user.latest_book">{{ i18n.t('discover.activity_in') }} {{ user.latest_book }}</span>
                </p>
                <p v-else-if="user.bio" class="row-bio">{{ user.bio }}</p>
                <div class="row-actions">
                  <router-link :to="`/users/${user.nickname}`" class="row-btn" style="text-decoration: none;">
                    {{ i18n.t('discover.view_profile') }}
                  </router-link>
                  <span class="row-btn-sep">·</span>
                  <button class="row-btn" @click="initThread(user.nickname)">
                    {{ i18n.t('discover.chat') }}
                  </button>
                </div>
              </div>
            </div>
          </section>

          <!-- También leyendo -->
          <section v-if="alsoReadingItems.length > 0" class="feed-section">
            <h2 class="section-label">{{ i18n.t('discover.section_also_reading') }}</h2>
            <div class="compact-list">
              <div
                v-for="item in alsoReadingItems"
                :key="`also-${item.bookId}-${item.nickname}`"
                class="compact-row"
              >
                <div class="compact-row-main">
                  <span class="nickname-tag">@{{ item.nickname }}</span>
                  <span class="row-sep">·</span>
                  <span class="book-italic">{{ item.bookTitle }}</span>
                </div>
                <button
                  class="row-btn"
                  :disabled="startingThread === item.nickname"
                  @click="initThread(item.nickname, item.bookTitle)"
                >
                  {{ startingThread === item.nickname ? '…' : i18n.t('discover.start_thread') }}
                </button>
              </div>
            </div>
          </section>

          <!-- Lectores afines -->
          <section v-if="similarReaders.length > 0" class="feed-section">
            <h2 class="section-label">{{ i18n.t('discover.section_similar_readers') }}</h2>
            <div class="compact-list">
              <div
                v-for="reader in similarReaders"
                :key="`reader-${reader.nickname}`"
                class="compact-row"
              >
                <div class="compact-row-main">
                  <span class="nickname-tag">@{{ reader.nickname }}</span>
                </div>
                <p v-if="reader.common_books && reader.common_books.length > 0" class="row-bio">
                  {{ i18n.t('discover.also_read_prefix') }}: {{ reader.common_books.join(' · ') }}
                </p>
                <p v-else-if="reader.bio" class="row-bio">{{ reader.bio }}</p>
                <button
                  class="row-btn"
                  :disabled="startingThread === reader.nickname"
                  @click="initThread(reader.nickname)"
                >
                  {{ startingThread === reader.nickname ? '…' : i18n.t('discover.chat') }}
                </button>
              </div>

            </div>
          </section>
        </div>

        <!-- ═══ Mis charlas ════════════════════════════════════════════════ -->
        <section v-if="threads.length > 0" class="feed-section threads-section">
          <h2 class="section-label">{{ i18n.t('discover.section_threads') }}</h2>
          <div class="thread-list">
            <router-link
              v-for="thread in paginatedThreads"
              :key="`thread-${thread.id}`"
              :to="`/hilos/${thread.id}`"
              class="thread-row"
            >
              <div class="thread-row-main">
                <span class="nickname-tag">@{{ thread.other_nickname }}</span>
                <span v-if="thread.context_book_title" class="book-italic">
                  · {{ thread.context_book_title }}
                </span>
              </div>
              <p v-if="thread.last_message" class="thread-preview">
                {{ thread.last_message.content.slice(0, 90)
                }}{{ thread.last_message.content.length > 90 ? '…' : '' }}
              </p>
            </router-link>
          </div>
          <PaginationControl 
            v-model="threadPage" 
            :total-items="threads.length" 
            :page-size="5" 
          />
        </section>

        <!-- ═══ Actividad de tus seguidos ══════════════════════════════════ -->
        <section v-if="followingFeed.length > 0" class="feed-section highlights-section">
          <h2 class="section-label">{{ i18n.t('discover.section_following_activity') }}</h2>
          <div class="highlight-stream">
            <article
              v-for="item in paginatedFollowingFeed"
              :key="`following-feed-${item.id}`"
              class="stream-entry"
            >
              <blockquote class="stream-quote">{{ item.content }}</blockquote>
              <footer class="stream-footer">
                <span class="book-italic">{{ item.book_title }}</span>
                <span class="row-sep">·</span>
                <span class="footer-nick">@{{ item.user_nickname }}</span>
              </footer>
            </article>
          </div>
          <PaginationControl 
            v-model="followingPage" 
            :total-items="totalFollowingCount" 
            :page-size="5" 
          />
        </section>

        <!-- ═══ Feed de highlights ═════════════════════════════════════════ -->
        <section v-if="discoveryFeed.length > 0" class="feed-section highlights-section">
          <h2 class="section-label">{{ i18n.t('discover.section_recent') }}</h2>
          <div class="highlight-stream">
            <article
              v-for="item in paginatedFeed"
              :key="`feed-${item.id}`"
              class="stream-entry"
            >
              <blockquote class="stream-quote">{{ item.content }}</blockquote>
              <footer class="stream-footer">
                <span class="book-italic">{{ item.book_title }}</span>
                <span class="row-sep">·</span>
                <span class="footer-nick">@{{ item.user_nickname }}</span>
              </footer>
            </article>
          </div>
          <PaginationControl 
            v-model="feedPage" 
            :total-items="totalFeedCount" 
            :page-size="5" 
          />
        </section>

        <!-- ═══ Estado vacío ═══════════════════════════════════════════════ -->
        <div
          v-if="!loading && isEmpty"
          class="empty-state"
        >
          <p class="empty-text">{{ i18n.t('discover.empty_text') }}</p>
        </div>

      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useUIStore } from '../stores/ui'
import { useI18nStore } from '../stores/i18n'
import { feedService } from '../services/feed'
import { authService } from '../services/auth'
import { apiRequest } from '../services/api'
import { logger } from '../utils/logger'
import Navbar from '../components/Navbar.vue'
import PaginationControl from '../components/PaginationControl.vue'
import { getLocalizedPath } from '../router/localizedRoutes'

const authStore = useAuthStore()
const uiStore = useUIStore()
const i18n = useI18nStore()
const router = useRouter()
const currentLocale = computed(() => (
  typeof i18n.locale === 'string'
    ? i18n.locale
    : i18n.locale?.value
))

const loading = ref(true)
const loadingMore = ref(false)
const startingThread = ref(null)

const similarReaders = ref([])
const alsoReadingItems = ref([])
const followingUsers = ref([])
const discoveryFeed = ref([])
const followingFeed = ref([])
const threads = ref([])

const threadPage = ref(1)

const feedPage = ref(1)
const totalFeedCount = ref(0)
const hasMoreFeed = ref(false)

const followingPage = ref(1)
const totalFollowingCount = ref(0)
const hasMoreFollowing = ref(false)

const paginatedThreads = computed(() => {
  const start = (threadPage.value - 1) * 5
  return threads.value.slice(start, start + 5)
})

watch(feedPage, async (newVal) => {
  const maxCovered = newVal * 5
  if (maxCovered > discoveryFeed.value.length && hasMoreFeed.value) {
    await loadMoreFeed()
  }
})

const paginatedFeed = computed(() => {
  const start = (feedPage.value - 1) * 5
  return discoveryFeed.value.slice(start, start + 5)
})

watch(followingPage, async (newVal) => {
  const maxCovered = newVal * 5
  if (maxCovered > followingFeed.value.length && hasMoreFollowing.value) {
    await loadMoreFollowingFeed()
  }
})

const paginatedFollowingFeed = computed(() => {
  const start = (followingPage.value - 1) * 5
  return followingFeed.value.slice(start, start + 5)
})

const isHermit = computed(() => authStore.user?.is_hermit_mode === true)
const isDiscoverDisabled = computed(() => authStore.user?.is_discoverable === false)
const topSectionsCount = computed(
  () =>
    (alsoReadingItems.value.length > 0 ? 1 : 0) +
    (similarReaders.value.length > 0 ? 1 : 0) +
    (followingUsers.value.length > 0 ? 1 : 0),
)
const hasTopSections = computed(() => topSectionsCount.value > 0)
const isTopGridSingle = computed(() => topSectionsCount.value === 1)
const isEmpty = computed(
  () =>
    alsoReadingItems.value.length === 0 &&
    similarReaders.value.length === 0 &&
    followingUsers.value.length === 0 &&
    discoveryFeed.value.length === 0 &&
    followingFeed.value.length === 0 &&
    threads.value.length === 0,
)

onMounted(async () => {
  if (!authStore.user && authService.isAuthenticated()) {
    try {
      await authStore.refreshCurrentUser()
    } catch (err) {
      logger.warn('No se pudo refrescar usuario para feed', err)
    }
  }

  if (isDiscoverDisabled.value || isHermit.value) {
    loading.value = false
    return
  }

  await loadFeed()
})

async function loadFeed() {
  loading.value = true
  try {
    const [readersResult, feedResult, threadsResult, followingUsersResult, followingFeedResult] = await Promise.allSettled([
      feedService.getSimilarReaders(5),
      feedService.getDiscoveryFeed(1),
      feedService.getThreads(),
      feedService.getFollowingUsers(),
      feedService.getFollowingFeed(1),
    ])

    if (readersResult.status === 'fulfilled') {
      similarReaders.value = readersResult.value.results || []
    }

    if (feedResult.status === 'fulfilled') {
      const feed = feedResult.value ?? {}
      discoveryFeed.value = Array.isArray(feed.results) ? feed.results : []
      hasMoreFeed.value = !!feed.next
      totalFeedCount.value = feed.count ?? discoveryFeed.value.length
    }

    if (threadsResult.status === 'fulfilled') {
      threads.value = threadsResult.value.results || []
    }

    if (followingUsersResult.status === 'fulfilled') {
      followingUsers.value = followingUsersResult.value.results || []
    }

    if (followingFeedResult.status === 'fulfilled') {
      const feed = followingFeedResult.value ?? {}
      followingFeed.value = Array.isArray(feed.results) ? feed.results : []
      hasMoreFollowing.value = !!feed.next
      totalFollowingCount.value = feed.count ?? followingFeed.value.length
    }

    await loadAlsoReading()
  } catch (err) {
    logger.error('Error cargando feed', err)
  } finally {
    loading.value = false
  }
}

async function loadAlsoReading() {
  try {
    // Usa apiRequest (JWT + auto-refresh) en vez de fetch crudo
    const data = await apiRequest('/highlights/?page=1&page_size=50')
    const highlights = data.results || data || []

    const bookMap = {}
    for (const h of highlights) {
      if (h.book_id && !bookMap[h.book_id]) {
        bookMap[h.book_id] = h.book_title || ''
      }
    }

    const bookIds = Object.keys(bookMap).slice(0, 5)
    const alsoResults = await Promise.all(
      bookIds.map(id =>
        feedService.getAlsoReading(id).then(d => ({ ...d, bookId: id, bookTitle: bookMap[id] })),
      ),
    )

    const items = []
    for (const result of alsoResults) {
      for (const reader of result.readers || []) {
        items.push({ nickname: reader.nickname, bookTitle: result.bookTitle, bookId: result.bookId })
      }
    }
    alsoReadingItems.value = items.slice(0, 5)
  } catch (err) {
    logger.warn('No se pudo cargar "también leyendo"', err)
  }
}

async function loadMoreFeed() {
  loadingMore.value = true
  try {
    const nextPage = Math.ceil(discoveryFeed.value.length / 20) + 1 // asumiendo que el backend trae de a 20 o similar
    const result = await feedService.getDiscoveryFeed(nextPage)
    discoveryFeed.value.push(...(result.results || []))
    hasMoreFeed.value = !!result.next
    totalFeedCount.value = result.count || discoveryFeed.value.length + (result.next ? 20 : 0) // fallback estimation
  } catch {
    uiStore.showError(i18n.t('discover.messages.load_more_error'))
  } finally {
    loadingMore.value = false
  }
}

async function loadMoreFollowingFeed() {
  loadingMore.value = true
  try {
    const nextPage = Math.ceil(followingFeed.value.length / 20) + 1
    const result = await feedService.getFollowingFeed(nextPage)
    followingFeed.value.push(...(result.results || []))
    hasMoreFollowing.value = !!result.next
    totalFollowingCount.value = result.count || followingFeed.value.length + (result.next ? 20 : 0)
  } catch {
    uiStore.showError(i18n.t('discover.messages.load_more_error'))
  } finally {
    loadingMore.value = false
  }
}

async function initThread(nickname, bookTitle = '') {
  // Cuando se llama desde un @click sin argumentos, bookTitle es un objeto PointerEvent.
  // Evitamos enviarlo al backend para no causar un 500.
  const contextBook = typeof bookTitle === 'string' ? bookTitle : ''
  
  startingThread.value = nickname
  try {
    const thread = await feedService.createThread(nickname, contextBook)
    router.push(
      getLocalizedPath('thread', currentLocale.value, { threadId: thread.id }) || `/hilos/${thread.id}`,
    )
  } catch (err) {
    uiStore.showError(err.message || i18n.t('discover.messages.thread_error'))
  } finally {
    startingThread.value = null
  }
}
</script>

<style scoped>
/* ── Layout ─────────────────────────────────────────────────────────────── */

.discover {
  padding-bottom: var(--space-3xl);
}

.feed-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-lg);
  padding-bottom: var(--space-md);
}

.feed-title {
  font-family: var(--font-display);
  font-size: var(--font-size-xl);
  font-weight: 400;
  margin: 0;
  text-transform: lowercase;
}

.feed-body {
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
}

/* Dos columnas en pantallas anchas para "también leyendo" + "lectores afines" */
.feed-top-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--space-md);
  align-items: start;
}

/* Corregir el vertical rhythm excesivo de style.css dentro del grid */
.feed-top-grid section + section {
  margin-top: 0;
}

@media (min-width: 720px) {
  .feed-top-grid {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-md);
    align-items: stretch;
  }

  .feed-top-grid > .feed-section {
    flex: 1 1 300px;
  }

  .feed-top-grid--single > .feed-section {
    flex: 0 0 100%;
  }
}

/* ── Secciones ──────────────────────────────────────────────────────────── */

.feed-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  border: 1px solid var(--border-subtle);
  border-radius: var(--border-radius);
  padding: var(--space-lg);
  background: var(--bg-secondary, transparent);
  min-width: 0;
}

.section-label {
  font-family: var(--font-ui);
  font-size: var(--font-size-xs);
  font-weight: 400;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-tertiary);
  margin: 0;
  padding-bottom: var(--space-sm);
  border-bottom: 1px solid var(--border-subtle);
}

/* ── Filas compactas (también leyendo / lectores afines) ────────────────── */

.compact-list {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.compact-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: var(--space-sm) 0;
  border-bottom: 1px solid var(--border-subtle);
}

.compact-row:last-child {
  border-bottom: none;
}

.compact-row-main {
  display: flex;
  align-items: baseline;
  gap: var(--space-xs);
  flex-wrap: wrap;
  min-width: 0;
}

.nickname-tag {
  font-family: var(--font-display);
  font-size: var(--font-size-sm);
  color: var(--text-primary);
  line-height: 1.4;
}

.row-sep {
  color: var(--text-tertiary);
  font-size: var(--font-size-xs);
}

.book-italic {
  font-size: var(--font-size-xs);
  font-style: italic;
  color: var(--text-tertiary);
  overflow-wrap: anywhere;
}

.row-bio {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  display: block;
  margin-top: 2px;
  line-height: 1.45;
  overflow-wrap: anywhere;
}

.row-btn {
  display: inline-flex;
  align-items: center;
  background: transparent;
  border: none;
  padding: 0;
  font-family: var(--font-ui);
  font-size: var(--font-size-xs);
  font-weight: 300;
  color: var(--text-tertiary);
  cursor: pointer;
  transition: color var(--transition-fast);
  letter-spacing: 0.03em;
  text-transform: lowercase;
  line-height: inherit;
  vertical-align: middle;
}

.row-actions {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  margin-top: 8px;
  line-height: 1;
}

.row-btn-sep {
  color: var(--text-tertiary);
  font-size: 10px;
}

.activity-label {
  font-weight: 500;
  color: var(--text-secondary);
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-right: 4px;
}

.activity-quote {
  font-style: italic;
  color: var(--text-primary);
}

.activity-book {
  display: block;
  font-size: 10px;
  color: var(--text-tertiary);
  margin-top: 2px;
}

.row-btn:hover {
  color: var(--text-primary);
}

.row-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* ── Charlas ────────────────────────────────────────────────────────────── */

.threads-section {
  padding-top: var(--space-lg);
}

.thread-list {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.thread-row {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: var(--space-sm) 0;
  border-bottom: 1px solid var(--border-subtle);
  text-decoration: none;
  transition: opacity var(--transition-fast);
}

.thread-row:last-child {
  border-bottom: none;
}

.thread-row:hover .nickname-tag {
  text-decoration: underline;
  text-underline-offset: 3px;
}

.thread-row-main {
  display: flex;
  gap: var(--space-xs);
  align-items: baseline;
  flex-wrap: wrap;
  min-width: 0;
}

.thread-preview {
  margin: 0;
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  line-height: 1.4;
  overflow-wrap: anywhere;
}

.footer-nick {
  font-family: var(--font-display);
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
}

/* ── Stream de highlights ───────────────────────────────────────────────── */

.highlights-section {
  padding-top: 0;
}

.highlight-stream {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.stream-entry {
  padding: var(--space-md) 0;
  border-bottom: 1px solid var(--border-subtle);
}

.stream-entry:last-child {
  border-bottom: none;
}

.stream-quote {
  margin: 0 0 var(--space-xs) 0;
  font-family: var(--font-display);
  font-size: var(--font-size-sm);
  font-weight: 300;
  line-height: 1.7;
  color: var(--text-primary);
  padding-left: var(--space-md);
  border-left: 1px solid var(--border-subtle);
  overflow-wrap: anywhere;
}

.stream-footer {
  padding-left: var(--space-md);
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  display: flex;
  gap: var(--space-xs);
  align-items: baseline;
  flex-wrap: wrap;
  min-width: 0;
}

.btn-load-more {
  margin-top: var(--space-md);
  background: transparent;
  border: 1px solid var(--border-subtle);
  border-radius: 0;
  padding: 0 var(--space-md);
  min-height: 30px;
  font-family: var(--font-ui);
  font-size: var(--font-size-xs);
  font-weight: 300;
  color: var(--text-tertiary);
  cursor: pointer;
  transition: all var(--transition-fast);
  letter-spacing: 0.04em;
  text-transform: lowercase;
}

.btn-load-more:hover {
  border-color: var(--text-primary);
  color: var(--text-primary);
}

.btn-load-more:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* ── Hermit mode ────────────────────────────────────────────────────────── */

.hermit-notice {
  border: 1px solid var(--border-subtle);
  padding: var(--space-md);
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}

.hermit-text {
  margin: 0;
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
}

.hermit-link {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  text-decoration: none;
  transition: color var(--transition-fast);
}

.hermit-link:hover {
  color: var(--text-primary);
}

/* ── Estados ────────────────────────────────────────────────────────────── */

.empty-state {
  text-align: center;
  padding: var(--space-2xl) 0 var(--space-3xl);
}

.empty-text {
  margin: 0;
  font-family: var(--font-display);
  font-size: var(--font-size-lg);
  font-style: italic;
  color: var(--text-tertiary);
  line-height: 1.6;
}

/* Skeleton loader */
.skeleton-block {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
  padding-top: var(--space-xl);
}

.skeleton-line {
  height: 12px;
  background: var(--border-subtle);
  border-radius: 0;
  animation: shimmer 1.6s ease-in-out infinite;
}

.skeleton-line--wide  { width: 80%; }
.skeleton-line--mid   { width: 55%; }
.skeleton-line--narrow{ width: 35%; }

@keyframes shimmer {
  0%   { opacity: 0.6; }
  50%  { opacity: 1; }
  100% { opacity: 0.6; }
}

@media (max-width: 640px) {
  .feed-section {
    padding: var(--space-md);
  }

  .stream-quote,
  .stream-footer {
    padding-left: var(--space-sm);
  }
}
</style>
