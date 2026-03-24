<template>
  <div class="container">
    <Navbar />

    <!-- Paso 1: Upload -->
    <section v-if="step === 'upload'" class="step-upload panel-shell">
      <p class="step-hint">{{ i18n.t('import_view.step_hint') }}</p>

      <div
        class="drop-area"
        :class="{ 'dragging': isDragging }"
        @drop.prevent="handleFileDrop"
        @dragover.prevent="isDragging = true"
        @dragleave.prevent="isDragging = false"
      >
        <span class="drop-label">{{ i18n.t('import_view.drop_label') }}</span>
        <span class="drop-or">{{ i18n.t('import_view.drop_or') }}</span>
        <label for="file-input" class="link-action select-file-link">{{ i18n.t('import_view.select_file') }}</label>
        <input
          id="file-input"
          type="file"
          accept=".txt"
          @change="handleFileSelect"
          style="display: none;"
        />
      </div>

      <p v-if="error" class="feedback error">{{ error }}</p>
    </section>

    <!-- Paso 2: Preview -->
    <section v-if="step === 'preview'" class="step-preview panel-shell">
      <div class="preview-summary">
        <span class="summary-number">{{ parsed.new_count }}</span>
        <span class="summary-label">{{ i18n.t('import_view.summary_new_highlights') }}</span>
        <span v-if="parsed.existing_count > 0" class="summary-detail">
          {{ i18n.t('import_view.summary_existing_books', { existing: parsed.existing_count, books: parsed.books_found }) }}
        </span>
        <span v-else class="summary-detail">{{ i18n.t('import_view.summary_books', { books: parsed.books_found }) }}</span>
      </div>

      <p class="import-note">
        {{ i18n.t('import_view.privacy_note') }}
      </p>

      <div class="preview-books">
        <div v-for="(book, idx) in newGroupedByBook" :key="idx" class="preview-book">
          <div class="preview-book-head">
            <span class="pb-title">{{ book.title }}</span>
            <span class="pb-meta">{{ i18n.t('import_view.preview_meta', { author: book.author, count: book.highlights.length }) }}</span>
          </div>

          <blockquote
            v-for="(h, hidx) in book.highlights.slice(0, 2)"
            :key="hidx"
            class="preview-quote"
          >
            <p>{{ h.content }}</p>
          </blockquote>

          <span v-if="book.highlights.length > 2" class="preview-more">
            {{ i18n.t('import_view.preview_more', { count: book.highlights.length - 2 }) }}
          </span>
        </div>
      </div>

      <!-- Sticky footer -->
      <div class="sticky-actions">
        <button @click="step = 'upload'" class="link-action">{{ i18n.t('import_view.back') }}</button>
        <button
          v-if="parsed.new_count > 0"
          @click="importHighlights"
          class="link-action action-primary"
          :disabled="importing"
        >
          {{ importing ? i18n.t('import_view.importing') : i18n.t('import_view.import_button', { count: parsed.new_count }) }}
        </button>
        <span v-else class="no-new">{{ i18n.t('import_view.no_new') }}</span>
      </div>

      <p v-if="error" class="feedback error">{{ error }}</p>
    </section>

    <!-- Paso 3: Resultado -->
    <section v-if="step === 'result'" class="step-result panel-shell">
      <div class="result-stats">
        <div class="result-stat">
          <span class="rs-number">{{ result.imported }}</span>
          <span class="rs-label">{{ i18n.t('import_view.result_imported') }}</span>
        </div>
        <span class="rs-sep">·</span>
        <div class="result-stat">
          <span class="rs-number">{{ result.books_created }}</span>
          <span class="rs-label">{{ i18n.t('import_view.result_new_books') }}</span>
        </div>
        <span v-if="result.skipped_duplicates > 0" class="rs-sep">·</span>
        <div v-if="result.skipped_duplicates > 0" class="result-stat">
          <span class="rs-number">{{ result.skipped_duplicates }}</span>
          <span class="rs-label">{{ i18n.t('import_view.result_duplicates') }}</span>
        </div>
      </div>

      <div class="step-actions">
        <button @click="resetImport" class="link-action">{{ i18n.t('import_view.import_another') }}</button>
        <router-link to="/biblioteca" class="link-action">{{ i18n.t('import_view.view_library') }}</router-link>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useUIStore } from '../stores/ui'
import { useI18nStore } from '../stores/i18n'
import { highlightService } from '../services/highlights'
import { logger } from '../utils/logger'
import Navbar from '../components/Navbar.vue'

const uiStore = useUIStore()
const i18n = useI18nStore()
const step = ref('upload')
const isDragging = ref(false)
const error = ref(null)
const parsed = ref(null)
const importing = ref(false)
const result = ref(null)

// Solo agrupar los highlights NUEVOS
const newGroupedByBook = computed(() => {
  if (!parsed.value) return []

  const grouped = {}

  for (const h of parsed.value.highlights) {
    if (!h.is_new) continue
    const key = h.title
    if (!grouped[key]) {
      grouped[key] = {
        title: h.title,
        author: h.author,
        highlights: []
      }
    }
    grouped[key].highlights.push(h)
  }

  return Object.values(grouped)
})

const handleFileDrop = async (e) => {
  isDragging.value = false
  const file = e.dataTransfer.files[0]
  if (file) {
    await uploadFile(file)
  }
}

const handleFileSelect = async (e) => {
  const file = e.target.files[0]
  if (file) {
    await uploadFile(file)
  }
}

const uploadFile = async (file) => {
  error.value = null

  if (!file.name.endsWith('.txt')) {
    error.value = i18n.t('import_view.errors.only_txt_inline')
    uiStore.showError(i18n.t('import_view.errors.only_txt_message'))
    return
  }

  try {
    logger.debug('Subiendo archivo', { fileName: file.name, size: file.size })
    parsed.value = await highlightService.uploadFile(file)
    step.value = 'preview'
    uiStore.showSuccess(i18n.t('import_view.messages.file_analyzed'))
  } catch (err) {
    logger.error('Error al subir archivo', err)
    error.value = err.message
    uiStore.showError(err.message || i18n.t('import_view.errors.process_error'))
  }
}

const importHighlights = async () => {
  importing.value = true
  error.value = null

  try {
    logger.debug('Importando highlights', { count: parsed.value.highlights.length })
    // Solo enviar los nuevos, siempre privados
    const newHighlights = parsed.value.highlights.filter(h => h.is_new)
    result.value = await highlightService.importHighlights(newHighlights)
    step.value = 'result'
    uiStore.showSuccess(i18n.t('import_view.messages.imported_success', { count: result.value.imported }))
    logger.info('Importación exitosa', result.value)
  } catch (err) {
    logger.error('Error al importar highlights', err)
    error.value = err.message
    uiStore.showError(err.message || i18n.t('import_view.errors.import_error'))
  } finally {
    importing.value = false
  }
}

const resetImport = () => {
  step.value = 'upload'
  parsed.value = null
  result.value = null
  error.value = null
  logger.debug('Importación reiniciada')
}
</script>

<style scoped>
/* Shared shell */
.panel-shell {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
  border: 1px solid var(--border-subtle);
  border-radius: var(--border-radius);
  background: var(--bg-secondary, transparent);
  padding: var(--space-lg);
}

/* Common */
.link-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: 1px solid var(--border-subtle);
  border-radius: 0;
  padding: 4px var(--space-sm);
  font-family: var(--font-ui);
  font-size: var(--font-size-xs);
  line-height: 1;
  text-align: center;
  white-space: nowrap;
  font-weight: 300;
  color: var(--text-tertiary);
  cursor: pointer;
  transition: all var(--transition-fast);
  text-decoration: none;
  letter-spacing: 0.04em;
  text-transform: lowercase;
}

.link-action:hover {
  border-color: var(--text-primary);
  background: rgba(10, 10, 10, 0.04);
  color: var(--text-primary);
}

.link-action:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.select-file-link {
  border: none;
  border-bottom: 1px solid var(--border-medium);
  border-radius: 0;
  padding: 0;
  text-transform: lowercase;
}

.select-file-link:hover {
  border-bottom-color: var(--text-primary);
  background: transparent;
}

.action-primary {
  background: var(--text-primary);
  border-color: var(--text-primary);
  color: var(--bg-primary);
  font-weight: 400;
}

.action-primary:hover {
  opacity: 0.9;
  color: var(--bg-primary);
}

.feedback {
  font-size: var(--font-size-xs);
  margin-top: var(--space-lg);
  text-align: center;
}

.feedback.error {
  color: #991B1B;
}

/* Step 1: Upload */
.step-upload {
  text-align: center;
}

.step-hint {
  font-family: var(--font-display);
  font-size: var(--font-size-lg);
  font-style: italic;
  color: var(--text-tertiary);
  margin-bottom: var(--space-2xl);
}

.drop-area {
  border: 1px solid var(--text-primary);
  border-radius: 0;
  padding: var(--space-2xl) var(--space-xl);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-md);
  transition: border-color var(--transition-fast), background-color var(--transition-fast);
}

.drop-area.dragging {
  border-color: var(--text-primary);
  background-color: rgba(10, 10, 10, 0.04);
}

.drop-label {
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
}

.drop-or {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}

/* Step 2: Preview */
.step-preview {
  padding-bottom: var(--space-lg);
}

.preview-summary {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-xs);
  margin-bottom: var(--space-lg);
  text-align: center;
}

.summary-number {
  font-family: var(--font-display);
  font-size: var(--font-size-2xl);
  font-weight: 400;
  color: var(--text-primary);
}

.summary-label {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

.summary-detail {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}

.import-note {
  text-align: center;
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  font-style: italic;
  margin-bottom: var(--space-2xl);
  line-height: 1.6;
}

.preview-books {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.preview-book {
  border: 1px solid var(--border-subtle);
  border-radius: var(--border-radius);
  padding: var(--space-lg);
  background: var(--bg-secondary, transparent);
}

.preview-book-head {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-bottom: var(--space-lg);
}

.pb-title {
  font-family: var(--font-display);
  font-size: var(--font-size-base);
  font-weight: 500;
  color: var(--text-primary);
}

.pb-meta {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}

.preview-quote {
  padding-left: var(--space-lg);
  border-left: 1px solid var(--border-subtle);
  margin: 0 0 var(--space-md) 0;
}

.preview-quote p {
  font-family: var(--font-display);
  font-size: var(--font-size-sm);
  font-style: italic;
  line-height: 1.7;
  color: var(--text-secondary);
  margin: 0;
}

.preview-more {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  padding-left: var(--space-lg);
}

/* Sticky footer for actions */
.sticky-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: var(--space-xl);
  padding-top: var(--space-md);
  border-top: 1px solid var(--border-subtle);
}

.no-new {
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
  font-style: italic;
}

/* Step 3: Result */
.step-result {
  padding-top: var(--space-lg);
}

.result-stats {
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: var(--space-lg);
  margin-bottom: var(--space-3xl);
}

.result-stat {
  display: flex;
  align-items: baseline;
  gap: var(--space-xs);
}

.rs-number {
  font-family: var(--font-display);
  font-size: var(--font-size-xl);
  font-weight: 400;
  color: var(--text-primary);
}

.rs-label {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.rs-sep {
  color: var(--text-tertiary);
}

.step-actions {
  display: flex;
  justify-content: center;
  gap: var(--space-2xl);
}

@media (max-width: 640px) {
  .result-stats {
    flex-direction: column;
    align-items: center;
    gap: var(--space-md);
  }

  .rs-sep {
    display: none;
  }

  .sticky-actions {
    flex-wrap: wrap;
    gap: var(--space-sm);
  }
}
</style>
