# Desarrollo local

Guía para levantar el entorno completo en tu máquina.

---

## Prerequisitos

- Docker Engine 24+ y Docker Compose v2 (`docker compose`, no `docker-compose`)
- Git
- Python 3.12 (solo si querés correr tests sin Docker)

---

## 1. Clonar el repositorio

```bash
git clone git@github.com:<org>/exogram.git
cd exogram
```

---

## 2. Crear el archivo de variables del backend

```bash
cp backend/.env.example backend/.env   # si existe, o crear manualmente
```

Contenido mínimo para desarrollo:

```env
SECRET_KEY=dev-secret-key-replace-in-production-min-50-chars-long-abc123
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,testserver
POSTGRES_PASSWORD=dev_password
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
DEFAULT_FROM_EMAIL=dev@localhost
```

Con `EMAIL_BACKEND=console` todos los emails (invitaciones, resets) se imprimen en
los logs del contenedor backend en lugar de enviarse. Suficiente para desarrollo.

El resto de variables tienen defaults razonables en `settings.py` para entorno local.
Ver la [referencia completa de variables](./environment-variables.md).

---

## 3. Levantar los servicios

```bash
docker compose up --build
```

Esto arranca: **PostgreSQL** (con pgvector), **Redis**, **backend** (Django runserver),
**Celery worker**, **Celery beat** y **frontend** (Vite dev server).

Postal (SMTP) no levanta por defecto. Se activa con `--profile mail` solo si lo necesitás.

Accesos:

| Servicio | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000/api/ |
| Django Admin | http://localhost:8000/admin/ |
| Flower (Celery) | http://localhost:5555 |

---

## 4. Crear el superusuario

En una terminal separada, con los contenedores corriendo:

```bash
docker compose exec backend python manage.py createsuperuser
```

El comando pedirá username, email y contraseña.
Con ese usuario podés entrar al admin y crear la primera invitación manualmente.

---

## 5. Cargar fixtures de artículos (opcional)

Los artículos del proyecto (filosofía, manifiesto) tienen fixtures precargables:

```bash
docker compose exec backend python manage.py loaddata articles/fixtures/*.json
```

---

## 6. Descargar el modelo ONNX para embeddings

El worker de Celery genera embeddings de highlights usando un modelo ONNX local
(`paraphrase-multilingual-MiniLM-L12-v2`, ~470 MB). En la primera ejecución
se descarga automáticamente desde HuggingFace al directorio `models_cache/`.

Para precargarlo manualmente y evitar la descarga en el primer import:

```bash
docker compose exec celery python manage.py download_onnx_model
```

El directorio `models_cache/` está montado como volumen compartido entre el
backend y el worker de Celery, por lo que la descarga solo ocurre una vez.

---

## 7. Correr los tests

Los tests requieren PostgreSQL con la extensión `pgvector` activa.
El test runner custom (`PgVectorTestRunner`) la habilita automáticamente.

**Con Docker (recomendado):**

```bash
docker compose exec backend coverage run --source='.' manage.py test --verbosity=2
docker compose exec backend coverage report
```

**Sin Docker** (requiere PostgreSQL local con pgvector y las variables de entorno configuradas):

```bash
cd backend
pip install -r requirements.txt
DJANGO_SETTINGS_MODULE=exogram.settings_ci \
DATABASE_URL=postgres://exogram:test_password@localhost:5432/exogram_test \
coverage run --source='.' manage.py test --verbosity=2
```

La configuración `settings_ci` desactiva el rate limiting y usa `FastPBKDF2PasswordHasher`
para acelerar la creación de usuarios en tests (iterations=1).

---

## 8. Correr el linter y el análisis de seguridad

```bash
# Desde backend/
flake8 .
isort --check-only .
bandit -r . -x ./migrations,./smoke_tests -ll -ii -c .bandit
pip-audit -r requirements.txt
```

```bash
# Desde frontend/
npm run build
npm test
```

---

## Flujo típico de desarrollo

1. Hacer cambios en `backend/` → Django runserver los recarga automáticamente.
2. Hacer cambios en `frontend/src/` → Vite HMR los recarga en el browser.
3. Cambios en modelos → `docker compose exec backend python manage.py makemigrations <app>`.
4. Antes de commitear → correr flake8 e isort localmente para evitar fallo en CI.

---

## Reiniciar la base de datos

Para empezar desde cero (destruye todos los datos):

```bash
docker compose down -v
docker compose up --build
```

La flag `-v` elimina los volúmenes Docker incluyendo `postgres_data`.

---

## Problemas frecuentes

**`type "vector" does not exist` al correr tests**
El test runner `PgVectorTestRunner` habilita la extensión automáticamente, pero
requiere que el usuario de PostgreSQL tenga permisos de superusuario o `CREATE EXTENSION`.
En el entorno de desarrollo, el usuario `exogram` del compose ya tiene esos permisos.
En entornos manuales, correr: `psql -U postgres -c "CREATE EXTENSION vector;" exogram_test`

**El worker Celery no procesa tareas**
Verificar que Redis esté saludable: `docker compose ps redis`.
Verificar los logs del worker: `docker compose logs celery -f`.

**El frontend no conecta con la API**
El Vite dev server tiene configurado un proxy en `vite.config.js`:
`/api/*` → `http://backend:8000`. Dentro de Docker esto funciona por nombre de servicio.
Fuera de Docker, la API estará en `http://localhost:8000`.
