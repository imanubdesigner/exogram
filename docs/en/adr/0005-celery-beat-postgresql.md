# 0005 — django-celery-beat with DatabaseScheduler

## Context

Exogram needs periodic tasks: daily trust level promotion, beat heartbeat,
and potentially more in the future. A scheduler that is robust against
container restarts is required.

## Decision

Use `django-celery-beat` with `DatabaseScheduler`. The schedule is persisted in PostgreSQL.
The `celery-beat` container has exactly one replica (never scale).

The heartbeat (`beat_heartbeat`) writes a timestamp to Redis every 60 seconds.
The beat container's healthcheck validates that this timestamp is recent, verifying
that both the beat and the worker are alive simultaneously.

## Alternatives considered

**Operating system cron:** simple, but execution state is not visible
from the application, requires SSH access to modify schedules, and does not survive
container recreation cleanly.

**Celery beat with a schedule file (`PersistentScheduler`):** the file is lost
when recreating the container or during a deploy. Requires mounting an additional volume.

**APScheduler in-process:** runs inside the Django process, does not scale well and
mixes responsibilities.

## Consequences

- The schedule is visible and editable from Django Admin → Periodic Tasks.
- Schedules in `CELERY_BEAT_SCHEDULE` act as an initial seed: they are created on the first run and then the database is the source of truth. Subsequent changes must be made from the admin, not in the code.
- The beat container **must never have more than one active replica**: two instances would publish each task twice.
- The heartbeat validation in Redis detects if the worker is not processing the tasks the beat publishes (both must be alive for the heartbeat to complete).
