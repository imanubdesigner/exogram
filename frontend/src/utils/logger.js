/* eslint-disable no-console */
/**
 * Frontend Logger Utility
 * En producción (PROD) sólo se emiten errores reales.
 * En desarrollo (DEV) se emiten todos los niveles.
 */

const isDev = import.meta.env.DEV

export const logger = {
  debug: (msg, data = null) => {
    if (!isDev) return
    const ts = new Date().toISOString()
    data
      ? console.log(`[DEBUG ${ts}] ${msg}`, data)
      : console.log(`[DEBUG ${ts}] ${msg}`)
  },

  info: (msg, data = null) => {
    if (!isDev) return
    const ts = new Date().toISOString()
    data
      ? console.log(`%c[INFO ${ts}] ${msg}`, 'color: #2196f3', data)
      : console.log(`%c[INFO ${ts}] ${msg}`, 'color: #2196f3')
  },

  warn: (msg, data = null) => {
    if (!isDev) return
    const ts = new Date().toISOString()
    data
      ? console.warn(`%c[WARN ${ts}] ${msg}`, 'color: #ff9800', data)
      : console.warn(`%c[WARN ${ts}] ${msg}`, 'color: #ff9800')
  },

  error: (msg, error = null) => {
    const ts = new Date().toISOString()
    if (isDev) {
      console.error(`%c[ERROR ${ts}] ${msg}`, 'color: #f44336; font-weight: bold')
      if (error instanceof Error) {
        console.error('Message:', error.message)
        console.error('Stack:', error.stack)
      } else if (error !== null) {
        console.error('Details:', error)
      }
    } else {
      // En producción: loggear solo el mensaje, sin detalles internos
      console.error(`[ERROR] ${msg}`)
    }
  },

  performance: (label, duration) => {
    if (!isDev) return
    const ts = new Date().toISOString()
    console.log(`%c[PERF ${ts}] ${label}: ${duration}ms`, 'color: #9c27b0')
  },

  group: (label) => {
    if (!isDev) return
    console.group(`[GROUP] ${label}`)
  },

  groupEnd: () => {
    if (!isDev) return
    console.groupEnd()
  },

  table: (data, label = 'Data') => {
    if (!isDev) return
    console.log(`[TABLE] ${label}:`)
    console.table(data)
  },
}

export default logger
