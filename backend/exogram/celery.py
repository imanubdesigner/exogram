"""
Configuración de Celery para Exogram.
"""
import logging
import os

from celery import Celery
from django.conf import settings

logger = logging.getLogger(__name__)

# Configurar el módulo de settings de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'exogram.settings')

app = Celery('exogram')

# Usar configuración de Django con prefijo CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-descubrir tareas en todas las apps instaladas
app.autodiscover_tasks()

# Auto-descubrir módulos de tareas no estándar.
# books.goodreads_tasks.py define workers de sincronización RSS.
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS, related_name='goodreads_tasks')


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Task de debug para verificar que Celery funciona."""
    logger.debug('Request: %r', self.request)
