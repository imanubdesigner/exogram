# Runbook operacional

Referencia rápida de comandos para situaciones frecuentes en producción.
Para procedimientos completos (gestión de secretos, GDPR, rotación de credenciales),
ver el [runbook completo](../runbook.md).

Todos los comandos asumen que estás en el servidor, en el directorio del proyecto.

---

## Niveles de severidad

| Nivel | Descripción | Tiempo de respuesta |
|-------|-------------|---------------------|
| **P0** | Servicio completamente inaccesible o pérdida de datos en curso | Inmediato |
| **P1** | Funcionalidad crítica degradada (login, invitaciones, emails) | < 30 min |
| **P2** | Funcionalidad no crítica degradada (embeddings, discovery) | < 4 horas |

---

## Playbooks de incidentes

### P0 — Base de datos caída

**Síntomas:** `{"status":"error","db":"error"}` en `/api/health/`, errores 500 generalizados.

```bash
# 1. Verificar estado del contenedor
dc ps db

# 2. Ver logs
dc logs db --tail=50

# 3. Si el contenedor está detenido, reiniciar
dc start db

# 4. Si falla al iniciar (datos corruptos), restaurar desde backup
# Ver sección "Restore desde backup" más abajo

# 5. Verificar conectividad desde backend
dc exec backend python manage.py dbshell -- --command="SELECT 1;"

# 6. Confirmar recovery
curl -s http://127.0.0.1:8000/api/health/ | python3 -m json.tool
```

**Escalado:** Si el volumen `postgres_data` está corrupto → restaurar último backup.

---

### P0 — Redis caído

**Síntomas:** Workers Celery desconectados, sessions JWT sin poder refrescarse, errores en throttling.

```bash
# 1. Verificar estado
dc ps redis
dc logs redis --tail=30

# 2. Reiniciar (Redis es stateless en este stack; los datos en memoria se pierden)
dc restart redis

# 3. Verificar que responde
dc exec redis redis-cli ping  # debe responder PONG

# 4. Reiniciar workers para reconectar
dc restart celery celery-beat

# 5. Verificar health
curl -s http://127.0.0.1:8000/api/health/ | python3 -m json.tool
```

**Impacto esperado:** Los rate limits se resetean (son en-memoria). Los JWT access tokens siguen siendo válidos hasta que expiran; el refresh necesita Redis para funcionar.

---

### P1 — Cola Celery atascada

**Síntomas:** Tareas en estado `PENDING` por más de 10 minutos, embeddings no se generan, emails no se envían.

```bash
# 1. Verificar estado del worker
dc exec celery celery -A exogram inspect ping
dc exec celery celery -A exogram inspect active
dc exec celery celery -A exogram inspect stats

# 2. Ver cola pendiente
dc exec celery celery -A exogram inspect reserved

# 3. Verificar heartbeat del beat (si es 0 o muy viejo, el beat no funciona)
dc exec redis redis-cli get celerybeat:heartbeat

# 4. Reiniciar worker (las tareas pendientes vuelven a la cola)
dc restart celery

# 5. Si la cola tiene tareas corruptas que bloquean el worker, purgar
dc exec celery celery -A exogram purge
# ⚠️ Purgar elimina todas las tareas pendientes. Evaluar impacto antes de ejecutar.
```

---

### P1 — Emails no se entregan

**Síntomas:** Invitaciones y resets de contraseña no llegan, logs muestran errores SMTP.

```bash
# 1. Ver logs del backend para errores SMTP
dc logs backend --tail=100 | grep -i "smtp\|email\|postal\|SMTPException"

# 2. Verificar que Postal está levantado (si usás el profile mail)
dc --profile mail ps postal
dc --profile mail logs postal --tail=30

# 3. Test manual desde Django
dc exec backend python manage.py shell -c "
from django.core.mail import send_mail
send_mail('Test P1', 'Diagnóstico', 'no-reply@exogram.app', ['tu@email.com'])
print('Enviado')
"

# 4. Si Postal está caído, reiniciar
dc --profile mail restart postal
```

---

## Verificación post-deploy

Ejecutar inmediatamente después de cada deploy:

```bash
# 1. Todos los contenedores en estado Up
dc ps

# 2. Health check del backend
curl -s http://127.0.0.1:8000/api/health/ | python3 -m json.tool
# Esperado: {"status":"ok","db":"ok","redis":"ok"}

# 3. Sin errores recientes en logs
dc logs backend --tail=20 | grep -E "ERROR|CRITICAL" || echo "Sin errores"

# 4. Worker Celery responde
dc exec celery celery -A exogram inspect ping

# 5. Migraciones aplicadas
dc exec backend python manage.py showmigrations | grep '\[ \]' || echo "Sin migraciones pendientes"
```

---

## Métricas mínimas observables

| Métrica | Fuente | Umbral de alerta |
|---------|--------|-----------------|
| HTTP 5xx rate | `dc logs backend` | > 1% de requests en 5 min |
| Latencia p95 backend | `dc logs backend` | > 2 s sostenido |
| Cola Celery pendiente | Flower / `inspect reserved` | > 100 tareas por > 5 min |
| Heartbeat Celery Beat | Redis `celerybeat:heartbeat` | Más de 120 s sin actualizar |
| Espacio en disco | `df -h /var/lib/docker` | > 80% |
| Memoria contenedores | `docker stats --no-stream` | backend > 1.8 GB, celery > 2.5 GB |

---

```bash
ssh usuario@servidor
cd /srv/exogram
```

El alias del compose en producción es:

```bash
alias dc='docker compose -f docker-compose.yml -f docker-compose.prod.yml'
```

---

## Ver logs

```bash
# Backend (Django/Gunicorn)
dc logs backend -f

# Worker Celery
dc logs celery -f

# Beat (tareas periódicas)
dc logs celery-beat -f

# Todos a la vez
dc logs -f

# Últimas 100 líneas de un servicio
dc logs backend --tail=100
```

---

## Restart de servicios

```bash
# Restart de un servicio sin reconstruir imagen
dc restart backend
dc restart celery
dc restart celery-beat

# Restart de todos
dc restart

# Restart forzado (detiene y vuelve a levantar)
dc stop backend && dc up -d backend
```

---

## Estado de la aplicación

```bash
# Health check (espera {"status":"ok","db":"ok","redis":"ok"})
curl -s http://127.0.0.1:8000/api/health/ | python3 -m json.tool

# Estado de contenedores
dc ps

# Uso de recursos
docker stats --no-stream

# Espacio en disco (volúmenes Docker)
docker system df
```

---

## Tareas Celery

### Ver estado del worker

```bash
# Desde Flower (UI web, solo accesible en localhost)
# ⚠️ Flower no tiene autenticación. Está bound a 127.0.0.1:5555 en producción,
# por lo que no es accesible desde internet. Acceder solo vía túnel SSH:
# Abrir un tunel SSH: ssh -L 5555:127.0.0.1:5555 usuario@servidor
# Luego abrir: http://localhost:5555

# Por línea de comandos
dc exec celery celery -A exogram inspect active
dc exec celery celery -A exogram inspect stats
```

### Verificar el heartbeat del beat

El beat escribe un timestamp en Redis cada 60 segundos como señal de vida.

```bash
dc exec redis redis-cli get celerybeat:heartbeat
# Devuelve el timestamp Unix de la última ejecución
# Si está vacío o muy desactualizado, el beat no está funcionando
```

### Lanzar una tarea manualmente

```bash
dc exec backend python manage.py shell -c "
from books.tasks import batch_generate_embeddings
batch_generate_embeddings.delay([1, 2, 3])
print('Tarea enviada')
"
```

### Purgar la cola de tareas pendientes

```bash
dc exec celery celery -A exogram purge
```

---

## Base de datos

### Conectarse al shell de PostgreSQL

```bash
dc exec db psql -U exogram -d exogram
```

### Backup manual

```bash
dc exec db pg_dump -U exogram exogram | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

### Restore desde backup

```bash
gunzip < backup_20260318_120000.sql.gz | dc exec -T db psql -U exogram -d exogram
```

### Correr migraciones manualmente

Las migraciones corren automáticamente en cada deploy vía `start-web.sh`.
Para correrlas a mano:

```bash
dc exec backend python manage.py migrate --noinput
```

### Ver migraciones pendientes

```bash
dc exec backend python manage.py showmigrations | grep '\[ \]'
```

---

## Django Admin

### Crear superusuario

```bash
dc exec backend python manage.py createsuperuser
```

### Cambiar contraseña de un usuario

```bash
dc exec backend python manage.py changepassword <username>
```

### Shell de Django

```bash
dc exec backend python manage.py shell
```

---

## JWT — Token Blacklist

Los refresh tokens rotados se almacenan en la blacklist de simplejwt en PostgreSQL.
Con el tiempo, la tabla puede crecer. Django simplejwt incluye un management command
para limpiar tokens expirados:

```bash
dc exec backend python manage.py flushexpiredtokens
```

Se recomienda schedulear esto periódicamente (se puede agregar a `CELERY_BEAT_SCHEDULE`).

---

## SECRET_KEY — Rotación

Rotar la `SECRET_KEY` invalida todas las sesiones activas, cookies de CSRF y
tokens de invitación/reset pendientes. Los usuarios deberán loguearse nuevamente.

1. Generar nueva clave: `python3 -c "import secrets; print(secrets.token_urlsafe(50))"`
2. Actualizar el secret `SECRET_KEY` en GitHub
3. Actualizar `backend/.env` en el servidor
4. `dc restart backend celery celery-beat`

---

## Certificados TLS

Caddy obtiene y renueva certificados Let's Encrypt automáticamente.
Los datos de certificados se persisten en el volumen `caddy_data`.

Para ver el estado del certificado:

```bash
dc exec caddy caddy version
# Los logs de Caddy muestran renovaciones automáticas
dc logs caddy | grep -i "certificate\|tls\|acme"
```

Si el certificado no renueva (edge case), reiniciar Caddy es suficiente en la
mayoría de casos: `dc restart caddy`.

---

## Limpieza de espacio en disco

```bash
# Imágenes Docker sin usar
docker image prune -f

# Contenedores detenidos, redes y cache de build sin usar
docker system prune -f

# Con volúmenes (CUIDADO: elimina datos si no están en uso activo)
docker system prune --volumes -f
```

---

## Diagnóstico de errores frecuentes

### El backend responde 500

```bash
dc logs backend --tail=100 | grep ERROR
dc exec backend python manage.py check
```

### Celery no procesa tareas

```bash
# Verificar conexión con Redis
dc exec celery celery -A exogram inspect ping

# Verificar que Redis esté arriba
dc exec redis redis-cli ping   # debe responder PONG

# Reiniciar worker
dc restart celery
```

### Emails no se envían

```bash
# Ver logs del backend para errores SMTP
dc logs backend | grep -i "email\|smtp\|postal"

# Verificar que Postal está levantado (si usás el profile mail)
dc --profile mail ps postal

# Test manual desde Django
dc exec backend python manage.py shell -c "
from django.core.mail import send_mail
send_mail('Test', 'Cuerpo', 'from@exogram.app', ['to@example.com'])
print('Enviado')
"
```
