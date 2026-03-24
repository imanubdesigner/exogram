# Stores (Pinia)

Four independent stores. All use the Pinia Composition API (`defineStore` with a setup function).

---

## `useAuthStore` — `stores/auth.js`

The most important store. Manages the user session and everything related to authentication.

### State

| Ref | Type | Description |
|---|---|---|
| `user` | `object \| null` | Authenticated user data. `null` if there is no session. |
| `isLoadingAuth` | `boolean` | True while a login or auth action is being processed. |
| `authError` | `string \| null` | Last auth error message. |
| `isLoadingInvitation` | `boolean` | True while an invitation is being processed. |
| `invitationError` | `string \| null` | Last invitation error message. |
| `sentInvitations` | `array` | List of invitations sent by the user. |
| `invitationStats` | `object \| null` | Stats: total sent, remaining. |

### Computed

| Computed | Description |
|---|---|
| `isAuthenticated` | `true` if `user !== null` |
| `userName` | `user.nickname` or `''` |
| `isHermitMode` | `user.is_hermit_mode` or `false` |

### Methods

| Method | Description |
|---|---|
| `login(nickname, password)` | Calls the auth service, updates `user`. |
| `logout()` | Clears local state and calls the logout service. |
| `refreshCurrentUser()` | Reloads user data from `/api/me/`. Used by the guard. Merges with the existing state to avoid losing local fields. |
| `sendInvitation(email)` | Sends an invitation and refreshes stats. |
| `validateInvitation(token)` | Validates an invitation token (for the registration view). |
| `fetchMyInvitations()` | Loads sent invitations. |
| `fetchInvitationStats()` | Loads invitation stats. |
| `updateProfile(data)` | Updates profile and merges the response into `user`. |
| `updatePrivacy(settings)` | Updates privacy settings. |
| `completeOnboarding()` | Marks onboarding as completed. |
| `exportData()` | Requests a user data export. |
| `getNetworkTree()` | Fetches the network graph for the Graph view. |
| `getActivityHeatmap()` | Fetches reading activity heatmap data. |

### sessionStorage

The store uses `sessionStorage` for two UI flags that must survive page reloads
but not tab closes:
- `auth_hint` — hint for the guard that an active session exists (avoids an unnecessary request).
- `must_change_credentials` — flag that forces a redirect to profile.

Both are cleared on logout and when `getCurrentUser` returns null.

---

## `useHighlightsStore` — `stores/highlights.js`

Minimal state for the highlights library.

### State

| Ref | Description |
|---|---|
| `allHighlights` | Array of user highlights. |
| `isLoadingHighlights` | Loading state. |
| `highlightsError` | Last error. |

### Main Methods

- `fetchHighlights()` — loads all highlights from `/api/highlights/`.
- `deleteHighlight(id)` — deletes a highlight.

---

## `useI18nStore` — `stores/i18n.js`

Lightweight internationalization with no external dependencies.

### State

- `locale` — active locale (`'es'` or `'en'`). Persisted in `localStorage`.

### Methods

- `t(key)` — translates a key in the format `'section.subsection.key'`.
  If the key does not exist in the active locale, it falls back to Spanish. If it does not exist in either,
  it returns the key itself (visible in the UI as a signal of a missing translation).
- `toggleLocale()` — toggles between Spanish and English.
- `setLocale(locale)` — sets the locale directly.

The translation dictionary is embedded in the same file (`translations.es`, `translations.en`).
There are no external `.json` files or lazy-loaded translations.

---

## `useUIStore` — `stores/ui.js`

Interface state shared across all views.

### State

| Ref | Description |
|---|---|
| `toasts` | Array of temporary notifications (success/error messages). |
| `modals` | Map of open modals by name. |
| `isSidebarOpen` | State of the navigation sidebar. |
| `isProcessing` | Global loading state (slow operations). |
| `processingMessage` | Message shown alongside the global loading indicator. |

### Main Methods

- `showToast({ message, type, duration })` — adds a notification. Auto-removed after `duration` ms.
- `openModal(name)` / `closeModal(name)` — manages modals by name.
- `setProcessing(isProcessing, message)` — activates/deactivates the global loading state.
