# Deployment

Cómo funciona el flujo de deploy automatizado y cómo ejecutarlo.

---

## Arquitectura de producción

```
Internet
   │
   ▼
Caddy (80/443) ── TLS automático vía Let's Encrypt
   │
   ├── /api/*  ──────► backend:8000  (Gunicorn, 4 workers × 2 threads)
   ├── /admin* ──────► backend:8000
   ├── /static/* ────► /srv/static   (archivos servidos directamente por Caddy)
   ├── /media/* ─────► /srv/media
   └── /* ───────────► /srv/frontend/dist  (SPA Vue, con fallback a index.html)

backend ──► PostgreSQL 16 + pgvector
backend ──► Redis 7
Celery worker ──► Redis (broker) ──► PostgreSQL (resultados)
Celery beat ──► Redis + PostgreSQL (schedule persistido con django-celery-beat)
Postal ──► MariaDB + Redis  (SMTP self-hosted, profile "mail")
```

Los puertos de PostgreSQL y Redis están restringidos a `127.0.0.1` en producción
(definido en `docker-compose.prod.yml`). Solo son accesibles desde la red interna Docker
y desde el host mismo.

---

## Flujo CI/CD

El deploy es completamente automatizado. Cada push a `main` dispara este flujo:

```
push a main
    │
    ▼
CI (.github/workflows/ci.yml)
    ├── backend-lint  ─── (paralelo) → flake8 + isort + bandit + pip-audit
    ├── backend-test  ─── (después de lint) → migrate + tests + coverage ≥ 70%
    ├── frontend      ─── (paralelo) → npm audit + eslint + build + vitest
    └── ci            ─── (status gate) → veredicto pass/fail
    │
    ▼ (si todos pasan)
Deploy (.github/workflows/deploy.yml)
    ├── build frontend (con VITE_API_URL inyectado)
    ├── rsync del repositorio al servidor
    ├── sube backend/.env y .env al servidor
    ├── docker compose build + up -d
    └── curl /api/health/ → verifica que el deploy respondió
```

El deploy solo corre si CI pasó **y** el branch es `main`.

---

## Prerequisitos en el servidor

- Docker Engine 24+ y Docker Compose v2
- Usuario con acceso SSH y permisos para correr `docker compose`
- Puerto 80 y 443 abiertos en el firewall
- Puerto 25 y 587 abiertos si usás Postal para email

---

## Configurar el deploy por primera vez

### 1. Generar un par de claves SSH para el deploy

En tu máquina local:

```bash
ssh-keygen -t ed25519 -C "exogram-deploy" -f ~/.ssh/exogram_deploy
```

Copiar la clave pública al servidor:

```bash
ssh-copy-id -i ~/.ssh/exogram_deploy.pub usuario@tu-servidor.com
```

### 2. Cargar los secrets en GitHub

Ir a **Settings → Secrets and variables → Actions** en el repositorio y crear
cada secret de la [lista completa](./environment-variables.md#secrets-requeridos-en-github-para-el-deploy-automático).

Los cuatro secrets de infraestructura del deploy:

| Secret | Valor |
|---|---|
| `DEPLOY_SSH_KEY` | Contenido de `~/.ssh/exogram_deploy` (clave privada) |
| `DEPLOY_HOST` | IP o hostname del servidor |
| `DEPLOY_USER` | Usuario SSH |
| `DEPLOY_PATH` | Path absoluto en el servidor, p.ej. `/srv/exogram` |

### 3. Configurar credenciales de base de datos

Antes de activar el deploy, asegurarse de que `POSTGRES_PASSWORD` esté definida
como un GitHub Secret (ver paso 2). El `docker-compose.yml` usa `${POSTGRES_PASSWORD:-dev_password}`:
**si el secret no existe, la DB arranca con `dev_password`, que es inseguro en producción.**

Para generar una contraseña fuerte:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Agregar el resultado como secret `POSTGRES_PASSWORD` en GitHub. También agregar
`POSTGRES_DB` (default: `exogram`) y `POSTGRES_USER` (default: `exogram`) si
se quieren personalizar.

> **Nota:** Si ya existe un volumen `postgres_data` con la contraseña anterior,
> cambiar `POSTGRES_PASSWORD` requiere también rotar la credencial dentro de
> PostgreSQL (ver sección Rotación de secretos en el Runbook).

### 3.b Configurar la URL del admin de Django

El valor de `ADMIN_URL` en los GitHub Secrets determina la ruta del admin de Django.
Cambiarla es una medida de oscuridad útil, pero **requiere sincronizar el Caddyfile**:

Si `ADMIN_URL=mi-panel-secreto/`, actualizar en `Caddyfile`:

```
handle /mi-panel-secreto* {
    reverse_proxy backend:8000
}
```

Sin esta actualización, Caddy no redirige el nuevo path al backend.

### 4. Habilitar el workflow de deploy

El archivo `deploy.yml.disabled` contiene el workflow listo. Renombrarlo para activarlo:

```bash
mv .github/workflows/deploy.yml.disabled .github/workflows/deploy.yml
git add .github/workflows/deploy.yml
git rm .github/workflows/deploy.yml.disabled
git commit -m "enable production deploy workflow"
git push
```

A partir de ese commit, cada push a `main` que pase el CI disparará el deploy.

### 5. Primera inicialización del servidor

El primer deploy crea los contenedores y corre las migraciones automáticamente.
Después de que termine, crear el superusuario:

```bash
ssh usuario@tu-servidor.com
cd /srv/exogram
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec backend python manage.py createsuperuser
```

Cargar los artículos fixtures si corresponde:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec backend python manage.py loaddata articles/fixtures/*.json
```

---

## Deploys subsiguientes

Con el workflow activo, cada `git push origin main` es un deploy si CI pasa.
No hay pasos manuales.

Para forzar un redeploy sin cambios de código:

```bash
git commit --allow-empty -m "chore: force redeploy"
git push
```

---

## Verificar el estado del deploy

```bash
# Health check de la aplicación
curl https://exogram.app/api/health/

# Respuesta esperada (200 OK):
# {"status": "ok", "db": "ok", "redis": "ok"}

# Logs del backend
ssh usuario@servidor 'cd /srv/exogram && docker compose logs backend --tail=50'

# Estado de todos los contenedores
ssh usuario@servidor 'cd /srv/exogram && docker compose ps'
```

---

## Rollback

El deploy hace `rsync` sobre el directorio del servidor. Para volver a la versión anterior:

```bash
ssh usuario@servidor
cd /srv/exogram

# Ver los últimos commits deployados (el deploy hace checkout del commit exacto)
git log --oneline -10

# Revertir al commit anterior en el servidor
git checkout <hash-anterior>
docker compose -f docker-compose.yml -f docker-compose.prod.yml build
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

Para un rollback limpio se recomienda hacer un `git revert` en la rama `main` y dejar
que el CI/CD haga el deploy, en lugar de intervenir manualmente en el servidor.

---

## Actualizaciones de dependencias

Después de modificar `backend/requirements.txt` o `frontend/package.json`:

1. El CI valida las nuevas dependencias con `pip-audit` y `npm audit`
2. El deploy rebuild automáticamente las imágenes Docker (`docker compose build`)
3. No hay que hacer nada manualmente

---

## Modelo ONNX en producción

El modelo ONNX para embeddings (~470 MB) se persiste en el volumen `models_cache`
(definido en `docker-compose.prod.yml`). Se descarga desde HuggingFace la primera
vez que el worker Celery lo necesita. No se incluye en la imagen Docker.

Si el volumen se pierde (p.ej. por `docker compose down -v`), el modelo se descarga
en el primer highlight que requiera embedding. Para precargarlo:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec celery \
  python manage.py download_onnx_model
```

---

## Release candidate y Go/No-Go

### Cómo crear un tag RC

```bash
git tag -a v1.0.0-rc1 -m "Release candidate 1"
git push origin v1.0.0-rc1
```

El tag dispara el workflow de deploy si está configurado con `on: push: tags`.

### Checklist preflight (antes del deploy)

- [ ] CI en verde en `main` (tests, lint, bandit, pip-audit, npm audit, build)
- [ ] Variables de entorno en GitHub Secrets actualizadas
- [ ] `ADMIN_URL` cambiado del valor por defecto y sincronizado con Caddyfile
- [ ] `SECRET_KEY` generado con `secrets.token_urlsafe(50)` (no el valor de ejemplo)
- [ ] `POSTGRES_PASSWORD` seguro y guardado como Secret
- [ ] Backup de DB vigente (si es upgrade de versión existente)
- [ ] CHANGELOG.md actualizado con los cambios de esta versión
- [ ] `SECURITY.md` revisado y con email de contacto válido

### Checklist postflight (después del deploy)

- [ ] `curl -s https://<dominio>/api/health/` devuelve `{"status":"ok","db":"ok","redis":"ok"}`
- [ ] Login funciona con un usuario de prueba
- [ ] Email de invitación llega correctamente
- [ ] Sin errores `ERROR` o `CRITICAL` en `dc logs backend --tail=50`
- [ ] Celery responde: `dc exec celery celery -A exogram inspect ping`
- [ ] HTTPS activo y certificado válido (Caddy emite automáticamente)
- [ ] Admin accesible en `https://<dominio>/<ADMIN_URL>`

### Criterio Go/No-Go

| Condición | Decisión |
|-----------|----------|
| Todos los checks postflight en verde | ✅ Go |
| Health check falla | 🔴 No-Go → rollback inmediato |
| Errores en logs o Celery no responde | 🔴 No-Go → investigar antes de continuar |
| Certificado TLS no emitido (> 5 min) | 🟡 Esperar 10 min, si persiste → rollback |

### Rollback

```bash
# Opción 1: revertir en git (preferida — deja trazabilidad)
git revert HEAD --no-edit
git push origin main

# Opción 2: rollback manual en el servidor (si el deploy rompió algo crítico)
ssh usuario@servidor
cd /srv/exogram
git checkout <commit-anterior>
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```
