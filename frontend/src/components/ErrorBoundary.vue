<template>
  <slot v-if="!hasError" />
  <div v-else class="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 px-4">
    <div class="text-center max-w-md">
      <p class="text-4xl mb-4">⚠️</p>
      <h1 class="text-xl font-semibold text-gray-800 dark:text-gray-100 mb-2">
        Algo salió mal
      </h1>
      <p class="text-gray-500 dark:text-gray-400 mb-6 text-sm">
        Ocurrió un error inesperado. Recargá la página para continuar.
      </p>
      <button
        @click="reload"
        class="px-4 py-2 rounded bg-indigo-600 text-white text-sm hover:bg-indigo-700 transition"
      >
        Recargar página
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onErrorCaptured } from 'vue'
import logger from '../utils/logger'

const hasError = ref(false)

onErrorCaptured((err) => {
  hasError.value = true
  logger.error('ErrorBoundary capturó un error de renderizado', err)
  // Retornar false evita que el error siga propagándose
  return false
})

function reload() {
  window.location.reload()
}
</script>
