<template>
  <div class="thread-page container">
    <Navbar />

    <header class="thread-header">
      <router-link to="/descubrir" class="back-link">← feed</router-link>
      <div v-if="thread" class="thread-meta">
        <span class="thread-with">charla con</span>
        <span class="thread-nickname">@{{ thread.other_nickname }}</span>
        <span v-if="thread.context_book_title" class="thread-book">
          · {{ thread.context_book_title }}
        </span>
      </div>
    </header>

    <div v-if="loading" class="state-msg">cargando...</div>

    <div v-else-if="error" class="state-msg error">{{ error }}</div>

    <template v-else>
      <!-- Mensajes -->
      <div class="messages-wrapper" ref="messagesEl">
        <div v-if="hasPreviousMessages" class="load-previous-wrapper">
          <button class="btn-load-previous" @click="loadPreviousMessages">
            ver anteriores ({{ messages.length - paginatedMessages.length }})
          </button>
        </div>

        <div v-if="messages.length === 0" class="empty-messages">
          <p class="empty-text">todavía no hay nada. escribí algo.</p>
        </div>
        <div v-else class="messages-list">
          <div
            v-for="msg in paginatedMessages"
            :key="msg.id"
            :class="['message-row', { 'message-own': msg.author === myNickname }]"
          >
            <p class="message-content">{{ msg.content }}</p>
            <span class="message-meta">
              {{ msg.author === myNickname ? 'vos' : `@${msg.author}` }}
              · {{ formatDate(msg.created_at) }}
            </span>
          </div>
        </div>
      </div>

      <!-- Input reply -->
      <form class="reply-form" @submit.prevent="submitMessage">
        <textarea
          v-model="newMessage"
          class="reply-input"
          placeholder="tu respuesta..."
          rows="3"
          maxlength="2000"
          :disabled="sending"
          @keydown.ctrl.enter="submitMessage"
          @keydown.meta.enter="submitMessage"
        />
        <div class="reply-actions">
          <span class="char-count">{{ newMessage.length }}/2000</span>
          <button type="submit" class="btn-action" :disabled="sending || !newMessage.trim()">
            {{ sending ? '...' : 'enviar' }}
          </button>
        </div>
      </form>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useUIStore } from '../stores/ui'
import { feedService } from '../services/feed'
import { logger } from '../utils/logger'
import Navbar from '../components/Navbar.vue'

const route = useRoute()
const authStore = useAuthStore()
const uiStore = useUIStore()

const POLL_INTERVAL_MIN = 5000
const POLL_INTERVAL_MAX = 60000

const threadId = computed(() => route.params.threadId)
const myNickname = computed(() => authStore.user?.nickname)

const thread = ref(null)
const messages = ref([])
const loading = ref(true)
const error = ref(null)
const sending = ref(false)
const newMessage = ref('')
const messagesEl = ref(null)
const currentPollInterval = ref(POLL_INTERVAL_MIN)

const visibleMessagesCount = ref(5)

const hasPreviousMessages = computed(() => messages.value.length > visibleMessagesCount.value)

const paginatedMessages = computed(() => {
  if (messages.value.length <= visibleMessagesCount.value) return messages.value
  return messages.value.slice(-visibleMessagesCount.value)
})

let pollTimeout = null
let pollInFlight = false
let pollController = null

onMounted(async () => {
  await loadThread()
  if (thread.value) startPolling()
})

onUnmounted(() => {
  // Evita memory leaks y requests fantasma cuando el usuario sale del hilo.
  stopPolling()
  if (pollController) {
    pollController.abort()
    pollController = null
  }
})

async function loadThread() {
  loading.value = true
  error.value = null
  try {
    const data = await feedService.getThread(threadId.value)
    thread.value = data.thread
    messages.value = data.messages || []
    await nextTick()
    scrollToBottom()
  } catch (err) {
    logger.error('Error cargando hilo', err)
    error.value = 'no se pudo cargar el hilo'
  } finally {
    loading.value = false
  }
}

async function pollMessages() {
  if (!thread.value || pollInFlight) return
  pollInFlight = true
  pollController = new AbortController()
  try {
    const data = await feedService.getThread(threadId.value, null, pollController.signal)
    const nextMessages = data.messages || []
    const previousLastId = messages.value[messages.value.length - 1]?.id
    const nextLastId = nextMessages[nextMessages.length - 1]?.id
    const hasNewMessages =
      nextMessages.length > messages.value.length || nextLastId !== previousLastId

    if (hasNewMessages) {
      currentPollInterval.value = POLL_INTERVAL_MIN
      messages.value = nextMessages
      await nextTick()
      scrollToBottom()
      return
    }

    currentPollInterval.value = Math.min(currentPollInterval.value * 2, POLL_INTERVAL_MAX)
  } catch (err) {
    // AbortError: el componente se desmontó mientras había un poll en vuelo.
    if (err?.name === 'AbortError') return
    // Un 429 en polling no es fatal: degradamos con backoff en vez de mostrar error.
    if (err?.status === 429) {
      currentPollInterval.value = POLL_INTERVAL_MAX
      logger.warn('[thread polling] throttled (429). Applying max backoff.')
      return
    }
    // silencioso en polling
  } finally {
    pollController = null
    pollInFlight = false
  }
}

async function submitMessage() {
  const content = newMessage.value.trim()
  if (!content || sending.value) return

  sending.value = true
  try {
    const msg = await feedService.sendMessage(threadId.value, content)
    messages.value.push(msg)
    newMessage.value = ''
    await nextTick()
    scrollToBottom()
    currentPollInterval.value = POLL_INTERVAL_MIN
    await triggerImmediatePoll()
  } catch (err) {
    uiStore.showError(err.message || 'No se pudo enviar')
  } finally {
    sending.value = false
  }
}

/*
 * Estrategia de polling adaptativo:
 * - intervalo mínimo cuando hay actividad
 * - backoff exponencial cuando el hilo está inactivo
 * - reset inmediato al enviar mensaje del usuario
 * Esto reduce ~80% de requests en conversaciones inactivas y mantiene
 * baja latencia cuando el intercambio está activo.
 */
function startPolling() {
  currentPollInterval.value = POLL_INTERVAL_MIN
  scheduleNextPoll(POLL_INTERVAL_MIN)
}

function stopPolling() {
  if (pollTimeout) {
    clearTimeout(pollTimeout)
    pollTimeout = null
  }
}

function scheduleNextPoll(delay = currentPollInterval.value) {
  stopPolling()
  pollTimeout = setTimeout(async () => {
    await pollMessages()
    scheduleNextPoll(currentPollInterval.value)
  }, delay)
}

async function triggerImmediatePoll() {
  stopPolling()
  await pollMessages()
  scheduleNextPoll(POLL_INTERVAL_MIN)
}

function scrollToBottom() {
  if (messagesEl.value) {
    messagesEl.value.scrollTop = messagesEl.value.scrollHeight
  }
}

function loadPreviousMessages() {
  visibleMessagesCount.value += 5
}

function formatDate(iso) {
  const d = new Date(iso)
  return d.toLocaleString('es-AR', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).toLowerCase()
}
</script>

<style scoped>
.thread-page {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
  padding-bottom: var(--space-3xl);
}

.thread-header {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}

.back-link {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  text-decoration: none;
  letter-spacing: 0.03em;
}

.back-link:hover {
  color: var(--text-primary);
}

.thread-meta {
  display: flex;
  align-items: baseline;
  gap: var(--space-xs);
  flex-wrap: wrap;
}

.thread-with {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}

.thread-nickname {
  font-family: var(--font-display);
  font-size: var(--font-size-base);
  color: var(--text-primary);
}

.thread-book {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  font-style: italic;
}

/* Mensajes */
.messages-wrapper {
  border: 1px solid var(--border-subtle);
  min-height: 300px;
  max-height: 60vh;
  overflow-y: auto;
  padding: var(--space-md);
  display: flex;
  flex-direction: column;
}

.load-previous-wrapper {
  display: flex;
  justify-content: center;
  padding-bottom: var(--space-md);
  margin-bottom: auto; /* Push down the rest */
}

.btn-load-previous {
  background: transparent;
  border: 1px solid var(--border-subtle);
  border-radius: 0;
  padding: 4px 12px;
  font-family: var(--font-ui);
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  cursor: pointer;
  transition: all var(--transition-fast);
  letter-spacing: 0.04em;
}

.btn-load-previous:hover {
  border-color: var(--text-primary);
  color: var(--text-primary);
  background: rgba(10, 10, 10, 0.04);
}

.messages-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
  flex: 1;
}

.empty-messages {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
}

.empty-text {
  color: var(--text-tertiary);
  font-size: var(--font-size-sm);
  font-style: italic;
}

.message-row {
  display: flex;
  flex-direction: column;
  gap: 2px;
  max-width: 80%;
}

.message-own {
  align-self: flex-end;
  align-items: flex-end;
}

.message-content {
  margin: 0;
  font-size: var(--font-size-sm);
  color: var(--text-primary);
  line-height: 1.6;
  padding: var(--space-sm) var(--space-md);
  border: 1px solid var(--border-subtle);
  background: var(--bg-secondary, transparent);
}

.message-own .message-content {
  background: rgba(10, 10, 10, 0.04);
}

.message-meta {
  font-size: 10px;
  color: var(--text-tertiary);
  letter-spacing: 0.02em;
}

/* Input */
.reply-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
  border: 1px solid var(--border-subtle);
  padding: var(--space-md);
}

.reply-input {
  width: 100%;
  background: transparent;
  border: none;
  outline: none;
  resize: vertical;
  font-family: var(--font-ui);
  font-size: var(--font-size-sm);
  color: var(--text-primary);
  line-height: 1.6;
  min-height: 72px;
}

.reply-input::placeholder {
  color: var(--text-tertiary);
  font-style: italic;
}

.reply-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.char-count {
  font-size: 10px;
  color: var(--text-tertiary);
}

.btn-action {
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
  font-weight: 300;
  color: var(--text-tertiary);
  cursor: pointer;
  transition: all var(--transition-fast);
  letter-spacing: 0.04em;
  text-transform: lowercase;
}

.btn-action:hover {
  border-color: var(--text-primary);
  color: var(--text-primary);
}

.btn-action:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.state-msg {
  padding: var(--space-xl) 0;
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
}

.state-msg.error {
  color: var(--color-error, #c0392b);
}
</style>
