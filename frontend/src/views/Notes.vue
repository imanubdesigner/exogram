<template>
  <div class="notes container">
    <Navbar />

    <section class="notes-header">
      <h1 class="notes-title">{{ i18n.t('notes.title') }}</h1>
      <button class="btn-new-note" @click="openNewNoteModal">{{ i18n.t('notes.new_note') }}</button>
    </section>

    <!-- Modal para crear/editar nota -->
    <div v-if="showNoteModal" class="modal-backdrop" @click.self="closeNoteModal">
      <div class="modal" role="dialog" aria-modal="true">
        <header class="modal-header login-modal-header">
          <span class="brand">{{ editingNote ? i18n.t('notes.modal_edit') : i18n.t('notes.modal_new') }} {{ i18n.t('notes.modal_note') }}</span>
          <button class="modal-close" :aria-label="i18n.t('notes.close_modal_aria')" @click="closeNoteModal">✕</button>
        </header>
        <div class="modal-body">
          <form class="note-form" @submit.prevent="saveNote">
            <textarea
              v-model="noteContent"
              :placeholder="i18n.t('notes.placeholder')"
              class="note-textarea"
              maxlength="5000"
            ></textarea>
            <div class="note-form-footer">
              <span class="char-count">{{ noteContent.length }}/5000</span>
              <div class="modal-footer">
                <button type="button" class="btn-enter" @click="closeNoteModal">{{ i18n.t('notes.cancel') }}</button>
                <button type="submit" class="btn-enter" :disabled="savingNote || !noteContent.trim()">
                  {{ savingNote ? i18n.t('notes.saving') : i18n.t('notes.save') }}
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- Lista de notas -->
    <section class="notes-container">
      <div v-if="notes.length === 0" class="empty-state">
        <p class="empty-text">{{ i18n.t('notes.empty') }}</p>
      </div>

      <div v-else class="notes-list">
        <div v-for="note in paginatedNotes" :key="note.id" class="note-card">
          <div class="note-header">
            <div class="note-date">{{ formatDate(note.created_at) }}</div>
            <div class="note-header-right">
              <button
                class="note-visibility-btn"
                :class="note.visibility"
                @click="toggleVisibility(note)"
                :title="note.visibility === 'public' ? i18n.t('notes.visibility_to_private') : i18n.t('notes.visibility_to_public')"
              >
                {{ visibilityLabel(note.visibility) }}
              </button>
              <div class="note-actions">
                <button
                  class="btn-note-action btn-favorite"
                  :class="{ 'is-favorite': note.is_favorite }"
                  @click="toggleFavorite(note.id)"
                  :title="note.is_favorite ? i18n.t('notes.favorite_remove') : i18n.t('notes.favorite_add')"
                  :aria-label="note.is_favorite ? i18n.t('notes.favorite_remove') : i18n.t('notes.favorite_add')"
                >
                  <svg class="note-icon" viewBox="0 0 24 24" aria-hidden="true">
                    <path
                      d="M11.48 3.5a.562.562 0 0 1 1.04 0l2.125 5.111a.563.563 0 0 0 .475.345l5.518.442c.499.04.701.663.321 1l-4.204 3.602a.563.563 0 0 0-.182.557l1.285 5.385a.562.562 0 0 1-.84.61l-4.725-2.885a.563.563 0 0 0-.586 0l-4.725 2.885a.562.562 0 0 1-.84-.61l1.285-5.385a.563.563 0 0 0-.182-.557l-4.204-3.602a.563.563 0 0 1 .321-1l5.518-.442a.563.563 0 0 0 .475-.345L11.48 3.5z"
                      :fill="note.is_favorite ? 'currentColor' : 'none'"
                      stroke="currentColor"
                      stroke-width="1.6"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    />
                  </svg>
                </button>
                <button
                  class="btn-note-action"
                  @click="startEditNote(note)"
                  :title="i18n.t('notes.edit_note')"
                  :aria-label="i18n.t('notes.edit_note')"
                >
                  <svg class="note-icon" viewBox="0 0 24 24" aria-hidden="true">
                    <path
                      d="M12 20h9"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="1.8"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    />
                    <path
                      d="M16.5 3.5a2.121 2.121 0 0 1 3 3L8 18l-4 1 1-4 11.5-11.5z"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="1.8"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    />
                  </svg>
                </button>
                <button
                  class="btn-note-action btn-danger"
                  @click="deleteNote(note.id)"
                  :title="i18n.t('notes.delete_note')"
                  :aria-label="i18n.t('notes.delete_note')"
                >
                  <svg class="note-icon" viewBox="0 0 24 24" aria-hidden="true">
                    <path
                      d="M3 6h18M8 6V4h8v2m-7 0v13m6-13v13m4-13-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="1.8"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    />
                  </svg>
                </button>
              </div>
            </div>
          </div>

          <div class="note-content">
            {{ note.content }}
          </div>
        </div>
        
        <PaginationControl 
          v-model="currentPage" 
          :total-items="sortedNotes.length" 
          :page-size="5" 
        />
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useI18nStore } from '../stores/i18n'
import { apiRequest } from '../services/api'
import Navbar from '../components/Navbar.vue'
import PaginationControl from '../components/PaginationControl.vue'
import { logger } from '../utils/logger'

const i18n = useI18nStore()
const notes = ref([])
const showNoteModal = ref(false)
const noteContent = ref('')
const editingNote = ref(null)
const savingNote = ref(false)
const loading = ref(true)
const currentPage = ref(1)

const normalizeNotesPayload = (payload) => {
  if (Array.isArray(payload)) return payload
  if (Array.isArray(payload?.results)) return payload.results
  return []
}

const sortedNotes = computed(() => {
  return [...notes.value].sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
})

const paginatedNotes = computed(() => {
  const start = (currentPage.value - 1) * 5
  return sortedNotes.value.slice(start, start + 5)
})

const handleNoteEscape = (event) => {
  if (event.key === 'Escape' && showNoteModal.value) {
    closeNoteModal()
  }
}

watch(showNoteModal, (isOpen) => {
  document.body.style.overflow = isOpen ? 'hidden' : ''
})

onMounted(async () => {
  window.addEventListener('keydown', handleNoteEscape)
  await loadNotes()
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleNoteEscape)
  document.body.style.overflow = ''
})

const loadNotes = async () => {
  try {
    loading.value = true
    const payload = await apiRequest('/notes/')
    notes.value = normalizeNotesPayload(payload)
  } catch (err) {
    logger.error('Error loading notes:', err)
  } finally {
    loading.value = false
  }
}

const openNewNoteModal = () => {
  editingNote.value = null
  noteContent.value = ''
  showNoteModal.value = true
}

const startEditNote = (note) => {
  editingNote.value = note
  noteContent.value = note.content
  showNoteModal.value = true
}

const closeNoteModal = () => {
  showNoteModal.value = false
  editingNote.value = null
  noteContent.value = ''
}

const saveNote = async () => {
  savingNote.value = true
  try {
    const method = editingNote.value ? 'PATCH' : 'POST'
    const path = editingNote.value ? `/notes/${editingNote.value.id}/` : '/notes/'
    
    const payload = {
      content: noteContent.value
    }
    if (!editingNote.value) {
      payload.visibility = 'private'
    }

    const savedNote = await apiRequest(path, {
      method,
      body: JSON.stringify(payload)
    })
    
    if (editingNote.value) {
      const idx = notes.value.findIndex(n => n.id === editingNote.value.id)
      if (idx !== -1) notes.value[idx] = savedNote
    } else {
      notes.value.unshift(savedNote)
    }
    closeNoteModal()
  } catch (err) {
    logger.error('Error saving note:', err)
    alert(i18n.t('notes.save_error'))
  } finally {
    savingNote.value = false
  }
}

const toggleFavorite = async (noteId) => {
  try {
    const updatedNote = await apiRequest(`/notes/${noteId}/toggle_favorite/`, {
      method: 'POST',
    })
    const idx = notes.value.findIndex(n => n.id === noteId)
    if (idx !== -1) notes.value[idx] = updatedNote
  } catch (err) {
    logger.error('Error toggling favorite:', err)
  }
}

const toggleVisibility = async (note) => {
  const nextVisibility = note.visibility === 'public' ? 'private' : 'public'
  try {
    const updatedNote = await apiRequest(`/notes/${note.id}/`, {
      method: 'PATCH',
      body: JSON.stringify({ visibility: nextVisibility })
    })
    const idx = notes.value.findIndex(n => n.id === note.id)
    if (idx !== -1) notes.value[idx] = updatedNote
  } catch (err) {
    logger.error('Error toggling visibility:', err)
  }
}

const deleteNote = async (noteId) => {
  if (!confirm(i18n.t('notes.confirm_delete'))) return
  
  try {
    await apiRequest(`/notes/${noteId}/`, {
      method: 'DELETE',
    })
    notes.value = notes.value.filter(n => n.id !== noteId)
  } catch (err) {
    logger.error('Error deleting note:', err)
  }
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

const visibilityLabel = (visibility) => {
  const labels = {
    'private': i18n.t('notes.visibility_private'),
    'unlisted': i18n.t('notes.visibility_unlisted'),
    'public': i18n.t('notes.visibility_public')
  }
  return labels[visibility] || visibility
}
</script>

<style scoped>
.notes {
  padding-bottom: var(--space-3xl);
}

.notes-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-lg);
  padding-bottom: var(--space-md);
}

.notes-title {
  font-family: var(--font-display);
  font-size: var(--font-size-xl);
  font-weight: 400;
  margin: 0;
  margin-bottom: 0;
}

.btn-new-note {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: 1px solid var(--text-primary);
  border-radius: var(--border-radius);
  min-width: 7.5rem;
  height: 32px;
  padding: 0 var(--space-md);
  font-family: var(--font-ui);
  font-size: var(--font-size-xs);
  line-height: 1;
  text-align: center;
  white-space: nowrap;
  color: var(--text-primary);
  cursor: pointer;
  transition: all var(--transition-fast);
  text-transform: lowercase;
  letter-spacing: 0.04em;
}

.btn-new-note:hover {
  background: var(--text-primary);
  color: var(--bg-primary);
}

/* Modal */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(10, 10, 10, 0.45);
  backdrop-filter: blur(1px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 60;
}

.modal {
  background: var(--bg-primary);
  padding: var(--space-lg);
  width: 100%;
  max-width: 600px;
  border: 1px solid var(--text-primary);
  border-radius: var(--border-radius);
  box-shadow: 0 8px 24px rgba(10, 10, 10, 0.2);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-md);
}

.modal-close {
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
  color: var(--text-tertiary);
}

.modal-close:hover {
  color: var(--text-primary);
}

.modal-body {
  padding-top: var(--space-sm);
}

.note-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.note-textarea {
  width: 100%;
  min-height: 200px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--border-radius);
  padding: var(--space-md);
  font-family: var(--font-display);
  font-size: var(--font-size-base);
  font-weight: 400;
  line-height: 1.6;
  color: var(--text-primary);
  background: transparent;
  resize: vertical;
  transition: border-color var(--transition-fast);
}

.note-textarea:focus {
  outline: none;
  border-color: var(--text-primary);
}

.note-textarea::placeholder {
  color: var(--text-tertiary);
}

.note-form-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.char-count {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}

.modal-footer {
  display: flex;
  gap: var(--space-sm);
}

.btn-enter {
  background: none;
  border: none;
  padding: var(--space-xs) 0;
  font-family: var(--font-ui);
  font-size: var(--font-size-sm);
  font-weight: 300;
  color: var(--text-tertiary);
  cursor: pointer;
  transition: color var(--transition-fast);
  letter-spacing: 0.05em;
}

.btn-enter:hover {
  color: var(--text-primary);
}

.btn-enter:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* Empty state */
.empty-state {
  text-align: center;
  padding: var(--space-2xl) 0 var(--space-3xl);
}

.empty-text {
  font-family: var(--font-display);
  font-size: var(--font-size-lg);
  font-style: italic;
  color: var(--text-tertiary);
  margin: 0;
  line-height: 1.6;
}

/* Notes list */
.notes-container {
  display: flex;
  flex-direction: column;
}

.notes-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
  margin-top: var(--space-lg);
}

.note-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
  padding: var(--space-lg);
  border: 1px solid var(--border-subtle);
  border-radius: var(--border-radius);
  background: var(--bg-secondary, transparent);
}

.note-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-sm);
}

.note-date {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.note-header-right {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.note-visibility-btn {
  border: 1px solid var(--border-subtle);
  background: transparent;
  color: var(--text-secondary);
  font-size: var(--font-size-xs);
  font-family: var(--font-ui);
  letter-spacing: 0.04em;
  text-transform: lowercase;
  padding: 4px var(--space-sm);
  border-radius: 0;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.note-visibility-btn:hover {
  border-color: var(--text-primary);
  color: var(--text-primary);
}

.note-visibility-btn.private {
  background: rgba(10, 10, 10, 0.06);
}

.note-visibility-btn.unlisted {
  background: rgba(200, 180, 150, 0.18);
}

.note-visibility-btn.public {
  background: rgba(100, 150, 100, 0.18);
}

.note-actions {
  display: flex;
  gap: var(--space-xs);
}

.btn-note-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 50%;
  color: var(--text-tertiary);
  cursor: pointer;
  transition: all var(--transition-fast);
  padding: 0;
}

.note-icon {
  width: 14px;
  height: 14px;
  overflow: visible;
}

.btn-note-action:hover {
  border-color: var(--border-subtle);
  background: rgba(10, 10, 10, 0.04);
  color: var(--text-primary);
}

.btn-note-action.is-favorite {
  color: #b88a32;
}

.btn-note-action.btn-favorite:hover {
  color: #b88a32;
  border-color: rgba(184, 138, 50, 0.35);
  background: rgba(184, 138, 50, 0.08);
}

.btn-note-action.btn-danger:hover {
  color: #c53030;
  border-color: rgba(197, 48, 48, 0.3);
  background: rgba(197, 48, 48, 0.05);
}

.note-content {
  font-size: var(--font-size-base);
  font-family: var(--font-display);
  line-height: 1.7;
  color: var(--text-primary);
  white-space: pre-wrap;
}

@media (max-width: 640px) {
  .notes-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-md);
  }

  .note-header {
    align-items: flex-start;
  }

  .note-header-right {
    flex-direction: column;
    align-items: flex-end;
    gap: 6px;
  }

  .note-textarea {
    min-height: 150px;
  }
}
</style>
