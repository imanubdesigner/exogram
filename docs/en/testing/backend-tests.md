# Backend Tests

Coverage by app and how to run them.

---

## Running the Tests

```bash
# All tests with coverage
docker compose exec backend coverage run --source='.' manage.py test --verbosity=2

# Only one app
docker compose exec backend python manage.py test accounts --verbosity=2

# Only one module or test case
docker compose exec backend python manage.py test books.tests.test_parsers --verbosity=2
docker compose exec backend python manage.py test accounts.tests.ProfileUpdateTest --verbosity=2

# Coverage report
docker compose exec backend coverage report
docker compose exec backend coverage html   # generates htmlcov/
```

---

## Coverage by App

### `accounts/tests.py`

| Test case | What it covers |
|---|---|
| `ProfileUpdateTest` | PATCH bio, PATCH nickname (including sync with User.username), duplicate nickname rejected, unauthenticated access rejected, valid JPEG/PNG upload, non-image file rejected, avatar > 2 MB rejected. |
| `PublicProfileTest` | Public profile visible without auth, profile with hermit mode returns 404, hermit profile visible to the owner, non-existent profile returns 404. |
| `TokenRefreshTest` | Refresh with valid cookie returns new access token, refresh without cookie rejected. |
| `WaitlistTest` | Joining the waitlist creates the entry, idempotency (double POST with same email → 200 and a single entry), missing email → 400, listing by non-staff user → 403, listing by staff → 200. |
| `ValidateInvitationTest` | Valid token → 200 with `valid: true`, expired token (>72h) → 400 with `valid: false`, non-existent token → 404. |
| `AvatarSanitizationTest` | Re-encoding on upload (verifies that Pillow.open was called), PNG RGBA accepted. |
| `CurrentUserViewTest` | GET /me/ without auth → 401, with auth → 200 with nickname, password not exposed in response. |

### `books/tests/`

| File | What it covers |
|---|---|
| `test_auth_views.py` | Authentication endpoints specific to the books app (login required for library actions). |
| `test_export_views.py` | Highlight export: correct format, only the authenticated user's highlights. |
| `test_goodreads_activation.py` | Activation of the Goodreads integration. |
| `test_goodreads_scraper.py` | Goodreads HTML parser: books read, reading status, handling of malformed rows. |
| `test_highlight_import.py` | Import of Kindle and Goodreads CSV files: highlights detected, books created, duplicates handled. |
| `test_highlight_update.py` | PATCH highlight: note, visibility, favorite. Owner can edit, another user cannot. |
| `test_models.py` | Book, Highlight, Author models: creation, relationships, defaults. |
| `test_parsers.py` | KindleParser: parsing of clippings.txt, extraction of books and authors, handling of date formats. |
| `test_public_notes.py` | Public notes: only highlights with `visibility=public` and a non-empty note, from users without hermit mode. |
| `test_user_models_abc.py` | User-related models in the books app. |

### `social/tests.py`

| Test case | What it covers |
|---|---|
| `ModerationTest` | `analyze_toxicity`: clean text → low score, toxic text → high score, multiple URLs → elevated score, CAPS abuse → elevated score. |

### `threads/tests.py`

Covers thread creation, network restriction (only users in the same network can create threads),
idempotency (second attempt between the same users returns the existing thread),
sending messages, listing messages with pagination.

### `affinity/tests.py`

| Test case | What it covers |
|---|---|
| `UserClusterModelTest` | UserCluster creation, compute_user_centroid with highlights, update_user_cluster. |

---

## Frontend Tests

See [frontend-tests.md](./frontend-tests.md).

---

## Adding New Tests

1. Create the test in the file corresponding to the app (`accounts/tests.py`, etc.)
   or in `books/tests/test_<feature>.py` if the app already has multiple files.
2. Inherit from `django.test.TestCase` for DB tests.
3. Use `rest_framework.test.APIClient` for endpoint tests.
4. The `_make_user` and `_login` helpers from `accounts/tests.py` are a good pattern to follow.

```python
from django.test import TestCase
from rest_framework.test import APIClient

class MiFeatureTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        # setup...

    def test_algo(self):
        response = self.client.get('/api/mi-endpoint/')
        self.assertEqual(response.status_code, 200)
```

5. If the test requires throttling to be disabled, `settings_ci.py` already disables it for the entire suite. If the test needs to specifically verify throttling, use `@override_settings`.
