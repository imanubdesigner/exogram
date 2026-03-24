<template>
  <div class="public-profile container">
    <div v-if="isOwner" class="owner-nav">
      <router-link to="/dashboard" class="link-subtle">← volver al dashboard</router-link>
    </div>

    <div v-if="loading" class="state-msg">
      cargando...
    </div>

    <div v-else-if="error" class="state-msg error">
      {{ error }}
    </div>

    <div v-else-if="!profile" class="empty-state">
      <p class="empty-text">perfil no encontrado o no es público</p>
      <router-link to="/" class="link-subtle">volver al inicio →</router-link>
    </div>

    <div v-else class="profile-content">
      <header class="profile-header">
        <div class="header-main">
          <div class="header-copy">
            <h1 class="nickname">{{ profile.nickname }}</h1>
            <p v-if="profile.bio" class="bio">{{ profile.bio }}</p>
          </div>

          <div class="header-side">
            <div class="tab-switcher">
              <button
                class="tab-btn"
                :class="{ active: activeTab === 'highlights' }"
                @click="activeTab = 'highlights'"
              >
                highlights <span class="tab-count">{{ sortedHighlights.length }}</span>
              </button>
              <button
                class="tab-btn"
                :class="{ active: activeTab === 'notes' }"
                @click="activeTab = 'notes'"
              >
                notas <span class="tab-count">{{ sortedPublicNotes.length }}</span>
              </button>
            </div>

            <div v-if="!isOwner && isAuthenticated" class="header-actions">
              <button 
                class="btn-option" 
                :class="{ 'is-active': isFollowing }"
                @click="toggleFollow"
                :disabled="followLoading"
              >
                {{ isFollowing ? 'siguiendo' : 'seguir' }}
              </button>
            </div>
          </div>
        </div>
      </header>

      <section v-if="activeTab === 'highlights'" class="public-section">
        <div v-if="sortedHighlights.length === 0" class="section-empty">no hay highlights públicos todavía</div>

        <div v-else class="feed-list">
          <article v-for="h in paginatedHighlights" :key="h.id" class="entry-card">
            <div class="entry-meta">
              <span class="entry-date">{{ formatDate(getHighlightDisplayDate(h)) }}</span>
            </div>

            <blockquote class="quote">
              <p>{{ h.content }}</p>
              <cite>{{ h.book_title }} — {{ (h.book_authors || []).join(', ') }}</cite>
            </blockquote>

            <p v-if="h.note" class="entry-note">{{ h.note }}</p>

            <div class="entry-actions">
              <button
                class="btn-option btn-option-sm"
                @click="toggleComments(h.id)"
                :title="commentsExpanded[h.id] ? 'ocultar comentarios' : 'ver comentarios'"
              >
                {{ commentsExpanded[h.id] ? 'ocultar comentarios' : 'ver comentarios' }}
                <span v-if="getCommentCount(h) > 0" class="inline-count">({{ getCommentCount(h) }})</span>
              </button>
            </div>

            <div v-if="commentsExpanded[h.id]" class="comments-panel">
              <p v-if="commentsLoading[h.id]" class="comments-state">cargando comentarios...</p>
              <p v-else-if="commentsErrors[h.id]" class="comments-state comments-error">
                {{ commentsErrors[h.id] }}
              </p>

              <template v-else>
                <div v-if="getCommentsList(h.id).length > 0" class="comments-list">
                  <article v-for="c in getCommentsList(h.id)" :key="c.id" class="comment-item">
                    <div class="comment-header">
                      <span class="comment-author">@{{ c.author_nickname }}</span>
                      <span class="comment-date">{{ formatDate(c.created_at) }}</span>
                    </div>
                    <p class="comment-content">{{ c.content }}</p>
                  </article>
                </div>
                <p v-else class="comments-state">sé el primero en comentar.</p>

                <div v-if="isAuthenticated" class="comment-form">
                  <textarea
                    v-model="newComments[h.id]"
                    placeholder="escribe un comentario..."
                    rows="2"
                    class="comment-input"
                    maxlength="1000"
                  ></textarea>
                  <div class="comment-actions">
                    <button
                      @click="postComment(h.id)"
                      :disabled="!newComments[h.id] || posting[h.id]"
                      class="btn-option btn-option-sm"
                    >
                      {{ posting[h.id] ? 'enviando...' : 'comentar' }}
                    </button>
                    <span v-if="commentErrors[h.id]" class="comment-inline-error">{{ commentErrors[h.id] }}</span>
                  </div>
                </div>
                <p v-else class="comments-state">inicia sesión para comentar.</p>
              </template>
            </div>
          </article>
        </div>

        <PaginationControl 
          v-model="highlightsPage" 
          :total-items="sortedHighlights.length" 
          :page-size="5" 
        />
      </section>

      <section v-else class="public-section">
        <p v-if="sortedPublicNotes.length === 0" class="section-empty">no hay notas públicas todavía</p>

        <div v-else class="feed-list">
          <article v-for="note in paginatedPublicNotes" :key="note.id" class="entry-card note-card">
            <div class="entry-meta">
              <span class="entry-date">{{ formatDate(getNoteDisplayDate(note)) }}</span>
            </div>
            <p class="note-content">{{ note.content }}</p>
          </article>
        </div>

        <PaginationControl 
          v-model="notesPage" 
          :total-items="sortedPublicNotes.length" 
          :page-size="5" 
        />
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import { apiFetch, apiRequest } from '../services/api'
import { highlightService } from '../services/highlights'
import { authService } from '../services/auth'
import { socialService } from '../services/social'
import { logger } from '../utils/logger'
import PaginationControl from '../components/PaginationControl.vue'

const route = useRoute()

const loading = ref(true)
const error = ref(null)
const profile = ref(null)
const highlights = ref([])
const publicNotes = ref([])
const isOwner = ref(false)
const activeTab = ref('highlights')
const viewerNickname = ref('')
const isAuthenticated = computed(() => !!viewerNickname.value || authService.isAuthenticated())

const isFollowing = ref(false)
const followLoading = ref(false)

const highlightsPage = ref(1)
const notesPage = ref(1)

watch(activeTab, () => {
  highlightsPage.value = 1
  notesPage.value = 1
})

const commentsByHighlight = ref({})
const commentsExpanded = ref({})
const commentsLoading = ref({})
const commentsLoaded = ref({})
const commentsErrors = ref({})

const newComments = ref({})
const posting = ref({})
const commentErrors = ref({})

const getHighlightDisplayDate = (highlight) => highlight?.published_at || highlight?.created_at
const getNoteDisplayDate = (note) => note?.updated_at || note?.created_at

const sortedHighlights = computed(() =>
  [...highlights.value].sort((a, b) => {
    const dateA = getHighlightDisplayDate(a)
    const dateB = getHighlightDisplayDate(b)
    if (!dateA || !dateB) return 0
    return new Date(dateB) - new Date(dateA)
  })
)

const sortedPublicNotes = computed(() =>
  [...publicNotes.value].sort((a, b) => {
    const dateA = getNoteDisplayDate(a)
    const dateB = getNoteDisplayDate(b)
    if (!dateA || !dateB) return 0
    return new Date(dateB) - new Date(dateA)
  })
)

const paginatedHighlights = computed(() => {
  const start = (highlightsPage.value - 1) * 5
  return sortedHighlights.value.slice(start, start + 5)
})

const paginatedPublicNotes = computed(() => {
  const start = (notesPage.value - 1) * 5
  return sortedPublicNotes.value.slice(start, start + 5)
})

const resetVisibleCounts = () => {
  highlightsPage.value = 1
  notesPage.value = 1
}

const resetCommentsState = () => {
  commentsByHighlight.value = {}
  commentsExpanded.value = {}
  commentsLoading.value = {}
  commentsLoaded.value = {}
  commentsErrors.value = {}
  newComments.value = {}
  posting.value = {}
  commentErrors.value = {}
}

const getCommentsList = (highlightId) => commentsByHighlight.value[highlightId] || []

const getCommentCount = (highlight) => {
  if (commentsLoaded.value[highlight.id]) {
    return getCommentsList(highlight.id).length
  }
  return Number.isFinite(highlight.comment_count) ? highlight.comment_count : 0
}

const loadComments = async (highlightId) => {
  commentsLoading.value[highlightId] = true
  commentsErrors.value[highlightId] = null
  try {
    const comments = await highlightService.getComments(highlightId)
    commentsByHighlight.value[highlightId] = Array.isArray(comments) ? comments : []
    commentsLoaded.value[highlightId] = true
  } catch (err) {
    commentsErrors.value[highlightId] = err.message || 'no se pudieron cargar los comentarios'
  } finally {
    commentsLoading.value[highlightId] = false
  }
}

const toggleComments = async (highlightId) => {
  const alreadyOpen = !!commentsExpanded.value[highlightId]
  commentsExpanded.value[highlightId] = !alreadyOpen

  if (!alreadyOpen && !commentsLoaded.value[highlightId]) {
    await loadComments(highlightId)
  }
}

const postComment = async (highlightId) => {
  const content = (newComments.value[highlightId] || '').trim()
  if (!content) return

  posting.value[highlightId] = true
  commentErrors.value[highlightId] = null

  try {
    if (!commentsLoaded.value[highlightId]) {
      await loadComments(highlightId)
    }

    const comment = await highlightService.postComment(highlightId, content)
    if (!Array.isArray(commentsByHighlight.value[highlightId])) {
      commentsByHighlight.value[highlightId] = []
    }
    commentsByHighlight.value[highlightId].push(comment)
    commentsLoaded.value[highlightId] = true
    commentsExpanded.value[highlightId] = true

    const target = highlights.value.find(item => item.id === highlightId)
    if (target) {
      target.comment_count = (Number(target.comment_count) || 0) + 1
    }

    newComments.value[highlightId] = ''
  } catch (err) {
    commentErrors.value[highlightId] = err.message || 'no tienes permiso para comentar en esta nota'
  } finally {
    posting.value[highlightId] = false
  }
}

const fetchPublicNotes = async (nickname) => {
  try {
    const notes = await apiRequest(`/users/${nickname}/notes/`)
    return Array.isArray(notes) ? notes : []
  } catch (err) {
    logger.error('Error loading public notes endpoint:', err)
  }

  if (isOwner.value) {
    try {
      const ownNotes = await apiRequest('/notes/')
      return ownNotes.filter(note => note.visibility === 'public')
    } catch (err) {
      logger.error('Error loading own notes fallback:', err)
    }
  }

  return []
}

const resolveViewerNickname = async () => {
  viewerNickname.value = ''
  try {
    const currentUser = await authService.getCurrentUser()
    const resolvedNickname = currentUser?.nickname || ''
    viewerNickname.value = resolvedNickname
    return resolvedNickname
  } catch (err) {
    logger.error('Error resolving current user in public profile:', err)
    return ''
  }
}

const loadPublicProfile = async (nickname) => {
  loading.value = true
  error.value = null
  profile.value = null
  highlights.value = []
  publicNotes.value = []
  isOwner.value = false
  viewerNickname.value = ''
  activeTab.value = 'highlights'
  resetVisibleCounts()
  resetCommentsState()

  try {
    const currentViewerNickname = await resolveViewerNickname()
    isOwner.value = currentViewerNickname === nickname

    const profileRes = await apiFetch(`/users/${nickname}/`)

    if (profileRes.status === 404) {
      profile.value = null
      return
    }

    if (!profileRes.ok) {
      throw new Error('error cargando perfil')
    }

    profile.value = await profileRes.json()

    if (!isOwner.value && isAuthenticated.value) {
      isFollowing.value = await socialService.checkFollow(nickname)
    }

    const [fetchedHighlights, fetchedNotes] = await Promise.all([
      highlightService.getPublicHighlights(nickname),
      fetchPublicNotes(nickname)
    ])

    highlights.value = Array.isArray(fetchedHighlights) ? fetchedHighlights : []
    publicNotes.value = Array.isArray(fetchedNotes) ? fetchedNotes : []
  } catch (err) {
    logger.error(err)
    error.value = 'no se pudo cargar el perfil'
  } finally {
    loading.value = false
  }
}

const handleSessionFocus = async () => {
  const currentNickname = route.params.nickname
  if (typeof currentNickname !== 'string' || !currentNickname.trim()) return
  const resolvedNickname = await resolveViewerNickname()
  isOwner.value = resolvedNickname === currentNickname.trim()
}

const toggleFollow = async () => {
  if (!profile.value || followLoading.value) return
  
  followLoading.value = true
  try {
    if (isFollowing.value) {
      await socialService.unfollow(profile.value.nickname)
      isFollowing.value = false
    } else {
      await socialService.follow(profile.value.nickname)
      isFollowing.value = true
    }
  } catch (err) {
    logger.error('Error toggling follow status', err)
  } finally {
    followLoading.value = false
  }
}

watch(
  () => route.params.nickname,
  (nextNickname) => {
    if (typeof nextNickname === 'string' && nextNickname.trim()) {
      loadPublicProfile(nextNickname.trim())
    }
  },
  { immediate: true }
)

onMounted(() => {
  window.addEventListener('focus', handleSessionFocus)
})

onBeforeUnmount(() => {
  window.removeEventListener('focus', handleSessionFocus)
})

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString('es-ES', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  }).toLowerCase()
}
</script>

<style scoped>
.public-profile {
  max-width: 680px;
  margin: 0 auto;
  padding-top: var(--space-2xl);
  padding-bottom: var(--space-3xl);
}

.owner-nav {
  margin-bottom: var(--space-md);
  display: flex;
  justify-content: flex-end;
}

.state-msg {
  text-align: center;
  padding: var(--space-3xl) 0;
  color: var(--text-tertiary);
  font-size: var(--font-size-sm);
}

.state-msg.error {
  color: #991B1B;
}

.empty-state {
  text-align: center;
  padding: var(--space-3xl) 0;
}

.empty-text {
  font-family: var(--font-display);
  font-size: var(--font-size-lg);
  font-style: italic;
  color: var(--text-tertiary);
  margin: 0 0 var(--space-md) 0;
}

.link-subtle {
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
  text-decoration: none;
  transition: color var(--transition-fast);
}

.link-subtle:hover {
  color: var(--text-primary);
}

.profile-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.profile-header {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
  padding-bottom: var(--space-xl);
  border-bottom: 1px solid var(--border-subtle);
}

.header-main {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-xl);
}

.header-copy {
  flex: 1 1 auto;
  min-width: 0;
}

.nickname {
  margin: 0;
  font-family: var(--font-display);
  font-size: var(--font-size-xl);
  font-weight: 400;
  color: var(--text-primary);
  line-height: 1.2;
}

.bio {
  margin: var(--space-sm) 0 0;
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  line-height: 1.65;
  font-style: italic;
  white-space: pre-wrap;
}

.header-side {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: var(--space-md);
  flex: 0 0 auto;
  padding-top: var(--space-xs);
}

.header-actions {
  display: flex;
  justify-content: flex-end;
}

.tab-switcher {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-sm);
  flex-wrap: wrap;
}

.tab-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-xs);
  min-height: 32px;
  background: transparent;
  border: 1px solid var(--border-subtle);
  border-radius: 0;
  padding: 0 var(--space-md);
  font-family: var(--font-ui);
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  text-transform: lowercase;
  letter-spacing: 0.04em;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.tab-btn:hover {
  border-color: var(--text-primary);
  color: var(--text-primary);
  background: rgba(10, 10, 10, 0.04);
}

.tab-btn.active {
  border-color: var(--text-primary);
  color: var(--text-primary);
}

.tab-count {
  color: var(--text-secondary);
}

.public-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.section-empty {
  margin: 0;
  padding-top: var(--space-lg);
  text-align: center;
  font-family: var(--font-display);
  font-size: var(--font-size-lg);
  font-style: italic;
  color: var(--text-tertiary);
}

.feed-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
}

.entry-card {
  border: 1px solid var(--border-subtle);
  border-radius: 0;
  background: var(--bg-secondary);
  padding: var(--space-lg);
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.entry-meta {
  display: flex;
  justify-content: flex-end;
}

.entry-date {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  letter-spacing: 0.05em;
  text-transform: lowercase;
}

.quote {
  margin: 0;
  padding-left: var(--space-md);
  border-left: 1px solid var(--border-medium);
}

.quote p {
  margin: 0 0 var(--space-sm) 0;
  font-family: var(--font-display);
  font-size: var(--font-size-lg);
  line-height: 1.6;
  color: var(--text-primary);
  white-space: pre-wrap;
}

.quote cite {
  display: block;
  margin: 0;
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
  font-style: normal;
}

.entry-note {
  margin: 0;
  font-size: var(--font-size-base);
  color: var(--text-secondary);
  line-height: 1.6;
  white-space: pre-wrap;
}

.entry-actions {
  display: flex;
  justify-content: flex-end;
}

.inline-count {
  margin-left: 2px;
}

.comments-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
  padding-top: var(--space-md);
  border-top: 1px solid var(--border-subtle);
}

.comments-state {
  margin: 0;
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}

.comments-error,
.comment-inline-error {
  color: #991B1B;
}

.comments-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.comment-item {
  border: 1px solid var(--border-subtle);
  border-radius: 0;
  background: rgba(10, 10, 10, 0.02);
  padding: var(--space-md);
}

.comment-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-sm);
  margin-bottom: var(--space-xs);
}

.comment-author {
  font-family: var(--font-display);
  font-size: var(--font-size-sm);
  color: var(--text-primary);
}

.comment-date {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}

.comment-content {
  margin: 0;
  font-size: var(--font-size-sm);
  line-height: 1.55;
  color: var(--text-secondary);
  white-space: pre-wrap;
}

.comment-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.comment-input {
  width: 100%;
  border: 1px solid var(--border-subtle);
  border-radius: 0;
  padding: var(--space-md);
  background: transparent;
  color: var(--text-primary);
  font-family: var(--font-ui);
  font-size: var(--font-size-sm);
  line-height: 1.5;
  resize: vertical;
}

.comment-input:focus {
  outline: none;
  border-color: var(--text-primary);
}

.comment-actions {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  flex-wrap: wrap;
}

.note-card {
  padding: var(--space-xl);
}

.note-card .note-content {
  margin: 0;
  font-family: var(--font-display);
  font-size: var(--font-size-lg);
  color: var(--text-primary);
  line-height: 1.6;
  white-space: pre-wrap;
}

.load-more-wrap {
  display: flex;
  justify-content: center;
  padding-top: var(--space-sm);
}

.btn-option {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 32px;
  background: transparent;
  border: 1px solid var(--border-subtle);
  border-radius: 0;
  padding: 0 var(--space-md);
  font-family: var(--font-ui);
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  letter-spacing: 0.04em;
  text-transform: lowercase;
  cursor: pointer;
  transition: all var(--transition-fast);
  text-decoration: none;
}

.btn-option:hover,
.btn-option.is-active {
  border-color: var(--text-primary);
  background: rgba(10, 10, 10, 0.04);
  color: var(--text-primary);
}

.btn-option:disabled {
  opacity: 0.5;
  cursor: wait;
}

.btn-option-sm {
  min-height: 30px;
  padding: 0 var(--space-sm);
}

@media (max-width: 640px) {
  .public-profile {
    padding-top: var(--space-xl);
  }

  .header-main {
    flex-direction: column;
    gap: var(--space-md);
  }

  .header-side {
    width: 100%;
    align-items: flex-start;
    gap: var(--space-sm);
    padding-top: 0;
  }

  .nickname {
    font-size: var(--font-size-lg);
  }

  .quote p {
    font-size: var(--font-size-base);
  }

  .note-card .note-content {
    font-size: var(--font-size-base);
  }

  .tab-switcher {
    gap: var(--space-xs);
  }

  .tab-btn,
  .btn-option {
    min-height: 30px;
  }

  .entry-card {
    padding: var(--space-md);
  }

  .note-card {
    padding: var(--space-lg);
  }

  .header-actions {
    justify-content: flex-start;
  }

  .tab-switcher {
    justify-content: flex-start;
  }
}
</style>
