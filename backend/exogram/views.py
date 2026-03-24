import logging

import redis as redis_client
from django.conf import settings
from django.db import connection
from django.http import JsonResponse

logger = logging.getLogger(__name__)


def health_view(_request):
    db_ok = False
    redis_ok = False

    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
        db_ok = True
    except Exception:
        logger.exception('Health check: fallo de conexión a la base de datos')

    try:
        r = redis_client.from_url(
            getattr(settings, 'REDIS_URL', 'redis://redis:6379/0'),
            socket_connect_timeout=2,
        )
        r.ping()
        redis_ok = True
    except Exception:
        logger.exception('Health check: fallo de conexión a Redis')

    all_ok = db_ok and redis_ok
    payload = {
        'status': 'ok' if all_ok else 'error',
        'db': 'ok' if db_ok else 'error',
        'redis': 'ok' if redis_ok else 'error',
    }
    return JsonResponse(payload, status=200 if all_ok else 503)
