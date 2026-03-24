# Pipeline de CI

Cómo funciona el pipeline de CI, por qué está estructurado así, y cómo
reproducir cada verificación localmente.

---

## Resumen

El CI corre en cada push y pull request hacia `main` o `develop`,
pero solo cuando cambian archivos bajo `backend/`, `frontend/`, o el workflow mismo.
Esto evita runs innecesarios al editar solo documentación o configuración
que no afecta la aplicación.

```
push / pull_request
        │
        ├──────────────────────┬──────────────────────┐
        ▼                      ▼                      │
  backend-lint           frontend                     │
  (lint + seguridad,     (audit + lint +              │
   sin servicios)         build + tests)              │
        │                      │                      │
        ▼ (si pasa)            │                      │
  backend-test                 │                      │
  (postgres + redis,           │                      │
   migrate + tests)            │                      │
        │                      │                      │
        └──────────┬───────────┘                      │
                   ▼                                  │
                   ci                                 │
            (status gate) ◄────────────────────────────
```

`backend-lint` y `frontend` arrancan de inmediato y corren en paralelo.
`backend-test` espera a `backend-lint`: no tiene sentido levantar PostgreSQL
y Redis si el código tiene un error de lint o un CVE conocido.
`ci` siempre corre al final y produce un único veredicto pass/fail, que es
lo que deben verificar las reglas de branch protection.

---

## Jobs

### `backend-lint` — Lint & Seguridad

**Timeout:** 10 minutos | **Servicios:** ninguno

| Paso | Herramienta | Qué verifica |
|------|-------------|--------------|
| flake8 | `flake8 .` | Errores de sintaxis, imports no usados, nombres indefinidos |
| isort | `isort --check-only .` | Consistencia en el orden de imports |
| bandit | `bandit -r . -ll -ii -c .bandit` | Patrones de código inseguros (SAST) |
| pip-audit | `pip-audit -r requirements.txt` | CVEs conocidos en dependencias Python |

La configuración vive en `backend/setup.cfg` (flake8, isort) y `backend/.bandit` (bandit).

### `backend-test` — Tests & Cobertura

**Timeout:** 20 minutos | **Servicios:** PostgreSQL 16 + pgvector, Redis 7

Corre solo después de que `backend-lint` tiene éxito.

| Paso | Qué hace |
|------|----------|
| Habilitar pgvector | Crea la extensión `vector` antes de las migraciones |
| Django system checks | `manage.py check` — valida settings y configuración de apps |
| Detectar migraciones faltantes | `makemigrations --check --dry-run` — falla si hay un cambio de modelo sin migración |
| Aplicar migraciones | `migrate --noinput` |
| Tests + cobertura | Test runner de Django con coverage; falla si la cobertura cae por debajo del 70% |
| Subir artifact | `backend/coverage.xml` retenido por 14 días |

**Entorno usado:**

| Variable | Valor en CI |
|----------|-------------|
| `DJANGO_SETTINGS_MODULE` | `exogram.settings_ci` |
| `DATABASE_URL` | `postgres://exogram:test_password@localhost:5432/exogram_test` |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` |
| `SECRET_KEY` | Valor fijo de test (no se usa en producción) |

`exogram/settings_ci.py` extiende los settings base con:
- Rate limiting desactivado (thresholds en 100 000/h)
- `FastPBKDF2PasswordHasher` para acelerar el hashing de contraseñas en tests

### `frontend` — Audit, Lint, Build & Tests

**Timeout:** 15 minutos | **Servicios:** ninguno

Corre en paralelo con `backend-lint`, completamente independiente del backend.

| Paso | Herramienta | Qué verifica |
|------|-------------|--------------|
| npm audit | `npm audit --audit-level=high` | CVEs conocidos en dependencias JS |
| ESLint | `npm run lint` | Calidad de código y reglas de seguridad |
| Build | `npm run build` | Build de producción de Vite (detecta errores de import) |
| Tests | `npm test` | Tests unitarios con Vitest |

### `ci` — Status Gate

**Timeout:** 5 minutos | **Depende de:** los tres jobs anteriores

Corre con `if: always()` para producir un resultado incluso cuando los jobs
anteriores fallan o son cancelados. Sale con código 1 si algún job no tuvo éxito.

Este es el único job que debe figurar en las reglas de branch protection.
Listar los jobs individuales requeriría actualizar la regla de protección cada vez
que se agrega o renombra un job.

---

## Concurrencia

```yaml
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true
```

Si se hace push de un nuevo commit a un branch mientras el CI aún está corriendo,
el run anterior se cancela automáticamente. Esto ahorra minutos de GitHub Actions
en branches con actividad frecuente y en colas de Dependabot.

---

## Caché

| Capa | Estrategia |
|------|-----------|
| Paquetes Python | Caché nativa de `setup-python@v5`, clave basada en `backend/requirements.txt` |
| Node modules | Caché nativa de `setup-node@v4`, clave basada en `frontend/package-lock.json` |

Ambos cachés están acotados al OS y se invalidan automáticamente cuando
cambia el lock file.

---

## Ejecutar las verificaciones localmente

### Lint de backend

```bash
cd backend
pip install flake8 isort bandit pip-audit
flake8 .
isort --check-only .
bandit -r . -x ./migrations,./smoke_tests -ll -ii -c .bandit
pip-audit -r requirements.txt
```

### Tests de backend

Requiere PostgreSQL con pgvector y Redis corriendo localmente (usá `docker compose up db redis`).

```bash
cd backend
export DJANGO_SETTINGS_MODULE=exogram.settings_ci
export DATABASE_URL=postgres://exogram:dev_password@localhost:5432/exogram
export SECRET_KEY=cualquier-valor-para-tests-locales
export CELERY_BROKER_URL=redis://localhost:6379/0
export CELERY_RESULT_BACKEND=redis://localhost:6379/0
export ALLOWED_HOSTS=localhost,127.0.0.1,testserver

coverage run --source='.' manage.py test --verbosity=2
coverage report --fail-under=70
```

### Frontend

```bash
cd frontend
npm ci
npm audit --audit-level=high
npm run lint
npm run build
npm test
```

---

## Configuración de branch protection

En **Settings → Branches → Branch protection rules** para `main`:

- Activar **Require status checks to pass before merging**
- Agregar solo el job `CI — All checks passed` como check requerido
- Activar **Require branches to be up to date before merging**

No agregar `backend-lint`, `backend-test` o `frontend` individualmente —
el status gate los cubre a todos.

---

## Agregar una nueva verificación

1. Agregar el step al job correspondiente (`backend-lint`, `backend-test` o `frontend`).
2. Si la nueva verificación necesita sus propios servicios o tiene un timeout muy diferente,
   considerar un nuevo job que alimente a `ci` via `needs`.
3. Actualizar este documento y `docs/es/security/ci-scanning.md` si la verificación
   es de seguridad.
