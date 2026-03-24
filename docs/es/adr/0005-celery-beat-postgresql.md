# 0005 — django-celery-beat con DatabaseScheduler


## Contexto

Exogram necesita tareas periódicas: promoción diaria de trust levels, heartbeat del beat,
y potencialmente más en el futuro. Se necesita un scheduler que sea robusto ante
reinicios de contenedores.

## Decisión

Usar `django-celery-beat` con `DatabaseScheduler`. El schedule se persiste en PostgreSQL.
El contenedor `celery-beat` tiene exactamente una réplica (nunca escalar).

El heartbeat (`beat_heartbeat`) escribe un timestamp en Redis cada 60 segundos.
El healthcheck del contenedor beat valida que ese timestamp sea reciente, verificando
que tanto el beat como el worker estén vivos simultáneamente.

## Alternativas consideradas

**Cron del sistema operativo:** simple, pero el estado de ejecución no es visible
desde la aplicación, requiere acceso SSH para modificar schedules, y no sobrevive
a cambios de contenedor de forma limpia.

**Celery beat con archivo de schedule (`PersistentScheduler`):** el archivo se pierde
al recrear el contenedor o al hacer deploy. Requiere montar un volumen adicional.

**APScheduler en proceso:** corre dentro del proceso Django, no escala bien y
mezcla responsabilidades.

## Consecuencias

- El schedule es visible y editable desde Django Admin → Periodic Tasks.
- Los schedules en `CELERY_BEAT_SCHEDULE` actúan como seed inicial: se crean en la primera ejecución y luego la base de datos es la fuente de verdad. Cambios posteriores deben hacerse desde el admin, no en el código.
- El contenedor beat **nunca debe tener más de una réplica** activa: dos instancias publicarían cada tarea el doble de veces.
- La validación de heartbeat en Redis detecta si el worker no está procesando las tareas que el beat publica (ambos deben estar vivos para que el heartbeat se complete).
