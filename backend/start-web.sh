#!/usr/bin/env bash
set -euo pipefail

# django_celery_beat trae migraciones propias; `migrate` las aplica
# automáticamente sin necesidad de crear migraciones manuales.
python manage.py migrate --noinput
python manage.py collectstatic --noinput

# Configuración de Gunicorn ajustable por entorno.
# Defaults apropiados para una instancia con 2–4 vCPUs y 2–4 GB RAM.
GUNICORN_WORKERS="${GUNICORN_WORKERS:-4}"
GUNICORN_THREADS="${GUNICORN_THREADS:-2}"
GUNICORN_TIMEOUT="${GUNICORN_TIMEOUT:-20}"

exec gunicorn \
  --workers="${GUNICORN_WORKERS}" \
  --threads="${GUNICORN_THREADS}" \
  --worker-class=gthread \
  --timeout="${GUNICORN_TIMEOUT}" \
  --bind=0.0.0.0:8000 \
  --access-logfile=- \
  --error-logfile=- \
  exogram.wsgi
