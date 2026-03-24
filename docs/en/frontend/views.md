# Views

One view per route. All are lazy-loaded (`() => import(...)`) to reduce the initial bundle.
Views with `requiresAuth: true` are not accessible without an active session.

---

## Public Views

### `LandingPage.vue`
Welcome page. Presents the project, its values, and the invitation system.
Links to registration (waitlist), login, and philosophy content.
Does not require a session.

### `Login.vue`
Login form with nickname and password.
If the user already has a session (detected by the guard), redirects to the dashboard.
Link to password recovery.

### `AcceptInvite.vue`
Registration flow with an invitation token.
1. Reads the token from the URL, calls `validateInvitation(token)`.
2. If the token is valid, shows the registration form (nickname, password).
3. If it has expired or does not exist, shows an error.

### `ForgotPassword.vue` / `ResetPassword.vue`
Two steps of the password reset flow:
- `ForgotPassword`: email form → calls `POST /api/auth/password-reset/`.
- `ResetPassword`: reads the token from the URL, new password form.

### `Waitlist.vue`
Form to sign up for the waitlist. Fields: email, optional message.

### `Philosophy.vue`
Displays project articles (philosophy, manifesto). Consumes the `articles` app from the backend.
Accepts an optional `articleId` parameter to display a specific article.

### `PublicProfile.vue`
Public profile of a user (by nickname). Shows public highlights, public notes, and bio.
If the user has hermit mode active, the backend returns 404 and the view handles it.

---

## Authenticated Views

### `Dashboard.vue`
Main post-login view. Activity summary: latest highlights, network activity,
reading heatmap. Entry point to all other sections.

### `Library.vue`
Personal library. List of highlights with filters (book, favorites, visibility).
The `/favs` route also uses this component, pre-filtered by `is_favorite=true`.
From here, the user can edit notes, change visibility, and mark/unmark as favorite.

### `Notes.vue`
View focused on highlights with a personal note. Displays the highlight content
alongside the user's note. Filtered by highlights that have a non-empty note.

### `Import.vue`
Highlight import flow.
1. The user uploads a file (Kindle `.txt` or Goodreads `.csv`).
2. A preview of the detected highlights is shown.
3. On confirmation, it is sent to `/api/books/import/` and the embedding tasks are triggered.

### `Discover.vue`
Semantic search and discovery of like-minded readers.
- Search field → vector similarity query against own highlights or the network.
- List of users with similar reading affinity.
- Book suggestions shared with other readers.

### `Profile.vue`
The authenticated user's own profile.
- View and edit nickname, bio, avatar.
- Privacy settings (hermit mode, is_discoverable).
- List of sent invitations and stats.
- Personal data export.
- Onboarding flow on first access.

### `Graph.vue`
Visualization of the user's network graph.
Displays nodes (users) and edges (connections by invitation / affinity).
Uses `v-network-graph` with a `d3-force` force layout.
Consumes `getNetworkTree()` from the auth store.

### `ThreadView.vue`
Private message thread view.
- Loads the thread by ID and displays the message history.
- Real-time reply form.
- Backward pagination (load older messages) via the `before` parameter.

### `CommunityWaitlist.vue`
View for users with invitations to activate people from the waitlist.
Lists waitlist entries and allows activating one at a time by consuming an invitation.
Only accessible to users with `invitations_remaining > 0`.
