<template>
  <div class="profile container">
    <Navbar />

    <section class="profile-header">
      <div class="nickname-row">
        <div class="nickname-left">
          <h1 class="profile-nickname">@{{ nickname }}</h1>
        </div>
        <div class="nickname-right">
          <router-link
            :to="'/users/' + nickname"
            class="link-public-profile right-link"
            target="_blank"
            :title="i18n.t('profile.public_profile_title')"
          >
            {{ i18n.t('profile.public_profile_link') }}
          </router-link>
          <a href="#" class="link-public-profile right-link" @click.prevent="openCredentialsModal">
            {{ i18n.t('profile.manage_credentials') }}
          </a>
          <a href="#" class="link-public-profile right-link" @click.prevent="openIntegrationsModal">
            {{ i18n.t('profile.integrations_link') }}
          </a>
        </div>
      </div>
      
      <p v-if="hermitMode" class="visibility-warning">
        {{ i18n.t('profile.hermit_warning') }}
      </p>
    </section>

    <section class="profile-section">
      <p v-if="mustChangeCredentials" class="credentials-warning">
        {{ i18n.t('profile.must_change_warning') }}
      </p>

      <!-- Minimal modal for credentials -->
      <div v-if="showCredentialsModal" class="modal-backdrop" @click.self="closeCredentialsModal">
        <div class="modal" role="dialog" aria-modal="true">
          <header class="modal-header login-modal-header">
            <span class="brand">{{ i18n.t('profile.credentials.title') }}</span>
            <button class="modal-close" :aria-label="i18n.t('profile.close_modal_aria')" @click="closeCredentialsModal">✕</button>
          </header>
          <div class="modal-body">
            <p class="modal-hint">{{ i18n.t('profile.credentials.hint') }}</p>
            <form class="login-form compact" @submit.prevent="handleSaveAndClose">
              <input
                v-model="credentialsNickname"
                type="text"
                :placeholder="i18n.t('profile.credentials.nickname_placeholder')"
                maxlength="50"
                required
                autocomplete="username"
              />

              <input
                v-model="newPassword"
                type="password"
                :placeholder="i18n.t('profile.credentials.password_placeholder')"
                minlength="8"
                autocomplete="new-password"
              />

              <input
                v-model="newPasswordConfirm"
                type="password"
                :placeholder="i18n.t('profile.credentials.password_confirm_placeholder')"
                autocomplete="new-password"
              />

              <div class="modal-footer">
                <button type="button" class="btn-enter" @click="closeCredentialsModal">{{ i18n.t('profile.credentials.cancel') }}</button>
                <button type="submit" class="btn-enter" :disabled="updatingCredentials">
                  {{ updatingCredentials ? i18n.t('profile.credentials.saving') : i18n.t('profile.credentials.save') }}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>

      <!-- Minimal modal for integrations (Goodreads) -->
      <div v-if="showIntegrationsModal" class="modal-backdrop" @click.self="closeIntegrationsModal">
        <div class="modal" role="dialog" aria-modal="true">
          <header class="modal-header login-modal-header">
            <span class="brand">{{ i18n.t('profile.integrations.title') }}</span>
            <button class="modal-close" :aria-label="i18n.t('profile.close_modal_aria')" @click="closeIntegrationsModal">✕</button>
          </header>
          <div class="modal-body">
            <p class="modal-hint">{{ i18n.t('profile.integrations.hint') }}</p>

            <div class="goodreads-panel">
              <span class="integration-label">{{ i18n.t('profile.integrations.goodreads_label') }}</span>

              <div v-if="editingGoodreads" class="goodreads-input-row">
                <input
                  v-model="goodreadsDraft"
                  type="text"
                  :placeholder="i18n.t('profile.integrations.goodreads_placeholder')"
                  class="text-input"
                  @keyup.enter="saveGoodreadsUsername"
                />
              </div>
              <div v-else class="goodreads-fixed-row">
                <span class="goodreads-fixed-value" :class="{ empty: !goodreadsUsername }">
                  {{ goodreadsUsername || i18n.t('profile.integrations.goodreads_empty') }}
                </span>
              </div>

              <div class="goodreads-actions">
                <template v-if="editingGoodreads">
                  <button
                    class="btn-inline-activate"
                    :disabled="savingGoodreads"
                    @click="saveGoodreadsUsername"
                  >
                    {{ savingGoodreads ? i18n.t('profile.credentials.saving') : i18n.t('profile.integrations.save') }}
                  </button>
                  <button
                    class="btn-inline-activate"
                    :disabled="savingGoodreads"
                    @click="cancelEditingGoodreads"
                  >
                    {{ i18n.t('profile.integrations.cancel') }}
                  </button>
                </template>
                <template v-else-if="!goodreadsUsername">
                  <button
                    class="btn-inline-activate"
                    @click="startEditingGoodreads"
                  >
                    {{ i18n.t('profile.integrations.add') }}
                  </button>
                </template>
                <template v-else>
                  <button
                    class="btn-inline-activate"
                    :disabled="activatingGoodreads"
                    @click="activateGoodreadsSync"
                    :title="i18n.t('profile.integrations.activate_title')"
                  >
                    {{ activatingGoodreads ? i18n.t('profile.integrations.activating') : i18n.t('profile.integrations.activate') }}
                  </button>
                  <button class="btn-inline-activate" @click="startEditingGoodreads">
                    {{ i18n.t('profile.integrations.edit') }}
                  </button>
                  <button class="btn-inline-activate btn-inline-danger" @click="clearGoodreadsUsername">
                    {{ i18n.t('profile.integrations.delete') }}
                  </button>
                </template>
              </div>
            </div>
            <p class="input-help">{{ i18n.t('profile.integrations.input_help') }}</p>
          </div>
        </div>
      </div>
      <!-- Modal eliminar cuenta -->
      <div v-if="showDeleteModal" class="modal-backdrop" @click.self="closeDeleteModal">
        <div class="modal" role="dialog" aria-modal="true">
          <header class="modal-header login-modal-header">
            <span class="brand">{{ i18n.t('profile.delete_account_modal.title') }}</span>
            <button class="modal-close" :aria-label="i18n.t('profile.close_modal_aria')" @click="closeDeleteModal">✕</button>
          </header>
          <div class="modal-body">
            <p class="modal-hint delete-warning">{{ i18n.t('profile.delete_account_modal.warning') }}</p>
            <form class="login-form compact" @submit.prevent="handleDeleteAccount">
              <label class="delete-confirm-label">{{ i18n.t('profile.delete_account_modal.confirm_label') }}</label>
              <input
                v-model="deleteConfirmText"
                type="text"
                :placeholder="i18n.t('profile.delete_account_modal.confirm_placeholder')"
                autocomplete="off"
                spellcheck="false"
              />
              <div class="modal-footer">
                <button type="button" class="btn-enter" @click="closeDeleteModal">
                  {{ i18n.t('profile.delete_account_modal.cancel') }}
                </button>
                <button
                  type="submit"
                  class="btn-enter btn-enter-danger"
                  :disabled="deletingAccount || deleteConfirmText !== 'DELETE_MY_ACCOUNT'"
                >
                  {{ deletingAccount ? i18n.t('profile.delete_account_modal.deleting') : i18n.t('profile.delete_account_modal.btn') }}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </section>

    <!-- Bio -->
    <section class="profile-section">
      <div class="bio-container">
        <textarea
          v-model="bio"
          :placeholder="i18n.t('profile.bio_placeholder')"
          maxlength="500"
          rows="3"
        ></textarea>
        <div class="bio-actions">
          <span class="char-count">{{ bio.length }}/500</span>
          <button
            class="btn-option"
            :disabled="savingProfile || !isBioDirty"
            @click="saveProfile"
          >
            {{ savingProfile ? i18n.t('profile.credentials.saving') : i18n.t('profile.save_bio') }}
          </button>
        </div>
      </div>
    </section>

    <!-- Privacidad -->
    <section class="profile-section">
      <h3 class="section-label">{{ i18n.t('profile.privacy_title') }}</h3>

      <div class="privacy-row">
        <div class="privacy-label">
          <div class="toggle-text">
            <span class="toggle-title">{{ i18n.t('profile.hermit_title') }}</span>
            <span class="toggle-desc">{{ i18n.t('profile.hermit_desc') }}</span>
          </div>
        </div>
        <div class="privacy-control">
          <div class="switch">
            <input type="checkbox" v-model="hermitMode" @change="handleHermitToggle" />
            <span class="slider"></span>
          </div>
        </div>
      </div>

      <div class="privacy-row">
        <div class="privacy-label">
          <div class="toggle-text">
            <span class="toggle-title">{{ i18n.t('profile.discover_title') }}</span>
            <span class="toggle-desc">{{ i18n.t('profile.discover_desc') }}</span>
          </div>
        </div>
        <div class="privacy-control">
          <div class="switch">
            <input type="checkbox" v-model="discoverable" @change="handleDiscoverableToggle" />
            <span class="slider"></span>
          </div>
        </div>
      </div>

      <div class="privacy-row" :class="{ 'disabled-text': hermitMode }">
        <div class="privacy-label">
          <div class="setting-text">
            <span class="setting-title">{{ i18n.t('profile.comments_title') }}</span>
            <span class="setting-desc">{{ i18n.t('profile.comments_desc') }}</span>
          </div>
        </div>
        <div class="privacy-control">
          <div class="setting-input-wrap stepper-wrap" :class="{ 'disabled-text': hermitMode }">
            <button 
              class="stepper-btn" 
              :disabled="hermitMode || commentAllowanceDepth <= 0"
              :aria-label="i18n.t('profile.decrease_comments_aria')"
              @click="updateDepth(-1)"
            >–</button>
            <span class="stepper-value">{{ commentAllowanceDepth }}</span>
            <button 
              class="stepper-btn" 
              :disabled="hermitMode || commentAllowanceDepth >= 10"
              :aria-label="i18n.t('profile.increase_comments_aria')"
              @click="updateDepth(1)"
            >+</button>
          </div>
        </div>
      </div>
    </section>


    <!-- Donaciones -->
    <section v-if="donationAlias" class="profile-section">
      <h3 class="section-label">{{ i18n.t('profile.donate_title') }}</h3>
      <div class="bio-container">
        <p class="visibility-warning" style="margin-top: 0; font-style: normal; line-height: 1.6;">
          {{ i18n.t('profile.donate_desc', { alias: donationAlias }) }}
        </p>
      </div>
    </section>

    <!-- Exportar -->
    <section class="profile-section">
      <h3 class="section-label">{{ i18n.t('profile.export_title') }}</h3>
      <div class="export-actions">
        <button class="btn-option" @click="exportObsidian" :disabled="exporting">
          {{ i18n.t('profile.export_obsidian') }}
        </button>
        <button class="btn-option" @click="exportJSON" :disabled="exporting">
          {{ i18n.t('profile.export_json') }}
        </button>
      </div>
    </section>

    <!-- Logout + Delete account -->
    <section class="profile-section profile-footer">
      <button class="btn-option btn-logout" @click="handleLogout">
        {{ i18n.t('profile.logout') }}
      </button>
      <button class="btn-option btn-delete-account" @click="openDeleteModal">
        {{ i18n.t('profile.delete_account') }}
      </button>
    </section>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useI18nStore } from '../stores/i18n'
import { authService } from '../services/auth'
import { useAuthStore } from '../stores/auth'
import { useUIStore } from '../stores/ui'
import Navbar from '../components/Navbar.vue'
import { logger } from '../utils/logger'

const authStore = useAuthStore()
const uiStore = useUIStore()
const i18n = useI18nStore()
const nickname = ref('')
const bio = ref('')
const goodreadsUsername = ref('')
const hermitMode = ref(false)
const discoverable = ref(true)
const commentAllowanceDepth = ref(2)
const exporting = ref(false)
const savingProfile = ref(false)
const activatingGoodreads = ref(false)
const editingGoodreads = ref(false)
const goodreadsDraft = ref('')
const savingGoodreads = ref(false)
const mustChangeCredentials = ref(false)
const credentialsNickname = ref('')
const newPassword = ref('')
const newPasswordConfirm = ref('')
const updatingCredentials = ref(false)
const initialBio = ref('')
const showDeleteModal = ref(false)
const deleteConfirmText = ref('')
const deletingAccount = ref(false)

const donationAlias = import.meta.env.VITE_DONATION_ALIAS || ''

const isBioDirty = computed(() => bio.value !== initialBio.value)


onMounted(async () => {
  window.addEventListener('keydown', handleProfileEscape)
  try {
    const user = await authService.getCurrentUser()
    if (user) {
      const resolvedDiscoverable =
        typeof user.is_discoverable === 'boolean'
          ? user.is_discoverable
          : (authStore.user?.is_discoverable !== false)
      authStore.user = {
        ...(authStore.user || {}),
        ...user,
        is_discoverable: resolvedDiscoverable
      }
      nickname.value = user.nickname || ''
      credentialsNickname.value = user.nickname || ''
      bio.value = user.bio || ''
      goodreadsUsername.value = user.goodreads_username || ''
      goodreadsDraft.value = goodreadsUsername.value
      hermitMode.value = user.is_hermit_mode || false
      discoverable.value = resolvedDiscoverable
      commentAllowanceDepth.value = user.comment_allowance_depth !== undefined ? user.comment_allowance_depth : 2
      mustChangeCredentials.value = !!user.must_change_credentials
      initialBio.value = bio.value
      if (mustChangeCredentials.value) {
        uiStore.showWarning(i18n.t('profile.feedback.must_change_prompt'))
      }
    }
  } catch (err) {
    logger.error('Error loading profile:', err)
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleProfileEscape)
  document.body.style.overflow = ''
})

const saveProfile = async () => {
  if (!isBioDirty.value) return
  savingProfile.value = true
  try {
    await authService.updateProfile({ 
      bio: bio.value
    })
    initialBio.value = bio.value
    uiStore.showSuccess(i18n.t('profile.feedback.saved'))
  } catch (err) {
    logger.error('Error saving profile:', err)
    uiStore.showError(i18n.t('profile.feedback.save_bio_error'))
  } finally {
    savingProfile.value = false
  }
}

const saveCredentials = async () => {
  const nextNickname = credentialsNickname.value.trim()
  if (!nextNickname || !newPassword.value || !newPasswordConfirm.value) {
    uiStore.showError(i18n.t('profile.feedback.credentials_required'))
    return
  }

  updatingCredentials.value = true
  try {
    const payload = {
      nickname: nextNickname,
      password: newPassword.value,
      password_confirm: newPasswordConfirm.value
    }
    const response = await authService.updateCredentials(payload)
    const user = response?.user || null
    if (user) {
      nickname.value = user.nickname || nextNickname
      credentialsNickname.value = user.nickname || nextNickname
      mustChangeCredentials.value = !!user.must_change_credentials
    } else {
      nickname.value = nextNickname
      credentialsNickname.value = nextNickname
      mustChangeCredentials.value = false
    }
    newPassword.value = ''
    newPasswordConfirm.value = ''
    sessionStorage.removeItem('must_change_credentials')
    uiStore.showSuccess(i18n.t('profile.feedback.credentials_updated'))
  } catch (err) {
    logger.error('Error saving credentials:', err)
    uiStore.showError(err.message || i18n.t('profile.feedback.credentials_update_error'))
  } finally {
    updatingCredentials.value = false
  }
}

// Modal control for credentials management
const showCredentialsModal = ref(false)
const openCredentialsModal = () => {
  // preload current values
  showCredentialsModal.value = true
}
const closeCredentialsModal = () => {
  showCredentialsModal.value = false
  // clear sensitive fields when closing (but keep nickname)
  newPassword.value = ''
  newPasswordConfirm.value = ''
}

const handleSaveAndClose = async () => {
  await saveCredentials()
  if (!mustChangeCredentials.value) {
    closeCredentialsModal()
  }
}

// Integrations modal (Goodreads)
const showIntegrationsModal = ref(false)
const openIntegrationsModal = () => {
  goodreadsDraft.value = goodreadsUsername.value || ''
  showIntegrationsModal.value = true
}
const closeIntegrationsModal = () => {
  showIntegrationsModal.value = false
}

const isAnyModalOpen = computed(
  () => showCredentialsModal.value || showIntegrationsModal.value || showDeleteModal.value
)

const handleProfileEscape = (event) => {
  if (event.key !== 'Escape') return
  if (showDeleteModal.value) {
    closeDeleteModal()
    return
  }
  if (showIntegrationsModal.value) {
    closeIntegrationsModal()
    return
  }
  if (showCredentialsModal.value) {
    closeCredentialsModal()
  }
}

watch(isAnyModalOpen, (isOpen) => {
  document.body.style.overflow = isOpen ? 'hidden' : ''
})


const activateGoodreadsSync = async () => {
  const username = goodreadsUsername.value.trim()
  if (!username) {
    uiStore.showError(i18n.t('profile.feedback.goodreads_required'))
    return
  }

  activatingGoodreads.value = true
  try {
    const activation = await authService.activateGoodreads(username)
    goodreadsUsername.value = (activation.goodreads_username || username).trim()
    goodreadsDraft.value = goodreadsUsername.value
    uiStore.showSuccess(i18n.t('profile.feedback.goodreads_sync_activated'))
  } catch (err) {
    logger.error('Error activating goodreads sync:', err)
    uiStore.showError(i18n.t('profile.feedback.goodreads_sync_error'))
  } finally {
    activatingGoodreads.value = false
  }
}

const startEditingGoodreads = () => {
  goodreadsDraft.value = goodreadsUsername.value
  editingGoodreads.value = true
}

const cancelEditingGoodreads = () => {
  goodreadsDraft.value = goodreadsUsername.value
  editingGoodreads.value = false
}

const saveGoodreadsUsername = async () => {
  const nextUsername = goodreadsDraft.value.trim()
  savingGoodreads.value = true
  try {
    await authService.updateProfile({
      goodreads_username: nextUsername
    })
    goodreadsUsername.value = nextUsername
    goodreadsDraft.value = nextUsername
    editingGoodreads.value = false
    uiStore.showSuccess(
      nextUsername
        ? i18n.t('profile.feedback.goodreads_saved')
        : i18n.t('profile.feedback.goodreads_removed')
    )
  } catch (err) {
    logger.error('Error saving Goodreads username:', err)
    uiStore.showError(i18n.t('profile.feedback.goodreads_save_error'))
  } finally {
    savingGoodreads.value = false
  }
}

const clearGoodreadsUsername = async () => {
  savingGoodreads.value = true
  try {
    await authService.updateProfile({
      goodreads_username: ''
    })
    goodreadsUsername.value = ''
    goodreadsDraft.value = ''
    editingGoodreads.value = false
    uiStore.showSuccess(i18n.t('profile.feedback.goodreads_removed'))
  } catch (err) {
    logger.error('Error clearing Goodreads username:', err)
    uiStore.showError(i18n.t('profile.feedback.goodreads_remove_error'))
  } finally {
    savingGoodreads.value = false
  }
}

const handleHermitToggle = async () => {
  const previousHermitMode = !hermitMode.value
  await savePrivacy({
    previousHermitMode
  })
}

const handleDiscoverableToggle = async () => {
  const previousDiscoverable = !discoverable.value
  await savePrivacy({
    previousDiscoverable
  })
}

const updateDepth = async (change) => {
  const previousDepth = commentAllowanceDepth.value
  const newVal = commentAllowanceDepth.value + change
  if (newVal >= 0 && newVal <= 10) {
    commentAllowanceDepth.value = newVal
    await savePrivacy({
      previousDepth
    })
  }
}

const savePrivacy = async ({
  previousHermitMode = null,
  previousDiscoverable = null,
  previousDepth = null
} = {}) => {
  try {
    const updated = await authService.updatePrivacy({
      is_hermit_mode: hermitMode.value,
      is_discoverable: discoverable.value,
      comment_allowance_depth: commentAllowanceDepth.value
    })
    const normalizedPrivacy = {
      is_hermit_mode:
        typeof updated?.is_hermit_mode === 'boolean' ? updated.is_hermit_mode : hermitMode.value,
      is_discoverable:
        typeof updated?.is_discoverable === 'boolean' ? updated.is_discoverable : discoverable.value,
      comment_allowance_depth:
        typeof updated?.comment_allowance_depth === 'number'
          ? updated.comment_allowance_depth
          : commentAllowanceDepth.value,
    }
    hermitMode.value = normalizedPrivacy.is_hermit_mode
    discoverable.value = normalizedPrivacy.is_discoverable
    commentAllowanceDepth.value = normalizedPrivacy.comment_allowance_depth
    authStore.user = { ...(authStore.user || {}), ...updated, ...normalizedPrivacy }
    uiStore.showSuccess(i18n.t('profile.feedback.saved'))
  } catch (err) {
    logger.error('Error saving privacy:', err)
    if (typeof previousHermitMode === 'boolean') {
      hermitMode.value = previousHermitMode
    }
    if (typeof previousDiscoverable === 'boolean') {
      discoverable.value = previousDiscoverable
    }
    if (typeof previousDepth === 'number') {
      commentAllowanceDepth.value = previousDepth
    }
    uiStore.showError(err.message || i18n.t('profile.feedback.privacy_save_error'))
  }
}

const exportObsidian = async () => {
  exporting.value = true
  try {
    const blob = await authService.exportObsidian()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'exogram-obsidian.zip'
    a.click()
    URL.revokeObjectURL(url)
    uiStore.showSuccess(i18n.t('profile.feedback.export_zip_success'))
  } catch (err) {
    logger.error('Error exporting:', err)
    uiStore.showError(i18n.t('profile.feedback.export_zip_error'))
  } finally {
    exporting.value = false
  }
}

const exportJSON = async () => {
  exporting.value = true
  try {
    const data = await authService.exportData()
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'exogram-datos.json'
    a.click()
    URL.revokeObjectURL(url)
    uiStore.showSuccess(i18n.t('profile.feedback.export_json_success'))
  } catch (err) {
    logger.error('Error exporting:', err)
    uiStore.showError(i18n.t('profile.feedback.export_json_error'))
  } finally {
    exporting.value = false
  }
}

const openDeleteModal = () => {
  deleteConfirmText.value = ''
  showDeleteModal.value = true
}

const closeDeleteModal = () => {
  showDeleteModal.value = false
  deleteConfirmText.value = ''
}

const handleDeleteAccount = async () => {
  if (deleteConfirmText.value !== 'DELETE_MY_ACCOUNT') return
  deletingAccount.value = true
  try {
    await authService.deleteAccount()
    sessionStorage.removeItem('auth_hint')
    sessionStorage.removeItem('must_change_credentials')
    window.location.href = '/'
  } catch (err) {
    logger.error('Error deleting account:', err)
    uiStore.showError(i18n.t('profile.feedback.delete_account_error'))
    deletingAccount.value = false
  }
}

const handleLogout = async () => {
  await authStore.logout()
}
</script>

<style scoped>
.profile {
  padding-bottom: var(--space-3xl);
}

.profile-header {
  margin-bottom: var(--space-md);
}

.nickname-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-md);
  margin-bottom: var(--space-xs);
}

.nickname-left {
  flex: 1 1 auto;
}
.nickname-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
}

.profile-nickname {
  font-family: var(--font-display);
  font-size: var(--font-size-xl);
  font-weight: 400;
  letter-spacing: -0.02em;
  margin-bottom: 0;
}

.link-public-profile {
  font-family: var(--font-display);
  font-size: var(--font-size-sm);
  color: var(--accent-primary, var(--text-primary));
  text-decoration: none;
  border-bottom: 1px solid var(--text-primary);
  opacity: 0.6;
  text-underline-offset: 4px;
  transition: all var(--transition-fast);
}

.link-public-profile:hover {
  opacity: 1;
}

.visibility-warning {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  margin-top: var(--space-xs);
  font-style: italic;
}

.profile-section {
  margin-bottom: var(--space-lg);
}

.profile-section + .profile-section {
  padding-top: var(--space-lg);
  border-top: 1px solid var(--border-subtle);
}

.section-label {
  font-family: var(--font-ui);
  font-size: var(--font-size-xs);
  font-weight: 400;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-tertiary);
  margin-bottom: var(--space-md);
}

.credentials-warning {
  font-size: var(--font-size-xs);
  color: #8a4b2f;
  margin-bottom: var(--space-md);
  font-style: italic;
}

/* Bio */
.bio-container {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.bio-container textarea {
  width: 100%;
  border: none;
  border-bottom: 1px solid var(--border-subtle);
  border-radius: 0;
  padding: var(--space-sm) 0;
  font-family: var(--font-display);
  font-size: var(--font-size-base);
  font-weight: 400;
  font-style: italic;
  line-height: 1.7;
  color: var(--text-secondary);
  background: transparent;
  resize: none;
  transition: border-color var(--transition-fast);
}

.bio-container textarea:focus {
  outline: none;
  border-bottom-color: var(--text-primary);
}

.bio-container textarea::placeholder {
  color: var(--text-tertiary);
  font-style: italic;
}

.char-count {
  display: inline-flex;
  align-items: center;
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}

.bio-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-sm);
}

/* Switch component */
.switch {
  position: relative;
  display: inline-block;
  width: 50px;
  height: 28px;
  flex-shrink: 0;
}

.switch input {
  opacity: 0;
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  margin: 0;
  cursor: pointer;
  z-index: 2;
}

.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: transparent;
  border: 1px solid var(--border-medium);
  transition: .3s;
  border-radius: 0;
  pointer-events: none;
}

.slider:before {
  position: absolute;
  content: "";
  height: 18px;
  width: 18px;
  left: 4px;
  bottom: 4px;
  background-color: var(--text-tertiary);
  transition: .3s;
  border-radius: 0;
}

input:checked + .slider {
  border-color: var(--text-primary);
}

input:checked + .slider:before {
  transform: translateX(22px);
  background-color: var(--text-primary);
}

.disabled-text {
  opacity: 0.5;
  pointer-events: none;
}

/* Privacy */
/* Rows in the privacy section use .privacy-row grid style */

.toggle-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  /* keep same line-height so content doesn't grow taller than switch */
  line-height: 1.2;
}

.toggle-title {
  font-family: var(--font-display);
  font-size: var(--font-size-base);
  color: var(--text-primary);
}

.toggle-desc {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}

.privacy-row {
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: stretch;
  gap: var(--space-md);
  padding: var(--space-sm) var(--space-md);
  border: 1px solid var(--border-subtle);
  border-radius: 0;
  background: rgba(10, 10, 10, 0.02);
}

.privacy-row + .privacy-row {
  margin-top: var(--space-sm);
}

.privacy-control {
  display: flex;
  align-items: center;
  justify-content: flex-end;
}

.setting-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-md) 0;
  border-bottom: 1px solid var(--border-subtle);
}

.setting-row:last-child {
  border-bottom: none;
}

.setting-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  max-width: 100%;
}

.setting-title {
  font-family: var(--font-display);
  font-size: var(--font-size-base);
  color: var(--text-primary);
}

.setting-desc {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  line-height: 1.4;
}

.stepper-wrap {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  padding: 4px;
  border: 1px solid var(--border-subtle);
  border-radius: 0;
  min-height: 38px;
  background: var(--bg-secondary);
}

.stepper-value {
  font-family: var(--font-display);
  font-size: var(--font-size-base);
  color: var(--text-primary);
  min-width: 32px;
  text-align: center;
  display: flex;
  align-items: center;
  justify-content: center;
  height: 28px;
  border: 1px solid var(--border-subtle);
  padding: 0 var(--space-xs);
}

.stepper-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  background: transparent;
  border: 1px solid var(--border-subtle);
  font-family: var(--font-ui);
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
  cursor: pointer;
  padding: 0;
  line-height: 1;
  transition: all var(--transition-fast);
}

.stepper-btn:hover:not(:disabled) {
  border-color: var(--text-primary);
  background: rgba(10, 10, 10, 0.04);
  color: var(--text-primary);
}

.stepper-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

/* Integrations */
.input-group {
  margin-bottom: calc(var(--space-sm));
}

.input-group label {
  display: block;
  font-family: var(--font-ui);
  font-size: var(--font-size-sm);
  color: var(--text-primary);
  margin-bottom: var(--space-xs);
}

.text-input {
  width: 100%;
  flex: 1;
  border: 1px solid var(--border-subtle);
  border-radius: 0;
  min-height: 32px;
  padding: var(--space-sm) var(--space-md);
  font-family: var(--font-ui);
  font-size: var(--font-size-base);
  background: transparent;
  color: var(--text-primary);
  transition: border-color var(--transition-fast);
}

/* Compact credentials grid */
.credentials-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--space-md);
}

.credentials-actions {
  margin-top: var(--space-sm);
}

.btn-subtle.compact {
  padding: var(--space-xs) var(--space-sm);
  font-size: var(--font-size-xs);
}

@media (min-width: 720px) {
  .credentials-grid {
    grid-template-columns: 1fr 1fr;
    align-items: start;
  }
  /* Place confirm password under new password on wide screens */
  .credentials-grid > .input-group:nth-child(3) {
    grid-column: 2 / 3;
  }
}

/* Minimal modal styles for credentials */
.manage-credentials-row {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}
.cred-hint {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}
.manage-credentials-link {
  margin-top: calc(var(--space-xs));
}
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(10, 10, 10, 0.5);
  backdrop-filter: blur(1px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 60;
}
.modal {
  background: var(--bg-primary);
  border: 1px solid var(--text-primary);
  padding: 0;
  width: 100%;
  max-width: 520px;
  border-radius: var(--border-radius);
  overflow: hidden;
  box-shadow: 0 14px 36px rgba(10, 10, 10, 0.24);
}

.modal-body {
  padding: var(--space-lg);
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.modal-hint {
  margin: 0;
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  font-style: italic;
  line-height: 1.5;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-sm) var(--space-lg);
  border-bottom: 1px solid var(--border-subtle);
}

.modal-close {
  background: transparent;
  border: 1px solid transparent;
  border-radius: 0;
  width: 26px;
  height: 26px;
  padding: 0;
  font-size: 13px;
  line-height: 1;
  color: var(--text-tertiary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.modal-close:hover {
  border-color: var(--border-subtle);
  background: rgba(10, 10, 10, 0.04);
  color: var(--text-primary);
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-sm);
  margin-top: var(--space-sm);
  padding-top: var(--space-md);
  border-top: 1px solid var(--border-subtle);
}

/* Reuse login-form styles inside modal */
.login-form.compact {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  width: 100%;
}

.login-form.compact input {
  border: 1px solid var(--border-subtle);
  border-radius: var(--border-radius);
  padding: var(--space-sm) var(--space-md);
  background: transparent;
  font-size: var(--font-size-base);
  font-weight: 300;
  color: var(--text-primary);
  transition: border-color var(--transition-fast), background-color var(--transition-fast);
}

.login-form.compact input:focus {
  outline: none;
  border-color: var(--text-primary);
  background: rgba(10, 10, 10, 0.02);
}

.login-form.compact input::placeholder {
  color: var(--text-tertiary);
  font-weight: 300;
}

.login-modal-header .brand {
  font-family: var(--font-ui);
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.modal .btn-enter {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 84px;
  height: 32px;
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

.modal .btn-enter:hover {
  border-color: var(--text-primary);
  background: rgba(10, 10, 10, 0.04);
  color: var(--text-primary);
}

.modal-footer .btn-enter:last-child {
  border-color: var(--text-primary);
  color: var(--text-primary);
}

.modal-footer .btn-enter:last-child:hover {
  background: var(--text-primary);
  color: var(--bg-primary);
}

.modal .btn-enter:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.text-input:focus {
  outline: none;
  border-color: var(--text-primary);
}

.goodreads-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.integration-label {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.goodreads-input-row {
  width: 100%;
}

.goodreads-fixed-row {
  display: flex;
  align-items: center;
  min-height: 42px;
  gap: var(--space-sm);
  padding: var(--space-sm) var(--space-md);
  border: 1px solid var(--border-subtle);
  border-radius: 0;
}

.goodreads-fixed-value {
  font-family: var(--font-display);
  font-size: var(--font-size-base);
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.goodreads-fixed-value.empty {
  color: var(--text-tertiary);
  font-style: italic;
}

.goodreads-actions {
  display: flex;
  width: 100%;
  justify-content: flex-end;
  align-items: center;
  gap: var(--space-xs);
  flex-wrap: wrap;
}

.btn-inline-activate {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 30px;
  background: transparent;
  border: 1px solid var(--border-subtle);
  border-radius: 0;
  padding: 0 var(--space-sm);
  font-family: var(--font-ui);
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  text-transform: lowercase;
  letter-spacing: 0.04em;
  line-height: 1;
  text-align: center;
  white-space: nowrap;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-inline-activate:hover {
  background: rgba(10, 10, 10, 0.04);
  color: var(--text-primary);
  border-color: var(--text-primary);
}

.btn-inline-activate:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-inline-danger {
  border-color: color-mix(in srgb, var(--text-tertiary) 65%, #7a2f2f 35%);
  color: color-mix(in srgb, var(--text-tertiary) 75%, #7a2f2f 25%);
}

.btn-inline-danger:hover {
  border-color: #7a2f2f;
  color: #7a2f2f;
}

.input-help {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  margin: 0;
  line-height: 1.4;
}

.sub-option {
  padding: var(--space-sm) 0 var(--space-md);
}

.sub-option select {
  border: none;
  border-bottom: 1px solid var(--border-subtle);
  border-radius: 0;
  padding: var(--space-xs) 0;
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  background: transparent;
}

.sub-option select:focus {
  outline: none;
  border-bottom-color: var(--text-primary);
}

/* Export */
.export-actions {
  display: flex;
  gap: var(--space-sm);
  justify-content: flex-end;
  flex-wrap: wrap;
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
  font-weight: 300;
  color: var(--text-tertiary);
  letter-spacing: 0.04em;
  text-transform: lowercase;
  line-height: 1;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-option:hover {
  border-color: var(--text-primary);
  background: rgba(10, 10, 10, 0.04);
  color: var(--text-primary);
}

.btn-option:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

/* Footer */
.profile-footer {
  border-top: 1px solid var(--border-subtle);
  padding-top: var(--space-xl);
  margin-top: var(--space-xl);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.btn-logout {
  color: var(--text-tertiary);
}

.btn-delete-account {
  color: color-mix(in srgb, var(--text-tertiary) 70%, #7a2f2f 30%);
}

.btn-delete-account:hover {
  color: #7a2f2f;
  border-color: color-mix(in srgb, var(--border-subtle) 50%, #7a2f2f 50%);
}

.delete-warning {
  color: color-mix(in srgb, var(--text-tertiary) 50%, #7a2f2f 50%) !important;
}

.delete-confirm-label {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  margin-bottom: calc(var(--space-xs) * -0.5);
}

.btn-enter-danger {
  border-color: color-mix(in srgb, var(--text-tertiary) 50%, #7a2f2f 50%) !important;
  color: color-mix(in srgb, var(--text-tertiary) 50%, #7a2f2f 50%) !important;
}

.btn-enter-danger:hover:not(:disabled) {
  border-color: #7a2f2f !important;
  color: #7a2f2f !important;
  background: transparent !important;
}

/* Save feedback */
.save-feedback {
  position: fixed;
  bottom: var(--space-xl);
  left: 50%;
  transform: translateX(-50%);
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  letter-spacing: 0.05em;
}

@media (max-width: 640px) {
  .profile-nickname {
    font-size: var(--font-size-xl);
  }

  .nickname-row {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-xs);
  }

  .nickname-right {
    align-items: flex-start;
  }

  .manage-credentials-link {
    margin-top: 0;
  }

  .goodreads-fixed-row {
    flex-direction: column;
    align-items: flex-start;
  }

  .goodreads-actions {
    width: 100%;
    flex-wrap: wrap;
  }

  .bio-actions {
    flex-wrap: wrap;
    justify-content: flex-end;
  }

  .privacy-row {
    grid-template-columns: 1fr;
    gap: var(--space-sm);
  }

  .privacy-control {
    justify-content: flex-start;
  }

  .stepper-wrap {
    width: fit-content;
  }

  .export-actions {
    flex-direction: row;
    justify-content: flex-end;
    gap: var(--space-sm);
  }
}
</style>
