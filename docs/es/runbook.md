# Exogram — Runbook Operacional

Procedimientos para operar, monitorear y recuperar Exogram en producción.

---

## Índice

1. [Stack de producción](#1-stack-de-producción)
2. [Primeros pasos: deploy inicial](#2-primeros-pasos-deploy-inicial)
3. [Gestión de secretos](#3-gestión-de-secretos)
4. [Operaciones de rutina](#4-operaciones-de-rutina)
5. [Backups y restauración](#5-backups-y-restauración)
6. [Monitoreo y alertas](#6-monitoreo-y-alertas)
7. [Respuesta a incidentes](#7-respuesta-a-incidentes)
8. [Tareas administrativas](#8-tareas-administrativas)
9. [Rotación de secretos](#9-rotación-de-secretos)
10. [Cumplimiento / GDPR](#10-cumplimiento--gdpr)

---

## 1. Stack de producción

| Componente      | Imagen / Versión            | Puerto expuesto |
|-----------------|-----------------------------|-----------------|
| Django + Gunicorn | Python 3.12-slim           | 8000 (interno)  |
| Celery worker   | mismo Dockerfile            | —               |
| Celery beat     | mismo Dockerfile            | —               |
| PostgreSQL 16   | pgvector/pgvector:pg16      | 5432 (interno)  |
| Redis 7         | redis:7-alpine              | 6379 (interno)  |
| Caddy           | caddy:2-alpine              | 80, 443         |
| Flower          | mher/flower                 | 5555 (localhost)|

```
Internet → Caddy (TLS) → Django API (:8000)
                       → /static/, /media/ (servidos por Caddy directamente)
Celery beat → Redis → Celery worker → PostgreSQL
```

---

## 2. Primeros pasos: deploy inicial

### 2.1 Clonar y configurar entorno

```bash
git clone git@github.com:<org>/exogram.git
cd exogram

# Copiar plantilla de variables de entorno
cp backend/.env.example backend/.env

# Editar con los valores reales de producción (ver sección 3)
$EDITOR backend/.env
```

### 2.2 Variables obligatorias en `backend/.env`

| Variable              | Descripción                                              | Cómo generar                              |
|-----------------------|----------------------------------------------------------|-------------------------------------------|
| `SECRET_KEY`          | Clave secreta de Django. Mínimo 50 chars, aleatoria.     | `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `DATABASE_URL`        | Cadena de conexión PostgreSQL.                           | `postgres://user:pass@host:5432/dbname`   |
| `REDIS_URL`           | URL de Redis.                                            | `redis://redis:6379/0`                    |
| `SENTRY_DSN`          | DSN de Sentry para error tracking.                       | Dashboard de Sentry → Settings → Client Keys |
| `FRONTEND_BASE_URL`   | URL pública del frontend (para links en emails).         | `https://exogram.app`             |
| `FORCE_HTTPS`         | Activar HSTS y cookies Secure.                           | `True`                                    |
| `ALLOWED_HOSTS`       | Dominios permitidos separados por comas.                 | `exogram.app,www.exogram.app` |
| `CORS_ALLOWED_ORIGINS`| Orígenes CORS permitidos.                                | `https://exogram.app`             |
| `CSRF_TRUSTED_ORIGINS`| Idem para CSRF.                                          | `https://exogram.app`             |
| `DEFAULT_FROM_EMAIL`  | Remitente de emails transaccionales.                     | `Exogram <no-reply@exogram.app>`  |
| `EMAIL_HOST`          | Servidor SMTP.                                           | Postal, SendGrid, SES, etc.               |
| `EMAIL_PORT`          | Puerto SMTP (587 para STARTTLS).                         | `587`                                     |
| `EMAIL_HOST_USER`     | Usuario SMTP.                                            | —                                         |
| `EMAIL_HOST_PASSWORD` | Contraseña SMTP.                                         | —                                         |

### 2.3 Primer arranque

```bash
# Levantar todos los servicios
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Verificar que todos los contenedores estén healthy
docker compose ps

# Crear superusuario inicial (genesis user)
docker compose exec backend python manage.py createsuperuser

# Verificar health endpoint
curl https://exogram.app/api/health/
# Respuesta esperada: {"status": "ok", "db": "ok", "redis": "ok"}
```

### 2.4 Build del frontend

```bash
cd frontend
npm ci
npm run build
# El directorio frontend/dist es servido por Caddy en producción
```

---

## 3. Gestión de secretos

### 3.1 Filosofía

- Secretos únicamente en `backend/.env` (excluido de git por `.gitignore`).
- Nunca en código fuente, variables de entorno del shell del host ni logs.
- Acceso al archivo `.env` restringido al usuario que ejecuta Docker.

### 3.2 Generar SECRET_KEY nueva

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

### 3.3 Credenciales de base de datos

```bash
# Generar contraseña fuerte
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Actualizar en .env:
# DATABASE_URL=postgres://exogram:<nueva_pass>@db:5432/exogram

# Cambiar en PostgreSQL:
docker compose exec db psql -U postgres -c "ALTER USER exogram PASSWORD '<nueva_pass>';"
```

### 3.4 Ver secretos actuales (solo en emergencia)

```bash
# Solo el operador autorizado con acceso SSH al servidor
cat backend/.env
```

---

## 4. Operaciones de rutina

### 4.1 Deploy de nueva versión

```bash
git pull origin main

# Rebuild y restart
docker compose -f docker-compose.yml -f docker-compose.prod.yml build backend
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --no-deps backend celery celery-beat

# Verificar logs
docker compose logs -f backend --tail=50
```

### 4.2 Aplicar migraciones

```bash
docker compose exec backend python manage.py migrate --noinput

# Verificar estado
docker compose exec backend python manage.py showmigrations
```

### 4.3 Reiniciar un servicio

```bash
docker compose restart backend      # API
docker compose restart celery       # Worker de embeddings
docker compose restart celery-beat  # Scheduler
docker compose restart redis        # Cache/broker
```

### 4.4 Ver logs en tiempo real

```bash
docker compose logs -f backend         # Django + Gunicorn
docker compose logs -f celery          # Tareas Celery
docker compose logs -f celery-beat     # Scheduling
docker compose logs -f caddy           # Proxy / TLS
```

### 4.5 Acceder a la shell de Django

```bash
docker compose exec backend python manage.py shell
```

---

## 5. Backups y restauración

### 5.1 Backup de PostgreSQL

```bash
# Backup completo
docker compose exec db pg_dump -U exogram exogram | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz

# Backup solo esquema (sin datos)
docker compose exec db pg_dump -U exogram --schema-only exogram > schema.sql
```

**Frecuencia recomendada:** diario automático vía cron o servicio de cloud (RDS automated backups, etc.).

```bash
# Ejemplo de cron en el host (diario a las 03:00)
0 3 * * * docker compose -f /opt/exogram/docker-compose.yml exec -T db pg_dump -U exogram exogram | gzip > /backups/exogram_$(date +\%Y\%m\%d).sql.gz
```

### 5.2 Restauración de PostgreSQL

```bash
# Detener la app (evitar escrituras durante restore)
docker compose stop backend celery celery-beat

# Restaurar
gunzip -c backup_20260315_030000.sql.gz | docker compose exec -T db psql -U exogram exogram

# Reiniciar
docker compose start backend celery celery-beat
```

### 5.3 Backup de media (avatares)

```bash
# Los avatares están en el volumen Docker `media_data`
docker run --rm -v exogram_media_data:/media -v $(pwd)/backups:/backup \
  alpine tar czf /backup/media_$(date +%Y%m%d).tar.gz /media
```

### 5.4 Backup del modelo ONNX (models_cache)

El modelo se descarga automáticamente desde HuggingFace en el primer arranque. No requiere backup, pero sí asegurar que el volumen `models_cache` persista entre reinicios (ya configurado en `docker-compose.prod.yml`).

---

## 6. Monitoreo y alertas

### 6.1 Health check

```bash
curl https://exogram.app/api/health/
# {"status": "ok", "db": "ok", "redis": "ok"}  → HTTP 200
# {"status": "error", "db": "error", ...}       → HTTP 503
```

Configurar un monitor externo (UptimeRobot, Pingdom, Better Uptime) apuntando a este endpoint.

### 6.2 Sentry

- Abrir [sentry.io](https://sentry.io) → proyecto Exogram.
- Configurar alertas para:
  - Error rate > 1% en una ventana de 5 minutos.
  - Nuevos issues con severidad HIGH/CRITICAL.
  - P95 de latencia > 2s en endpoints de API.

```python
# Ya configurado en settings.py con:
# traces_sample_rate=0.1  → muestra de 10% de transacciones para performance
```

### 6.3 Beat heartbeat

Verificar que el heartbeat de Celery Beat esté activo:

```bash
docker compose exec redis redis-cli GET celerybeat:heartbeat
# Debe retornar un timestamp Unix reciente (< 120 s)
```

Si el valor está vacío o viejo, el beat o el worker no están funcionando:

```bash
# Ver estado
docker compose ps celery-beat celery

# Reiniciar si es necesario
docker compose restart celery-beat celery
```

### 6.4 Cola de embeddings

Verificar que no se acumulen highlights sin embedding:

```bash
docker compose exec backend python manage.py shell -c "
from books.models import Highlight
pending = Highlight.objects.filter(embedding__isnull=True).count()
total = Highlight.objects.count()
print(f'Sin embedding: {pending}/{total}')
"
```

### 6.5 Flower (monitoreo de Celery)

> ⚠️ **Flower no tiene autenticación.** Está bound a `127.0.0.1:5555` en producción
> (configurado en `docker-compose.prod.yml`), por lo que no es accesible desde internet.
> Acceder únicamente mediante túnel SSH.

```bash
# En la máquina local
ssh -L 5555:localhost:5555 user@servidor

# Abrir en el navegador
open http://localhost:5555
```

---

## 7. Respuesta a incidentes

### 7.1 API devuelve 503 / health check falla

```bash
# 1. Verificar estado de contenedores
docker compose ps

# 2. Ver logs del backend
docker compose logs backend --tail=100

# 3. Si la DB está caída
docker compose restart db
docker compose exec backend python manage.py migrate --noinput  # aplica migraciones pendientes si hay

# 4. Si Redis está caído
docker compose restart redis
docker compose restart celery  # workers reconectan automáticamente
```

### 7.2 Celery worker no procesa tareas

```bash
# 1. Ver heartbeat
docker compose exec redis redis-cli GET celerybeat:heartbeat

# 2. Verificar cola de tareas
docker compose exec redis redis-cli LLEN celery

# 3. Ver logs del worker
docker compose logs celery --tail=100

# 4. Reiniciar
docker compose restart celery

# 5. Si el modelo ONNX no pudo descargarse (EmbeddingModelUnavailable en logs)
# El worker loguea el error y salta la tarea sin retries.
# Reiniciar el worker con conexión a internet disponible.
```

### 7.3 Modelo ONNX no disponible

```bash
# Verificar que el volumen existe y tiene el modelo
docker volume ls | grep models_cache
docker run --rm -v exogram_models_cache:/models alpine ls -lh /models/

# Si el archivo está corrupto o incompleto, eliminarlo para forzar re-descarga
docker run --rm -v exogram_models_cache:/models alpine rm -f /models/paraphrase-multilingual-MiniLM-L12-v2.onnx
docker compose restart celery
```

### 7.4 Fallo de envío de emails

```bash
# Verificar configuración SMTP
docker compose exec backend python manage.py shell -c "
from django.core.mail import send_mail
send_mail('Test', 'Test email', 'no-reply@exogram.app', ['admin@exogram.app'])
print('OK')
"

# Si falla, verificar credenciales en .env:
# EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD
```

### 7.5 Base de datos llena / lenta

```bash
# Verificar tamaño
docker compose exec db psql -U exogram -c "
SELECT pg_size_pretty(pg_database_size('exogram')) AS db_size;
SELECT relname, pg_size_pretty(pg_total_relation_size(relid)) AS size
FROM pg_stat_user_tables ORDER BY pg_total_relation_size(relid) DESC LIMIT 10;
"

# Vacuum manual si hay mucha fragmentación
docker compose exec db psql -U exogram -c "VACUUM ANALYZE;"
```

---

## 8. Tareas administrativas

### 8.1 Crear usuario genesis (superuser)

```bash
docker compose exec backend python manage.py createsuperuser
```

### 8.2 Generar embeddings faltantes manualmente

```bash
docker compose exec backend python manage.py shell -c "
from books.models import Highlight
from books.tasks import batch_generate_embeddings

pending = list(Highlight.objects.filter(embedding__isnull=True).values_list('id', flat=True))
print(f'Encolando {len(pending)} highlights...')
if pending:
    batch_generate_embeddings.delay(pending)
    print('Tarea encolada.')
"
```

### 8.3 Resetear contraseña de un usuario (admin)

```bash
docker compose exec backend python manage.py changepassword <username>
```

### 8.4 Exportar datos de un usuario (GDPR)

```bash
docker compose exec backend python manage.py shell -c "
from django.contrib.auth.models import User
user = User.objects.get(username='<nickname>')
# Usar el endpoint /api/me/export/ o acceder vía admin
print(user.profile.verified_email)
"
```

### 8.5 Eliminar cuenta de usuario (GDPR)

```bash
# Usar el endpoint autenticado DELETE /api/me/delete/
# O desde la shell:
docker compose exec backend python manage.py shell -c "
from django.contrib.auth.models import User
user = User.objects.get(username='<nickname>')
user.delete()  # Cascade elimina Profile, Highlights, etc.
print('Eliminado.')
"
```

### 8.6 Ver lista de espera

```bash
docker compose exec backend python manage.py shell -c "
from accounts.models import Waitlist
entries = Waitlist.objects.filter(is_activated=False).order_by('requested_at')
for e in entries:
    print(f'{e.requested_at:%Y-%m-%d} | {e.email} | {e.message[:50]}')
print(f'Total: {entries.count()}')
"
```

### 8.7 Actualizar certificado TLS (Caddy)

Caddy gestiona el certificado automáticamente via ACME (Let's Encrypt). No requiere intervención manual. Si hay problemas:

```bash
docker compose logs caddy | grep -i cert
docker compose restart caddy
```

---

## 9. Rotación de secretos

### 9.1 Rotar SECRET_KEY

> ⚠️ Cambiar `SECRET_KEY` invalida todas las sesiones activas (JWT cookies) y todos los tokens HMAC de invitación y reset de contraseña en la base de datos.

```bash
# 1. Generar nueva clave
NEW_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(64))")
echo "Nueva SECRET_KEY: $NEW_KEY"

# 2. Invalidad tokens activos antes de cambiar la clave
docker compose exec backend python manage.py shell -c "
from accounts.models import InvitationToken, PasswordResetToken
# Tokens HMAC calculados con la clave vieja quedarán inválidos.
# Limpiarlos antes del cambio para evitar confusión.
InvitationToken.objects.all().delete()
PasswordResetToken.objects.filter(used_at__isnull=True).delete()
print('Tokens limpiados.')
"

# 3. Actualizar .env
sed -i "s/^SECRET_KEY=.*/SECRET_KEY=$NEW_KEY/" backend/.env

# 4. Reiniciar servicios
docker compose restart backend celery celery-beat
```

### 9.2 Rotar contraseña de la base de datos

```bash
NEW_PASS=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

# Cambiar en PostgreSQL
docker compose exec db psql -U postgres -c "ALTER USER exogram PASSWORD '$NEW_PASS';"

# Actualizar .env
sed -i "s|DATABASE_URL=postgres://exogram:.*@|DATABASE_URL=postgres://exogram:$NEW_PASS@|" backend/.env

# Reiniciar
docker compose restart backend celery celery-beat
```

### 9.3 Rotar credenciales SMTP

```bash
# 1. Actualizar EMAIL_HOST_PASSWORD en .env
# 2. Reiniciar solo el backend (Celery también usa el mailer)
docker compose restart backend celery
```

---

## 10. Cumplimiento / GDPR

### 10.1 Datos que almacena Exogram por usuario

| Dato                | Dónde               | Visibilidad |
|---------------------|---------------------|-------------|
| Email verificado    | `Profile.verified_email` | Solo admin |
| Nickname            | `Profile.nickname`  | Pública     |
| Bio                 | `Profile.bio`       | Pública     |
| Avatar              | `media/avatars/`    | Pública     |
| Highlights          | `Highlight`         | Según visibilidad |
| Notas               | `Note`              | Privada     |
| Árbol de invitaciones | `Profile.invited_by` | Solo admin |

### 10.2 Eliminar datos de un usuario (derecho al olvido)

Ver sección 8.5. El `User.delete()` elimina en cascade todos los objetos relacionados gracias a `on_delete=CASCADE` en los modelos.

Los avatares en `media/avatars/` deben eliminarse manualmente:

```bash
docker compose exec backend python manage.py shell -c "
from django.contrib.auth.models import User
user = User.objects.get(username='<nickname>')
if user.profile.avatar:
    user.profile.avatar.delete(save=False)
user.delete()
print('Usuario y avatar eliminados.')
"
```

### 10.3 Exportar datos de un usuario (portabilidad)

```bash
curl -X GET https://exogram.app/api/me/export/ \
  -H "Cookie: exo_access=<token>" \
  -H "X-CSRFToken: <csrf>"
```

El endpoint devuelve JSON con todos los highlights, notas y datos del perfil del usuario autenticado.

---

*Última actualización: 2026-03-18*
