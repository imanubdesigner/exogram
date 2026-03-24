const LOCALE_STORAGE_KEY = 'exogram_locale'

export const LOCALIZED_ROUTE_PATHS = Object.freeze({
  landing: { es: '/', en: '/' },
  login: { es: '/login', en: '/login' },
  accept_invite: { es: '/accept-invite', en: '/accept-invite' },
  forgot_password: { es: '/olvide-contrasena', en: '/forgot-password' },
  reset_password: { es: '/reset-password', en: '/reset-password' },
  dashboard: { es: '/dashboard', en: '/dashboard' },
  library: { es: '/biblioteca', en: '/library' },
  favorites: { es: '/favs', en: '/favs' },
  notes: { es: '/notas', en: '/notes' },
  discover: { es: '/descubrir', en: '/discover' },
  profile: { es: '/perfil', en: '/profile' },
  graph: { es: '/graph', en: '/graph' },
  philosophy: { es: '/filosofia', en: '/philosophy' },
  philosophy_article: { es: '/filosofia/:articleId', en: '/philosophy/:articleId' },
  public_profile: { es: '/users/:nickname', en: '/users/:nickname' },
  thread: { es: '/hilos/:threadId', en: '/threads/:threadId' },
  waitlist: { es: '/lista-espera', en: '/waitlist' },
  waitlist_community: { es: '/red/comunidad', en: '/network/community' },
  changelog: { es: '/novedades', en: '/news' },
})

export const normalizeLocale = (locale) => (locale === 'en' ? 'en' : 'es')

export const getStoredLocale = () => {
  if (typeof window === 'undefined') return 'es'
  return normalizeLocale(window.localStorage.getItem(LOCALE_STORAGE_KEY))
}

const encodeParam = (value) => encodeURIComponent(String(value))

const buildPath = (template, params = {}) => {
  let missingParam = false
  const path = template.replace(/:([A-Za-z0-9_]+)/g, (_, key) => {
    const rawValue = params[key]
    if (rawValue === undefined || rawValue === null || rawValue === '') {
      missingParam = true
      return ''
    }
    const resolvedValue = Array.isArray(rawValue) ? rawValue[0] : rawValue
    return encodeParam(resolvedValue)
  })

  if (missingParam || /:[A-Za-z0-9_]+/.test(path)) return null
  return path
}

const buildQueryString = (query = {}) => {
  const search = new URLSearchParams()
  for (const [key, rawValue] of Object.entries(query)) {
    if (rawValue === undefined || rawValue === null) continue
    if (Array.isArray(rawValue)) {
      for (const item of rawValue) {
        if (item === undefined || item === null) continue
        search.append(key, String(item))
      }
      continue
    }
    search.append(key, String(rawValue))
  }
  const serialized = search.toString()
  return serialized ? `?${serialized}` : ''
}

export const getLocalizedPath = (routeName, locale, params = {}, query = {}, hash = '') => {
  const pathsByLocale = LOCALIZED_ROUTE_PATHS[routeName]
  if (!pathsByLocale) return null

  const normalizedLocale = normalizeLocale(locale)
  const template = pathsByLocale[normalizedLocale] || pathsByLocale.es
  const path = buildPath(template, params)
  if (!path) return null

  const queryString = buildQueryString(query)
  const normalizedHash = hash
    ? (String(hash).startsWith('#') ? String(hash) : `#${String(hash)}`)
    : ''

  return `${path}${queryString}${normalizedHash}`
}

export const getRouteAliases = (routeName, canonicalLocale = 'es') => {
  const pathsByLocale = LOCALIZED_ROUTE_PATHS[routeName]
  if (!pathsByLocale) return []

  const canonicalPath = pathsByLocale[normalizeLocale(canonicalLocale)] || pathsByLocale.es
  const aliases = Object.values(pathsByLocale).filter((path) => path !== canonicalPath)
  return Array.from(new Set(aliases))
}
