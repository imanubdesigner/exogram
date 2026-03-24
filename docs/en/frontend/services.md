# Services

API access layer. Each service groups requests related to a single domain.
All of them use the `apiFetch` and `apiRequest` functions from `api.js`.

---

## `api.js` — Base Client

The core of backend communication. Every request goes through here.

### `resolveApiBase(baseUrl?)`

Builds the API base URL:
- If `VITE_API_URL` is defined at build time: `<VITE_API_URL>/api`
- Otherwise: `http://localhost:8000/api`

### `apiFetch(path, options)`

Wrapper over `fetch` with:
1. **`credentials: 'include'`** on all requests — sends cookies automatically.
2. **`X-CSRFToken` header** on mutating requests (POST, PUT, PATCH, DELETE) — reads the
   `csrftoken` cookie (non-HttpOnly) and includes it as a header. Implements Double Submit Cookie.
3. **Auto-refresh on 401** — if the request fails due to an expired session, calls
   `/api/auth/token/refresh/` and retries the original request once.
   No infinite loop: the refresh endpoint and the login endpoint are excluded from the retry.
4. **`Content-Type: application/json`** by default, except when the body is `FormData`
   (in that case the browser sets the correct boundary).

### `apiRequest(path, options)`

Wrapper over `apiFetch` that also parses JSON and throws an `Error` if `response.ok` is false.
Returns `null` for 204 No Content responses.

Most services use `apiRequest`. `apiFetch` is used when direct access to the `Response` is needed
(for example, for binary downloads).

---

## `auth.js` — Authentication and Profile

| Function | Endpoint | Description |
|---|---|---|
| `login(nickname, password)` | `POST /auth/login/` | Login. Returns user data. |
| `logout()` | `POST /auth/logout/` | Logout. Blacklists the refresh token. |
| `getCurrentUser()` | `GET /me/` | Verifies session and returns user data or `null`. |
| `saveUser(user)` | — | Saves `auth_hint` in sessionStorage (hint for the guard). |
| `sendInvitation(email)` | `POST /invitations/` | Sends an invitation. |
| `validateInvitation(token)` | `GET /invitations/validate/<token>/` | Validates token. |
| `getMyInvitations()` | `GET /invitations/` | Lists my invitations. |
| `getInvitationStats()` | `GET /invitations/stats/` | Invitation stats. |
| `updateProfile(data)` | `PATCH /me/profile/` | Updates profile (multipart if avatar is present). |
| `updatePrivacy(settings)` | `PATCH /me/privacy/` | Updates privacy settings. |
| `completeOnboarding()` | `POST /me/onboarding/` | Marks onboarding as completed. |
| `exportData()` | `GET /me/export/` | Exports user data. |
| `getNetworkTree()` | `GET /affinity/graph/` | Network graph. |
| `getActivityHeatmap()` | `GET /me/activity/` | Activity heatmap. |

### Avatar handling in `updateProfile`

If `profileData` contains an `avatar` field (File object), the service builds
a `FormData` instead of sending JSON. This is required to upload binary files.
The rest of the profile fields are included in the same FormData.

---

## `highlights.js` — Library

| Function | Endpoint | Description |
|---|---|---|
| `fetchHighlights(params?)` | `GET /highlights/` | Lists highlights with optional filters. |
| `updateHighlight(id, data)` | `PATCH /highlights/<id>/` | Updates note, visibility, favorite. |
| `deleteHighlight(id)` | `DELETE /highlights/<id>/` | Deletes a highlight. |
| `importHighlights(file, format)` | `POST /books/import/` | Imports a Kindle or Goodreads file. |
| `exportHighlights(format?)` | `GET /books/export/` | Exports highlights. |

---

## `feed.js` — Discovery

| Function | Endpoint | Description |
|---|---|---|
| `searchHighlights(query, scope, limit)` | `POST /discovery/search/` | Semantic search. |
| `getSimilarUsers()` | `GET /discovery/users/` | Users with similar affinity. |

---

## `social.js` — Social

| Function | Endpoint | Description |
|---|---|---|
| `getComments(highlightId)` | `GET /highlights/<id>/comments/` | Comments on a highlight. |
| `postComment(highlightId, content)` | `POST /highlights/<id>/comments/` | Create a comment. |
| `deleteComment(commentId)` | `DELETE /comments/<id>/` | Delete own comment. |
| `followUser(nickname)` | `POST /users/<nickname>/follow/` | Follow a user. |
| `unfollowUser(nickname)` | `DELETE /users/<nickname>/follow/` | Unfollow a user. |
