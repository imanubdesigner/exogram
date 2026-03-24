<template>
  <div class="dashboard container">
    <Navbar />

    <!-- Onboarding (solo si no está completado) -->
    <section v-if="!onboardingCompleted" class="onboarding-card card">
      <p class="onboarding-eyebrow">{{ i18n.t('dashboard.onboarding.title') }}</p>

      <div class="onboarding-field">
        <label class="onboarding-label">{{ i18n.t('dashboard.onboarding.nickname_title') }}</label>
        <p class="onboarding-hint">{{ i18n.t('dashboard.onboarding.nickname_desc') }}</p>
        <input
          v-model="nickname"
          type="text"
          :placeholder="i18n.t('dashboard.onboarding.nickname_placeholder')"
          maxlength="50"
          class="mt-sm"
        />
      </div>

      <div class="onboarding-field mt-xl">
        <label class="onboarding-label">{{ i18n.t('dashboard.onboarding.privacy_title') }}</label>
        <p class="onboarding-hint">{{ i18n.t('dashboard.onboarding.privacy_desc') }}</p>
        <label class="checkbox-label mt-sm">
          <input type="checkbox" v-model="hermitMode" />
          <span>{{ i18n.t('dashboard.onboarding.hermit_toggle') }}</span>
        </label>
      </div>

      <div class="onboarding-submit mt-xl">
        <button class="btn btn-primary" @click="saveAndComplete">
          {{ i18n.t('dashboard.onboarding.complete') }}
        </button>
      </div>
    </section>

    <!-- Contenido principal (post-onboarding) -->
    <section v-else class="main-content">
      <!-- Stats centradas -->
      <div class="dash-stats">
        <div class="dash-stat">
          <span class="dash-stat-number">{{ highlightsCount }}</span>
          <span class="dash-stat-label">{{ i18n.t('dashboard.stats.highlights') }}</span>
        </div>
        <span class="dash-sep">·</span>
        <div class="dash-stat">
          <span class="dash-stat-number">{{ booksCount }}</span>
          <span class="dash-stat-label">{{ i18n.t('dashboard.stats.books') }}</span>
        </div>
        <span class="dash-sep">·</span>
        <div class="dash-stat">
          <span class="dash-stat-number">{{ notesCount }}</span>
          <span class="dash-stat-label">{{ i18n.t('dashboard.stats.notes') }}</span>
        </div>
      </div>

      <!-- Mapa de calor tipográfico (Actividad de lectura) -->
      <div v-if="heatmapDays.length > 0" class="heatmap-container">
        <div class="heatmap-nav">
          <button 
            class="heatmap-nav-btn" 
            :disabled="selectedYear <= minYear" 
            :aria-label="i18n.t('dashboard.heatmap.prev_year_aria')"
            @click="changeYear(-1)"
          >←</button>
          <span class="heatmap-year-label">{{ selectedYear }}</span>
          <button 
            class="heatmap-nav-btn" 
            :disabled="selectedYear >= currentYear" 
            :aria-label="i18n.t('dashboard.heatmap.next_year_aria')"
            @click="changeYear(1)"
          >→</button>
        </div>
        
        <div class="heatmap-grid">
          <div 
            v-for="day in heatmapDays" 
            :key="day.date" 
            class="heatmap-day"
            :class="getHeatmapIntensityClass(day.count)"
            :title="day.count > 0
              ? i18n.t('dashboard.heatmap.tooltip_with_count', { count: day.count, date: formatDate(day.date) })
              : i18n.t('dashboard.heatmap.tooltip_empty', { date: formatDate(day.date) })"
          ></div>
        </div>
        <div class="heatmap-legend">
          <span>{{ i18n.t('dashboard.heatmap.less') }}</span>
          <div class="heatmap-day intensity-0"></div>
          <div class="heatmap-day intensity-1"></div>
          <div class="heatmap-day intensity-2"></div>
          <div class="heatmap-day intensity-3"></div>
          <div class="heatmap-day intensity-4"></div>
          <span>{{ i18n.t('dashboard.heatmap.more') }}</span>
        </div>
      </div>

      <section v-if="goodreadsUsername" class="dash-goodreads">
        <h3 class="dash-goodreads-label">{{ i18n.t('dashboard.goodreads.title') }}</h3>
        <div v-if="loadingGoodreadsReading" class="dash-goodreads-state">
          {{ i18n.t('dashboard.goodreads.loading') }}
        </div>
        <div v-else-if="goodreadsReading.length === 0" class="dash-goodreads-state">
          {{ i18n.t('dashboard.goodreads.empty') }}
        </div>
        <div v-else class="dash-goodreads-list">
          <div v-for="item in goodreadsReading" :key="item.book_id" class="dash-goodreads-item">
            <div class="dash-goodreads-main">
              <span class="dash-goodreads-title">{{ item.book_title }}</span>
              <span class="dash-goodreads-authors">{{ item.book_authors.join(', ') }}</span>
            </div>
            <span class="dash-goodreads-progress">{{ item.progress_percent }}%</span>
          </div>
        </div>
      </section>

      <!-- Procesamiento de conexiones semánticas -->
      <div v-if="embeddingMissing > 0" class="embedding-status">
        <div class="embedding-bar-wrap">
          <div
            class="embedding-bar-fill"
            :style="{ width: embeddingProgressPct + '%' }"
          ></div>
        </div>
        <span class="embedding-label">
          {{ i18n.t('dashboard.embeddings', { missing: embeddingMissing, total: embeddingTotal }) }}
        </span>
      </div>

      <!-- Espacio principal: highlights recientes o mensaje de bienvenida -->
      <section v-if="highlightsCount === 0" class="empty-state">
        <p>{{ i18n.t('dashboard.empty') }}</p>
        <button class="btn-subtle-link" @click="uiStore.openModal('import')">{{ i18n.t('dashboard.empty_cta') }}</button>
      </section>

    </section>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useUIStore } from '../stores/ui'
import { useI18nStore } from '../stores/i18n'
import { authService } from '../services/auth'
import { apiRequest } from '../services/api'
import { logger } from '../utils/logger'
import Navbar from '../components/Navbar.vue'

const authStore = useAuthStore()
const uiStore = useUIStore()
const i18n = useI18nStore()

// Estado del onboarding — pre-inicializar con caché para evitar flash de onboarding
const onboardingCompleted = ref(authStore.user?.onboarding_completed ?? false)
const nickname = ref('')
const hermitMode = ref(false)

// Stats y Actividad
const highlightsCount = ref(0)
const booksCount = ref(0)
const notesCount = ref(0)
const activityData = ref([])
const heatmapDays = ref([])
const goodreadsUsername = ref('')
const goodreadsReading = ref([])
const loadingGoodreadsReading = ref(false)

// Estado de embeddings pendientes
const embeddingTotal = ref(0)
const embeddingMissing = ref(0)
const embeddingProgressPct = computed(() => {
  if (!embeddingTotal.value) return 100
  return Math.round(((embeddingTotal.value - embeddingMissing.value) / embeddingTotal.value) * 100)
})
let embeddingPollTimer = null

// Navegación del heatmap
const currentYear = new Date().getFullYear()
const selectedYear = ref(currentYear)
const minYear = ref(currentYear)

// Cargar datos al montar
onUnmounted(() => {
  if (embeddingPollTimer) {
    clearTimeout(embeddingPollTimer)
    embeddingPollTimer = null
  }
})

onMounted(async () => {
  try {
    logger.debug('Montando Dashboard')
    const user = await authStore.refreshCurrentUser()
    if (user) {
      onboardingCompleted.value = user.onboarding_completed
      nickname.value = user.nickname || ''
      hermitMode.value = user.is_hermit_mode || false
      highlightsCount.value = user.highlights_count || 0
      booksCount.value = user.books_count || 0
      notesCount.value = user.notes_count || 0
      goodreadsUsername.value = user.goodreads_username || ''
    }

    // Cargar actividad y estado del perfil
    await Promise.all([
      loadActivityData(),
      loadEmbeddingStatus(),
      loadGoodreadsReading(),
      loadNotesCount()
    ])
  } catch (err) {
    logger.error('Error loading dashboard data', err)
    uiStore.showError(i18n.t('dashboard.messages.load_error'))
  }
})

const loadEmbeddingStatus = async () => {
  try {
    const { highlightService } = await import('../services/highlights')
    const data = await highlightService.getEmbeddingStatus()
    embeddingTotal.value = data.total
    embeddingMissing.value = data.missing

    // Seguir actualizando mientras haya pendientes
    if (data.missing > 0) {
      embeddingPollTimer = setTimeout(loadEmbeddingStatus, 10000)
    } else if (embeddingPollTimer) {
      clearTimeout(embeddingPollTimer)
    }
  } catch (err) {
    logger.warn('No se pudo obtener estado de embeddings', err)
  }
}

const loadGoodreadsReading = async () => {
  if (!goodreadsUsername.value.trim()) {
    goodreadsReading.value = []
    return
  }

  loadingGoodreadsReading.value = true
  try {
    const payload = await authService.getGoodreadsReading()
    goodreadsReading.value = payload.results || []
  } catch (err) {
    logger.error('Error loading Goodreads reading', err)
    goodreadsReading.value = []
  } finally {
    loadingGoodreadsReading.value = false
  }
}

const loadNotesCount = async () => {
  try {
    const payload = await apiRequest('/notes/')
    if (Array.isArray(payload)) {
      notesCount.value = payload.length
      return
    }
    if (Array.isArray(payload?.results)) {
      notesCount.value = payload.results.length
      return
    }
    notesCount.value = 0
  } catch (err) {
    logger.warn('No se pudo obtener conteo de notas', err)
  }
}

const loadActivityData = async () => {
  try {
    logger.debug('Cargando datos de actividad')
    const data = await authStore.getActivityHeatmap()
    activityData.value = data

    // Determinar el año más antiguo de los datos
    if (data.length > 0) {
      const years = data.map(d => parseInt(d.date.substring(0, 4)))
      minYear.value = Math.min(...years)
    }

    generateHeatmapGrid()
  } catch (err) {
    logger.error('Error loading activity data', err)
  }
}

const changeYear = (delta) => {
  const newYear = selectedYear.value + delta
  if (newYear >= minYear.value && newYear <= currentYear) {
    selectedYear.value = newYear
    generateHeatmapGrid()
  }
}

const generateHeatmapGrid = () => {
  const year = selectedYear.value
  const days = []

  // Desde 1 de Enero hasta 31 de Diciembre del año seleccionado
  const startDate = new Date(year, 0, 1)
  const endDate = new Date(year, 11, 31)

  // Mapa para búsqueda rápida
  const activityMap = new Map()
  activityData.value.forEach(item => {
    activityMap.set(item.date, item.count)
  })

  // Generar todos los días del año
  let currentDate = new Date(startDate)
  while (currentDate <= endDate) {
    // Formatear a YYYY-MM-DD localmente para evitar problemas de timezone
    const y = currentDate.getFullYear()
    const m = String(currentDate.getMonth() + 1).padStart(2, '0')
    const d = String(currentDate.getDate()).padStart(2, '0')
    const dateStr = `${y}-${m}-${d}`

    days.push({
      date: dateStr,
      count: activityMap.get(dateStr) || 0
    })

    currentDate.setDate(currentDate.getDate() + 1)
  }

  heatmapDays.value = days
}

const getHeatmapIntensityClass = (count) => {
  if (count === 0) return 'intensity-0'
  if (count <= 3) return 'intensity-1'
  if (count <= 10) return 'intensity-2'
  if (count <= 25) return 'intensity-3'
  return 'intensity-4'
}

const formatDate = (dateStr) => {
  const date = new Date(dateStr)
  const locale = typeof i18n.locale === 'string' ? i18n.locale : i18n.locale?.value
  const localeCode = locale === 'en' ? 'en-US' : 'es-ES'
  return date.toLocaleDateString(localeCode, {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  }).toLowerCase()
}

// Onboarding
const saveAndComplete = async () => {
  if (!nickname.value.trim()) {
    uiStore.showError(i18n.t('dashboard.messages.nickname_required'))
    return
  }
  try {
    logger.debug('Completando onboarding', { nickname: nickname.value, hermitMode: hermitMode.value })
    await authStore.updateProfile({ nickname: nickname.value.trim() })
    await authStore.updatePrivacy({ is_hermit_mode: hermitMode.value })
    await authStore.completeOnboarding()
    onboardingCompleted.value = true
  } catch (err) {
    logger.error('Error completing onboarding', err)
    uiStore.showError(err.message || i18n.t('dashboard.messages.onboarding_error'))
  }
}
</script>

<style scoped>
/* Dashboard layout */
.main-content {
  display: flex;
  flex-direction: column;
  align-items: center; /* Centrar contenido principal verticalmente */
}

/* Embedding status widget */
.embedding-status {
  width: 100%;
  max-width: 760px;
  margin-bottom: var(--space-xl);
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--space-xs);
}

.embedding-bar-wrap {
  width: 100%;
  height: 2px;
  background-color: var(--border-subtle);
  border-radius: 1px;
  overflow: hidden;
}

.embedding-bar-fill {
  height: 100%;
  background-color: var(--text-tertiary);
  border-radius: 1px;
  transition: width 1s ease;
}

.embedding-label {
  font-size: 10px;
  color: var(--text-tertiary);
  font-family: var(--font-ui);
  letter-spacing: 0.03em;
}

/* Stats */
.dash-stats {
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: var(--space-lg);
  margin-bottom: var(--space-xl); /* Reducido para acercar al heatmap */
}

.dash-stat {
  display: flex;
  align-items: baseline;
  gap: var(--space-xs);
}

.dash-stat-number {
  font-family: var(--font-display);
  font-size: var(--font-size-2xl);
  font-weight: 400;
  color: var(--text-primary);
}

.dash-stat-label {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.dash-sep {
  color: var(--text-tertiary);
  font-size: var(--font-size-lg);
}

.dash-goodreads {
  width: 100%;
  max-width: 760px;
  margin-bottom: var(--space-2xl);
}

.dash-goodreads-label {
  font-family: var(--font-ui);
  font-size: var(--font-size-xs);
  font-weight: 400;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-tertiary);
  margin-bottom: var(--space-md);
}

.dash-goodreads-state {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  font-style: italic;
}

.dash-goodreads-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.dash-goodreads-item {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-md);
  padding: var(--space-xs) 0;
  border-bottom: 1px solid var(--border-subtle);
}

.dash-goodreads-item:last-child {
  border-bottom: none;
}

.dash-goodreads-main {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.dash-goodreads-title {
  font-family: var(--font-display);
  font-size: var(--font-size-base);
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.dash-goodreads-authors {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}

.dash-goodreads-progress {
  font-family: var(--font-display);
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  flex-shrink: 0;
}

/* Heatmap Typográfico */
.heatmap-container {
  width: 100%;
  max-width: 760px; /* Suficiente para unos 365 cuadraditos que se van al wrap */
  margin-bottom: var(--space-3xl);
  display: flex;
  flex-direction: column;
  align-items: center; /* Centrar todo el bloque */
}

.heatmap-nav {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  margin-bottom: var(--space-md);
  align-self: flex-start; /* Alineado a la izquierda */
}

.heatmap-year-label {
  font-family: var(--font-display);
  font-size: var(--font-size-base);
  color: var(--text-primary);
  font-weight: 500;
}

.heatmap-nav-btn {
  background: none;
  border: none;
  font-family: var(--font-ui);
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
  cursor: pointer;
  padding: 0;
  transition: color var(--transition-fast);
}

.heatmap-nav-btn:hover:not(:disabled) {
  color: var(--text-primary);
}

.heatmap-nav-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.heatmap-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 3px;
  justify-content: flex-start;
  margin-bottom: var(--space-sm);
}

.heatmap-day {
  width: 10px;
  height: 10px;
  border-radius: 2px;
  background-color: var(--border-subtle);
  transition: transform var(--transition-fast), background-color var(--transition-normal);
}

.heatmap-day:hover {
  transform: scale(1.3);
  z-index: 2;
}

/* Intensidades: escala de grises minimalista en modo claro, invirtiéndose en oscuro (via variables si estuvieran) */
/* Asumiendo que --text-primary es oscuro en light-mode y claro en dark-mode */
.intensity-0 { background-color: var(--bg-tertiary); }
.intensity-1 { background-color: var(--border-medium); opacity: 0.4; }
.intensity-2 { background-color: var(--text-tertiary); opacity: 0.6; }
.intensity-3 { background-color: var(--text-secondary); opacity: 0.8; }
.intensity-4 { background-color: var(--text-primary); }

.heatmap-legend {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 10px;
  color: var(--text-tertiary);
  font-family: var(--font-ui);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  align-self: flex-end; /* Alinear leyenda a la derecha */
}

.heatmap-legend span {
  margin: 0 4px;
}

/* Empty state */
.empty-state {
  text-align: center;
  padding: var(--space-3xl) 0;
}

.empty-state p {
  font-family: var(--font-display);
  font-size: var(--font-size-lg);
  font-style: italic;
  color: var(--text-tertiary);
  margin-bottom: var(--space-lg);
}

.btn-subtle-link {
  background: none;
  border: none;
  padding: 0;
  font-family: var(--font-ui);
  font-size: var(--font-size-sm);
  font-weight: 300;
  color: var(--text-tertiary);
  cursor: pointer;
  transition: color var(--transition-fast);
  border-bottom: 1px solid transparent;
  text-decoration: none;
}

.btn-subtle-link:hover {
  color: var(--text-primary);
  border-bottom-color: var(--text-primary);
}

/* Onboarding */
.onboarding-card {
  max-width: 560px;
  margin: 0 auto;
}

.onboarding-eyebrow {
  font-family: var(--font-ui);
  font-size: var(--font-size-xs);
  font-weight: 400;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--text-tertiary);
  margin-bottom: var(--space-xl);
}

.onboarding-field {
  display: flex;
  flex-direction: column;
}

.onboarding-label {
  font-family: var(--font-display);
  font-size: var(--font-size-base);
  font-weight: 400;
  color: var(--text-primary);
  margin-bottom: var(--space-xs);
}

.onboarding-hint {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  margin-bottom: 0;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  cursor: pointer;
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

.checkbox-label input[type="checkbox"] {
  width: auto;
}

.onboarding-submit {
  border-top: 1px solid var(--border-subtle);
  padding-top: var(--space-lg);
}

@media (max-width: 640px) {
  .dash-stat-number {
    font-size: var(--font-size-xl);
  }
}
</style>
