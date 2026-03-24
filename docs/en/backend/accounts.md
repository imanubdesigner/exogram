# App: accounts

Manages everything related to users: registration, authentication, profile, invitations, and the waitlist.

---

## Models

### `Profile`

Extends Django's `User` with Exogram-specific fields.
Automatically created for each `User` via a `post_save` signal.

Relevant fields:
- `nickname` — the user's public name (unique). Also synced with `User.username`.
- `bio` — personal description.
- `avatar` — profile picture. Validated with magic bytes, re-encoded on the server to strip EXIF data.
- `verified_email` — the user's verified email. Separate from `User.email`.
- `is_hermit_mode` — when active, the profile is not publicly visible. The user exists but is invisible to others. A 404 is returned to anyone querying their profile.
- `comment_allowance_depth` — trust level. `0` = new user, `1` = promoted after 30 days.
- `invitations_remaining` — how many invitations the user can still send.
- `trust_promoted_at` — timestamp of the last automatic promotion.
- `created_at`

### `Invitation`

Invitation sent by a registered user to an email address.

Fields:
- `email` — recipient (unique; cannot receive two invitations).
- `invited_by` → FK to `User`.
- `token_hash` — HMAC-SHA256 of the raw token. The raw token is never stored.
- `token_created_at` — generation timestamp. The 72-hour validation window is calculated from here.
- `expires_at` — expiration of platform access (30 days by default, configurable).
- `accepted_at` — timestamp of successful registration.
- `token` — legacy UUID (do not use in new logic).

### `Waitlist`

Registry of people interested in joining who do not yet have an invitation.

Fields:
- `email` (unique)
- `message` — optional message from the applicant.
- `created_at`
- `activated_at` — timestamp if activated.
- `activated_by` → FK to the `Profile` of the user who activated it.

Method `activate(activating_profile)`: marks the entry as active and deducts one invitation from the activator.

### `PasswordResetToken`

Single-use token for resetting a password.

Fields:
- `user` → FK to `User`.
- `token_hash` — HMAC-SHA256 of the raw token.
- `expires_at` — TTL configurable via `PASSWORD_RESET_TOKEN_TTL_HOURS` (default: 2h).
- `used_at` — if not null, the token has already been consumed.

### Hash functions

```python
build_invitation_token_hash(raw_token) -> str
build_password_reset_token_hash(raw_token) -> str
```

Both use `HMAC-SHA256` with `SECRET_KEY` as the key. This protects against
rainbow table attacks: without the `SECRET_KEY`, a compromised hash cannot be reversed to the original token.

---

## Main flows

### Invitation-based registration

1. User A sends an invitation to `email@example.com` → `POST /api/invitations/`
2. System generates a raw token (`secrets.token_urlsafe(32)`), stores its HMAC hash.
3. Email with link `<FRONTEND_BASE_URL>/accept-invite/<raw_token>` is sent to the recipient.
4. Recipient validates the token → `GET /api/invitations/validate/<token>/`
   - Returns `{valid: true, email: "..."}` if the token is valid and has not expired (< 72h).
   - Returns `{valid: false}` if expired or not found.
5. Recipient completes registration → `POST /api/auth/register/` with nickname, password, and token.

### Login

`POST /api/auth/login/` with `nickname` and `password`.
- If correct: issues `exo_access` and `exo_refresh` cookies (HttpOnly, SameSite=Lax).
- Returns user data.

Login is done with **nickname**, not email. This separates the public identity (nickname) from the private one (email).

### Token refresh

`POST /api/auth/token/refresh/`
- Reads the `exo_refresh` cookie, validates and rotates it: issues a new `exo_access` and a new `exo_refresh`.
- The previous refresh token is added to simplejwt's blacklist (table in PostgreSQL).

### Logout

`POST /api/auth/logout/`
- Blacklists the active refresh token.
- Clears both cookies from the client.

### Password reset

1. `POST /api/auth/password-reset/` with `email` → generates token, sends email.
2. `POST /api/auth/password-reset/confirm/` with `token`, `password`, `password_confirm` → changes the password.
- The token is invalidated after use (`used_at = now()`).
- Only one active token per user (previous ones are deleted before generating a new one).

---

## Avatar security

Avatar validation operates in two layers:

1. **`validate_avatar`** (model validator): checks size (max 2 MB) and file byte signature (actual magic bytes, not the client's Content-Type). SVG is explicitly rejected to prevent embedded XSS.

2. **Re-encoding with Pillow** (`accounts/image_utils.py`): after validation, the avatar is opened with `Image.open()` and saved again. This removes any EXIF metadata (including GPS coordinates) and neutralizes malicious payloads that Pillow might have ignored during parsing but would remain in the binary file.

---

## Endpoints

| Method | URL | Description |
|---|---|---|
| POST | `/api/auth/login/` | Login with nickname + password |
| POST | `/api/auth/logout/` | Logout, blacklists refresh token |
| POST | `/api/auth/token/refresh/` | Renew access token |
| GET | `/api/me/` | Authenticated user data |
| PATCH | `/api/me/profile/` | Update profile (bio, nickname, avatar) |
| GET | `/api/users/<nickname>/` | Public profile (respects hermit mode) |
| POST | `/api/waitlist/` | Join the waitlist |
| GET | `/api/waitlist/` | List waitlist entries (staff only) |
| POST | `/api/invitations/` | Send invitation |
| GET | `/api/invitations/validate/<token>/` | Validate invitation token |
| POST | `/api/auth/register/` | Register with invitation token |
| POST | `/api/auth/password-reset/` | Request password reset |
| POST | `/api/auth/password-reset/confirm/` | Confirm reset with token |

---

## Hermit mode

When `Profile.is_hermit_mode = True`:
- `GET /api/users/<nickname>/` returns 404 to any user other than the profile owner.
- The user does not appear in search results or discovery.
- Their own data remains accessible to themselves.

---

## Trust levels

| Level | `comment_allowance_depth` | Condition |
|---|---|---|
| New | 0 | Upon registration |
| Established | 1 | >= 30 days of seniority, promoted by a daily Celery task |

The `promote_trust_levels_task` task (in `books/tasks.py`) runs daily and bulk-promotes
all eligible users who have not been manually promoted.
