# Contributing

Guide for working on the project in a way that is consistent with the rest of the codebase.

---

## Workflow

1. Create a branch from `main`: `git checkout -b feature/short-description`
2. Make the changes.
3. Verify that CI would pass locally (see the checks section).
4. Create the PR against `main`.
5. CI runs automatically (tests, lint, security, frontend build).
6. Once approved and merged, the deploy runs automatically if CI passes.

---

## Checks before pushing

```bash
# Backend — from backend/
flake8 .
isort --check-only .
bandit -r . -x ./migrations,./smoke_tests -ll -ii -c .bandit
pip-audit -r requirements.txt
python manage.py test --verbosity=2
python manage.py makemigrations --check --dry-run   # there should be no pending migrations

# Frontend — from frontend/
npm run build
npm test
npm audit --audit-level=high
```

---

## Code conventions (backend)

**Style:** flake8 with `max-line-length = 120`. isort with `profile = black`.

**Imports:** ordered with isort. When in doubt: `isort archivo.py` to sort automatically.

**Naming:**
- Views: `ResourceNameView` (e.g.: `ProfileUpdateView`, `ThreadListCreateView`)
- Tests: `ResourceNameTest` with methods `test_description_of_behavior`
- Celery tasks: snake_case, `_task` suffix if periodic (e.g.: `promote_trust_levels_task`)

**Migrations:** do not edit existing migrations. If there is an error in a migration not
yet applied in production, create a new migration that corrects the state.

**Logging:** use `logger = logging.getLogger(__name__)` in each module.
Use `logger.info`, `logger.warning`, `logger.exception` (not `print`).

---

## How to add a new Django app

1. `python manage.py startapp app_name`
2. Add `'app_name'` to `INSTALLED_APPS` in `settings.py`.
3. Create `app_name/urls.py` and add the include in `exogram/urls.py`.
4. Create `app_name/tests.py` with at least one basic test.
5. Create the initial migration: `python manage.py makemigrations app_name`.
6. Document in `docs/backend/app_name.md`.

---

## How to add a migration

```bash
# After modifying a model
docker compose exec backend python manage.py makemigrations <app>

# Verify the migration is as expected
docker compose exec backend python manage.py sqlmigrate <app> <migration_number>

# Apply
docker compose exec backend python manage.py migrate
```

In CI, `python manage.py makemigrations --check --dry-run` fails if there are
pending migrations that have not been generated. This guarantees that models and migrations are always in sync.

---

## How to add an environment variable

1. Add the read in `settings.py` with `config('VAR_NAME', default=safe_value)`.
2. Document in [`docs/operations/environment-variables.md`](./operations/environment-variables.md).
3. Add to the list of GitHub secrets if it is needed in production.
4. Add to `deploy.yml` in the "Render backend env" or "Render root env" step.

---

## How to add a route to the frontend

1. Define the path in `src/router/localizedRoutes.js` (with es and en versions).
2. Add the route in `src/router/index.js` with `localizedRoute(...)`.
3. Create the view in `src/views/ViewName.vue`.
4. Document in [`docs/frontend/views.md`](./frontend/views.md).

---

## How to add an ADR

When a significant architectural decision is made:

1. Create `docs/adr/NNNN-kebab-case-title.md` with the next sequential number.
2. Follow the format defined in [`docs/adr/README.md`](./adr/README.md).
3. Add the entry to the index in that same README.

Decisions that warrant an ADR: technology changes, new external integrations,
changes to the security model, design decisions with non-obvious trade-offs.

---

## Commit format

No strict convention, but descriptive messages in Spanish or English:

```
fix: corregir validación de token expirado en ValidateInvitationView
feat: agregar exportación en formato Markdown
chore: actualizar Django a 5.2.12
docs: documentar flujo de password reset
```

Avoid messages like `fix stuff`, `WIP`, `changes`.
