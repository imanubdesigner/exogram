# Authorization

What each user type can do and how controls are applied.

---

## Access levels

### Anonymous (no session)

Can:
- View the landing page, login, philosophy, waiting list.
- Validate an invitation token (`GET /api/invitations/validate/<token>/`).
- Register with an invitation token (`POST /api/auth/register/`).
- Join the waiting list (`POST /api/waitlist/`).
- View public profiles of users who do not have hermit mode enabled.
- View a user's public notes (`GET /api/books/public-notes/<nickname>/`).

Cannot:
- Access any endpoint that requires `IsAuthenticated`.

### Authenticated user (depth=0, newly registered)

Can:
- Everything the anonymous user can do.
- View and edit their own profile, highlights, and notes.
- Import and export highlights.
- View their network graph and discovery feed.
- Search by semantic similarity.
- Read but **not comment** on others' highlights (restriction by trust level).

Cannot (yet):
- Comment on other users' highlights (requires depth=1 or compatible network).
- Start private threads with users outside their network.

### Established user (depth=1, ≥30 days)

Can do everything above, plus:
- Comment on highlights from users within their network.
- Start private threads with users within their network.

### Staff (`is_staff=True`)

Can additionally:
- View the full waitlist (`GET /api/waitlist/`).
- Access the Django Admin (if they know the URL configured in `ADMIN_URL`).

### Superuser (`is_superuser=True`)

Full access to the Django Admin. Complete management of all entities.

---

## Trust levels and network distance

The authorization system for comments and private messages is not solely based on
individual trust level: it also considers the **distance in the network graph**.

`are_in_same_network(profile_a, profile_b)` verifies that the distance between the two
profiles in the invitation and follow graph is within the limit allowed by
their respective `comment_allowance_depth`.

This means a user with depth=1 can comment on highlights from users
within their network, not from any user on the platform.

---

## Hermit mode

When `Profile.is_hermit_mode = True`:
- `GET /api/users/<nickname>/` returns 404 for any user other than the owner.
- The profile does not appear in discovery results or in others' graphs.
- The user's own highlights and data are accessible normally.

This allows users who want full privacy to remain on the platform
without being visible to others.

---

## `must_change_credentials`

A flag that is activated when a user needs to update their nickname or password
(for example, on the first login after registration).

When active:
- The router guard redirects to the profile on every navigation.
- The user cannot go to any other view until the change is completed.
- Once updated and `completeOnboarding()` is called, the flag is cleared.

---

## DRF permissions

The base configuration in `settings.py`:

```python
'DEFAULT_PERMISSION_CLASSES': [
    'rest_framework.permissions.IsAuthenticatedOrReadOnly',
]
```

Write-only endpoints (create invitations, send messages) use explicit `IsAuthenticated`.
Staff endpoints use `IsAdminUser`.
Purely public endpoints (health, waitlist POST, validate invitation) use explicit `AllowAny`.
