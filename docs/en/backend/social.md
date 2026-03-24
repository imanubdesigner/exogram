# App: social

Comments on highlights and the user follow system.

---

## Models

### `Comment`

Comment on a public highlight.

- `highlight` → FK to `Highlight`
- `author` → FK to `Profile`
- `content` — comment text
- `created_at`
- `moderation_score` — toxicity score assigned automatically (0.0–1.0)
- `moderation_reason` — textual reason if moderated
- `is_hidden` — if `True`, the comment is not visible. Result of automatic moderation.

### `UserFollow`

Follow relationship between users.

- `follower` → FK to `Profile`
- `following` → FK to `Profile`
- `created_at`
- Unique constraint: a user cannot follow the same user twice.

---

## Automatic moderation

### `analyze_toxicity(text) -> (score: float, reason: str)`

Local moderation engine with no external dependencies or APIs. Combines:

1. **Weighted toxic word list**: common insults in Spanish with different weights based on severity.
2. **Spam detection**: multiple URLs (>= 3 in the same message) increase the score.
3. **CAPS abuse**: a high percentage of uppercase letters in long text raises the score.
4. **Repetition**: excessively repeated characters ("jajajajajaja") as a noise signal.

The resulting score is a float between 0 and 1. Thresholds are applied in `moderate_comment`.

### `moderate_comment(comment) -> Comment`

Calls `analyze_toxicity`, assigns `moderation_score` and `moderation_reason`.
If the score exceeds the configured threshold, sets `is_hidden=True` automatically.
Hidden comments are stored but not returned by the API.

---

## Network restrictions

Comments are not open to everyone. The function `are_in_same_network(profile_a, profile_b)`
(in `accounts/utils.py`) verifies that both users are within the network distance
allowed by the trust level system.

A user with `comment_allowance_depth=0` can only interact with users at distance 0
in the network graph (in practice, they can view but cannot comment until promoted).
A user with `depth=1` can comment on highlights from users within their network.

---

## Endpoints

| Method | URL | Description |
|---|---|---|
| GET | `/api/highlights/<id>/comments/` | List comments on a highlight |
| POST | `/api/highlights/<id>/comments/` | Create comment (with automatic moderation) |
| DELETE | `/api/comments/<id>/` | Delete own comment |
| POST | `/api/users/<nickname>/follow/` | Follow a user |
| DELETE | `/api/users/<nickname>/follow/` | Unfollow a user |
| GET | `/api/me/following/` | Users I follow |
| GET | `/api/me/followers/` | Users who follow me |
