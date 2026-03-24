<template>
  <div class="toast-container">
    <transition-group name="toast" tag="div">
      <div
        v-for="toast in toasts"
        :key="toast.id"
        :data-testid="`toast-${toast.id}`"
        class="toast"
        :class="[`toast-${toast.type}`]"
      >
        <span class="toast-icon">
          <span v-if="toast.type === 'success'" class="icon">✓</span>
          <span v-else-if="toast.type === 'error'" class="icon">!</span>
          <span v-else-if="toast.type === 'warning'" class="icon">⚠</span>
          <span v-else-if="toast.type === 'info'" class="icon">ℹ</span>
        </span>

        <span class="toast-message">{{ toast.message }}</span>

        <button
          class="toast-close"
          @click="uiStore.dismissToast(toast.id)"
          :aria-label="i18n.t('common.close_notification')"
        >
          x
        </button>
      </div>
    </transition-group>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useUIStore } from '../stores/ui'
import { useI18nStore } from '../stores/i18n'

const uiStore = useUIStore()
const i18n = useI18nStore()

// Computed para facilitar acceso a toasts
const toasts = computed(() => uiStore.toasts)
</script>

<style scoped>
.toast-container {
  position: fixed;
  bottom: 20px;
  right: 20px;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  gap: 10px;
  pointer-events: none;
}

.toast {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 0;
  background-color: var(--bg-secondary);
  color: var(--text-primary);
  border: 1px solid var(--border-subtle);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  pointer-events: auto;
  min-width: 280px;
  max-width: 400px;
  font-size: var(--font-size-sm);
  line-height: 1.5;
  animation: slideIn 0.3s ease-out;
}

/* Tipos de toast - unified gray style */
.toast-success,
.toast-error,
.toast-warning,
.toast-info {
  background-color: var(--bg-secondary);
  color: var(--text-primary);
  border-color: var(--border-medium);
}

.toast-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  font-weight: bold;
}

.toast-message {
  flex: 1;
  word-break: break-word;
}

.toast-close {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 18px;
  height: 18px;
  padding: 0;
  background: none;
  border: none;
  color: inherit;
  font-size: 14px;
  cursor: pointer;
  line-height: 1;
  opacity: 0.5;
  transition: opacity var(--transition-fast);
}

.toast-close:hover {
  opacity: 1;
}

/* Animaciones */
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from {
  transform: translateX(100%);
  opacity: 0;
}

.toast-leave-to {
  transform: translateX(100%);
  opacity: 0;
}

@keyframes slideIn {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

/* Responsive */
@media (max-width: 640px) {
  .toast-container {
    bottom: 10px;
    right: 10px;
    left: 10px;
  }

  .toast {
    min-width: auto;
  }
}
</style>
