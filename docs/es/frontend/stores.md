# Stores (Pinia)

Cuatro stores independientes. Todos usan la Composition API de Pinia (`defineStore` con setup function).

---

## `useAuthStore` — `stores/auth.js`

El store más importante. Gestiona la sesión del usuario y todo lo relacionado con autenticación.

### Estado

| Ref | Tipo | Descripción |
|---|---|---|
| `user` | `object \| null` | Datos del usuario autenticado. `null` si no hay sesión. |
| `isLoadingAuth` | `boolean` | True mientras se procesa login o una acción de auth. |
| `authError` | `string \| null` | Mensaje del último error de auth. |
| `isLoadingInvitation` | `boolean` | True mientras se procesa una invitación. |
| `invitationError` | `string \| null` | Mensaje del último error de invitación. |
| `sentInvitations` | `array` | Lista de invitaciones enviadas por el usuario. |
| `invitationStats` | `object \| null` | Estadísticas: total enviadas, restantes. |

### Computed

| Computed | Descripción |
|---|---|
| `isAuthenticated` | `true` si `user !== null` |
| `userName` | `user.nickname` o `''` |
| `isHermitMode` | `user.is_hermit_mode` o `false` |

### Métodos

| Método | Descripción |
|---|---|
| `login(nickname, password)` | Llama al servicio de auth, actualiza `user`. |
| `logout()` | Limpia el estado local y llama al servicio de logout. |
| `refreshCurrentUser()` | Recarga los datos del usuario desde `/api/me/`. Usado por el guard. Hace merge con el estado existente para no perder campos locales. |
| `sendInvitation(email)` | Envía invitación y refresca las stats. |
| `validateInvitation(token)` | Valida un token de invitación (para la vista de registro). |
| `fetchMyInvitations()` | Carga las invitaciones enviadas. |
| `fetchInvitationStats()` | Carga estadísticas de invitaciones. |
| `updateProfile(data)` | Actualiza perfil y fusiona la respuesta en `user`. |
| `updatePrivacy(settings)` | Actualiza configuración de privacidad. |
| `completeOnboarding()` | Marca el onboarding como completado. |
| `exportData()` | Solicita exportación de datos del usuario. |
| `getNetworkTree()` | Obtiene el grafo de red para la vista Graph. |
| `getActivityHeatmap()` | Obtiene datos del heatmap de actividad lectora. |

### sessionStorage

El store usa `sessionStorage` para dos flags de UI que deben sobrevivir a recargas
pero no a cierre de pestaña:
- `auth_hint` — hint para el guard de que hay sesión activa (evita un request innecesario).
- `must_change_credentials` — flag que fuerza redirección a perfil.

Ambos se limpian en logout y cuando `getCurrentUser` devuelve null.

---

## `useHighlightsStore` — `stores/highlights.js`

Estado mínimo de la biblioteca de highlights.

### Estado

| Ref | Descripción |
|---|---|
| `allHighlights` | Array de highlights del usuario. |
| `isLoadingHighlights` | Loading state. |
| `highlightsError` | Último error. |

### Métodos principales

- `fetchHighlights()` — carga todos los highlights desde `/api/highlights/`.
- `deleteHighlight(id)` — elimina un highlight.

---

## `useI18nStore` — `stores/i18n.js`

Internacionalización liviana sin dependencias externas.

### Estado

- `locale` — idioma activo (`'es'` o `'en'`). Persiste en `localStorage`.

### Métodos

- `t(key)` — traduce una clave del formato `'seccion.subseccion.clave'`.
  Si la clave no existe en el idioma activo, cae al español. Si no existe en ninguno,
  devuelve la propia clave (visible en la UI como señal de traducción faltante).
- `toggleLocale()` — alterna entre español e inglés.
- `setLocale(locale)` — establece el idioma directamente.

El diccionario de traducciones está embebido en el mismo archivo (`translations.es`, `translations.en`).
No hay archivos `.json` externos ni carga lazy de traducciones.

---

## `useUIStore` — `stores/ui.js`

Estado de interfaz transversal a todas las vistas.

### Estado

| Ref | Descripción |
|---|---|
| `toasts` | Array de notificaciones temporales (mensajes de éxito/error). |
| `modals` | Mapa de modales abiertos por nombre. |
| `isSidebarOpen` | Estado del sidebar de navegación. |
| `isProcessing` | Loading state global (operaciones lentas). |
| `processingMessage` | Mensaje que acompaña al loading global. |

### Métodos principales

- `showToast({ message, type, duration })` — agrega una notificación. Se auto-elimina tras `duration` ms.
- `openModal(name)` / `closeModal(name)` — gestión de modales por nombre.
- `setProcessing(isProcessing, message)` — activa/desactiva el loading global.
