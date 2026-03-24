# Contribución

Guía para trabajar en el proyecto de forma consistente con el resto del código.

---

## Flujo de trabajo

1. Crear una rama desde `main`: `git checkout -b feature/descripcion-corta`
2. Hacer los cambios.
3. Verificar que el CI pasaría localmente (ver sección de verificaciones).
4. Crear el PR contra `main`.
5. El CI corre automáticamente (tests, lint, seguridad, build frontend).
6. Una vez aprobado y mergeado, el deploy corre automáticamente si el CI pasa.

---

## Verificaciones antes de hacer push

```bash
# Backend — desde backend/
flake8 .
isort --check-only .
bandit -r . -x ./migrations,./smoke_tests -ll -ii -c .bandit
pip-audit -r requirements.txt
python manage.py test --verbosity=2
python manage.py makemigrations --check --dry-run   # no debe haber migraciones pendientes

# Frontend — desde frontend/
npm run build
npm test
npm audit --audit-level=high
```

---

## Convenciones de código (backend)

**Estilo:** flake8 con `max-line-length = 120`. isort con `profile = black`.

**Imports:** ordenados con isort. En caso de duda: `isort archivo.py` para ordenar automáticamente.

**Nombres:**
- Views: `NombreDeRecursoView` (ej: `ProfileUpdateView`, `ThreadListCreateView`)
- Tests: `NombreDeRecursoTest` con métodos `test_descripcion_del_comportamiento`
- Tasks Celery: snake_case, sufijo `_task` si son periódicas (ej: `promote_trust_levels_task`)

**Migraciones:** no editar migraciones existentes. Si hay un error en una migración no
aplicada en producción, crear una nueva migración que corrija el estado.

**Logging:** usar `logger = logging.getLogger(__name__)` en cada módulo.
Usar `logger.info`, `logger.warning`, `logger.exception` (no `print`).

---

## Cómo agregar una nueva app Django

1. `python manage.py startapp nombre_app`
2. Agregar `'nombre_app'` a `INSTALLED_APPS` en `settings.py`.
3. Crear `nombre_app/urls.py` y agregar el include en `exogram/urls.py`.
4. Crear `nombre_app/tests.py` con al menos un test básico.
5. Crear la migración inicial: `python manage.py makemigrations nombre_app`.
6. Documentar en `docs/backend/nombre_app.md`.

---

## Cómo agregar una migración

```bash
# Después de modificar un modelo
docker compose exec backend python manage.py makemigrations <app>

# Verificar que la migración es la esperada
docker compose exec backend python manage.py sqlmigrate <app> <numero_migracion>

# Aplicar
docker compose exec backend python manage.py migrate
```

En CI, `python manage.py makemigrations --check --dry-run` falla si hay migraciones
pendientes sin generar. Esto garantiza que los modelos y las migraciones siempre están sincronizados.

---

## Cómo agregar una variable de entorno

1. Agregar la lectura en `settings.py` con `config('NOMBRE_VAR', default=valor_seguro)`.
2. Documentar en [`docs/operations/environment-variables.md`](./operations/environment-variables.md).
3. Agregar a la lista de secrets de GitHub si es necesaria en producción.
4. Agregar al `deploy.yml` en el paso "Render backend env" o "Render root env".

---

## Cómo agregar una ruta al frontend

1. Definir el path en `src/router/localizedRoutes.js` (con versión es y en).
2. Agregar la ruta en `src/router/index.js` con `localizedRoute(...)`.
3. Crear la vista en `src/views/NombreVista.vue`.
4. Documentar en [`docs/frontend/views.md`](./frontend/views.md).

---

## Cómo agregar un ADR

Cuando se toma una decisión de arquitectura significativa:

1. Crear `docs/adr/NNNN-titulo-kebab-case.md` con el siguiente número secuencial.
2. Seguir el formato definido en [`docs/adr/README.md`](./adr/README.md).
3. Agregar la entrada al índice en ese mismo README.

Las decisiones que merecen un ADR: cambios de tecnología, nuevas integraciones externas,
cambios en el modelo de seguridad, decisiones de diseño con trade-offs no obvios.

---

## Formato de commits

Sin convención estricta, pero mensajes descriptivos en español o inglés:

```
fix: corregir validación de token expirado en ValidateInvitationView
feat: agregar exportación en formato Markdown
chore: actualizar Django a 5.2.12
docs: documentar flujo de password reset
```

Evitar mensajes tipo `fix stuff`, `WIP`, `changes`.
