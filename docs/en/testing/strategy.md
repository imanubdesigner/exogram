# Testing Strategy

---

## Philosophy

**Integration over unit tests.**

Most tests in Exogram make HTTP requests to the real endpoints and verify
end-to-end behavior: authentication, validations, responses, and database effects.
The database and the ORM are not mocked.

This comes with a cost (tests are slower than pure unit tests) and a benefit:
the tests are faithful to the real behavior. A test that passes with the real DB is more reliable
than one that passes with a mock that could diverge from the actual behavior.

---

## Test Infrastructure

### Database

Tests use a real PostgreSQL database (in CI, started as a service in the job).
The `PgVectorTestRunner` test runner enables the `vector` extension before migrating,
which allows testing models with `VectorField` without additional configuration.

### Password hashing

`settings_ci.py` configures `FastPBKDF2PasswordHasher` (iterations=1) so that user creation
in tests is fast (<1ms vs ~100ms with the production hasher).

### Throttling

`settings_ci.py` disables global throttling to avoid false negatives in tests that
make many consecutive requests. Tests that specifically test throttling must use
`override_settings` to restore the throttles for that particular test.

---

## Coverage

CI verifies that coverage does not drop below **60%** with `coverage --fail-under=60`.

This threshold is conservatively set by design: it is better to have a reachable threshold and raise
the bar over time than to block CI with an arbitrarily high threshold.

To view the coverage report locally:

```bash
coverage run --source='.' manage.py test
coverage report
coverage html   # generates htmlcov/ with per-file visualization
```

---

## What Is Tested

- **accounts:** all authentication flows, profile, avatar, invitations, waitlist.
- **books:** import, parsers, models, export, Goodreads, public notes, auth views.
- **social:** automatic comment moderation, toxicity scores.
- **threads:** CRUD for threads and messages, network restrictions.
- **affinity:** clustering, models.
- **frontend:** auth store, router guard, API URL resolution.

## What Is Not Tested (and Why)

- **Celery tasks:** tasks are tested indirectly through the views that trigger them. The internal behavior of Celery (retry, backoff) is not tested: that is Celery's responsibility, not the application's.
- **Migrations:** Django guarantees that migrations are consistent with `manage.py makemigrations --check` in CI.
- **External HTML scraping code (`goodreads_reading_scraper.py`):** Goodreads HTML changes without notice. The code has tolerant exceptions by design and is marked with `# pragma: no cover` in blocks that depend on external HTML structure.
- **Smoke tests (`smoke_tests/`):** excluded from the main runner. These are integration tests against a real instance and are run manually before a critical deploy.
