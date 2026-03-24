/**
 * Highlights Store
 *
 * - books: lista liviana de libros con highlights_count (cargada al entrar a Library)
 * - highlightsByBook: todos los highlights de un libro, cargados al expandirlo
 * - allHighlights: todos los highlights del usuario (para Favorites y Home/stats)
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { apiRequest } from '../services/api'

function nextUrl(fullUrl) {
  const u = new URL(fullUrl)
  return u.pathname.replace(/^\/api/, '') + u.search
}

export const useHighlightsStore = defineStore('highlights', () => {
  // Lista liviana: [{id, title, authors, highlights_count}]
  const books = ref([])
  const isLoadingBooks = ref(false)

  // Highlights por libro: { [bookId]: { results, isLoading, loaded } }
  const highlightsByBook = ref({})

  // Todos los highlights (para Favorites y Home)
  const allHighlights = ref([])
  const isLoadingHighlights = ref(false)
  const highlightsError = ref(null)

  const fetchBooks = async () => {
    if (isLoadingBooks.value) return
    isLoadingBooks.value = true
    try {
      books.value = await apiRequest('/books/')
    } finally {
      isLoadingBooks.value = false
    }
  }

  // Carga todos los highlights de un libro de una vez (los libros rara vez tienen >100)
  const fetchHighlightsForBook = async (bookId) => {
    const existing = highlightsByBook.value[bookId]
    if (existing?.loaded || existing?.isLoading) return
    highlightsByBook.value[bookId] = { results: [], isLoading: true, loaded: false }
    try {
      let url = `/highlights/?book_id=${bookId}`
      while (url) {
        const response = await apiRequest(url)
        const results = response.results || (Array.isArray(response) ? response : [])
        highlightsByBook.value[bookId].results.push(...results)
        url = response.next ? nextUrl(response.next) : null
      }
      highlightsByBook.value[bookId].loaded = true
    } finally {
      highlightsByBook.value[bookId].isLoading = false
    }
  }

  // Para Favorites y Home: carga todos los highlights paginando
  const fetchHighlights = async () => {
    if (isLoadingHighlights.value) return
    isLoadingHighlights.value = true
    highlightsError.value = null
    try {
      const all = []
      let url = '/highlights/'
      while (url) {
        const response = await apiRequest(url)
        if (response.results) {
          all.push(...response.results)
          url = response.next ? nextUrl(response.next) : null
        } else {
          all.push(...(Array.isArray(response) ? response : []))
          url = null
        }
      }
      allHighlights.value = all
      return allHighlights.value
    } catch (error) {
      highlightsError.value = error.message
      throw error
    } finally {
      isLoadingHighlights.value = false
    }
  }

  const deleteHighlight = async (highlightId) => {
    try {
      await apiRequest(`/highlights/${highlightId}/`, { method: 'DELETE' })
      allHighlights.value = allHighlights.value.filter(h => h.id !== highlightId)
      for (const state of Object.values(highlightsByBook.value)) {
        state.results = state.results.filter(h => h.id !== highlightId)
      }
    } catch (error) {
      highlightsError.value = error.message
      throw error
    }
  }

  return {
    books,
    isLoadingBooks,
    highlightsByBook,
    allHighlights,
    isLoadingHighlights,
    highlightsError,
    fetchBooks,
    fetchHighlightsForBook,
    fetchHighlights,
    deleteHighlight,
  }
})
