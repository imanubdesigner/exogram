<template>
  <div class="pagination-controls" v-if="totalPages > 1">
    <button 
      class="btn-pagination" 
      :disabled="modelValue <= 1"
      @click="prevPage"
      aria-label="anterior"
    >
      &larr;
    </button>
    <span class="pagination-indicator">{{ modelValue }}<span class="muted">/</span>{{ totalPages }}</span>
    <button 
      class="btn-pagination" 
      :disabled="modelValue >= totalPages"
      @click="nextPage"
      aria-label="siguiente"
    >
      &rarr;
    </button>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: Number,
    required: true
  },
  totalItems: {
    type: Number,
    required: true
  },
  pageSize: {
    type: Number,
    default: 5
  }
})

const emit = defineEmits(['update:modelValue'])

const totalPages = computed(() => Math.ceil(props.totalItems / props.pageSize))

const prevPage = () => {
  if (props.modelValue > 1) {
    emit('update:modelValue', props.modelValue - 1)
  }
}

const nextPage = () => {
  if (props.modelValue < totalPages.value) {
    emit('update:modelValue', props.modelValue + 1)
  }
}
</script>

<style scoped>
.pagination-controls {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: var(--space-md);
  margin-top: var(--space-lg);
  padding: var(--space-md) 0;
}

.btn-pagination {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: transparent;
  border: 1px solid var(--border-subtle);
  border-radius: 0;
  color: var(--text-tertiary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-pagination:hover:not(:disabled) {
  border-color: var(--text-primary);
  color: var(--text-primary);
  background: rgba(10, 10, 10, 0.04);
}

.btn-pagination:disabled {
  opacity: 0.25;
  cursor: not-allowed;
}

.pagination-indicator {
  font-family: var(--font-ui);
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
  letter-spacing: 0.1em;
}

.muted {
  color: var(--text-tertiary);
  margin: 0 2px;
}
</style>
