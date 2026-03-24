import logging

import requests
from celery import shared_task
from django.conf import settings

from .embeddings import EmbeddingModelUnavailable, encode_batch, encode_text
from .models import Book, Highlight

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def enrich_book_metadata(self, book_id: int):
    """
    Obtiene metadatos de OpenLibrary API para un libro.
    Usa exponential backoff en caso de rate limiting.
    """
    try:
        book = Book.objects.get(id=book_id)

        # Buscar por ISBN si existe
        if book.isbn:
            url = f"{settings.OPENLIBRARY_API_URL}/books?bibkeys=ISBN:{book.isbn}&format=json&jscmd=data"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                key = f"ISBN:{book.isbn}"

                if key in data:
                    info = data[key]

                    if 'publish_date' in info:
                        try:
                            book.publish_year = int(info['publish_date'][:4])
                        except (ValueError, TypeError):
                            pass

                    if 'subjects' in info and info['subjects']:
                        book.genre = info['subjects'][0]['name']

                    book.save()
                    return f"Book {book_id} enriched successfully"

        return f"No metadata found for book {book_id}"

    except Book.DoesNotExist:
        return f"Book {book_id} not found"
    except requests.RequestException as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@shared_task
def generate_highlight_embedding(highlight_id: int):
    """
    Genera el embedding vectorial para un highlight usando ONNX Runtime.

    Modelo: paraphrase-multilingual-MiniLM-L12-v2 (384 dimensiones)
    """
    try:
        highlight = Highlight.objects.get(id=highlight_id)

        embedding = encode_text(highlight.content)
        highlight.embedding = embedding.tolist()
        highlight.save(update_fields=['embedding'])

        return f"Embedding generado para highlight {highlight_id}"

    except EmbeddingModelUnavailable:
        logger.warning('[embeddings] Modelo no disponible, saltando highlight %s', highlight_id)
        return f"Modelo no disponible para highlight {highlight_id}"
    except Highlight.DoesNotExist:
        return f"Highlight {highlight_id} no encontrado"


@shared_task(
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=300,
)
def batch_generate_embeddings(highlight_ids: list):
    """
    Genera embeddings para múltiples highlights en batch.

    Modelo: paraphrase-multilingual-MiniLM-L12-v2 (384 dimensiones, multilingüe)

    Solo procesa highlights que aún no tienen embedding (embedding__isnull=True),
    para que sea idempotente y seguro ante reenvíos o reintentos.

    Args:
        highlight_ids: Lista de IDs de highlights a procesar
    """
    highlights = list(
        Highlight.objects.filter(id__in=highlight_ids, embedding__isnull=True)
    )

    if not highlights:
        return "No hay highlights pendientes para procesar"

    total = len(highlights)
    logger.info(f"[embeddings] Procesando batch de {total} highlights...")

    # Procesar en sub-lotes para no bloquear la base de datos
    batch_size = 16
    processed = 0

    for i in range(0, total, batch_size):
        batch = highlights[i:i + batch_size]
        contents = [h.content for h in batch]

        try:
            embeddings = encode_batch(contents)

            for highlight, embedding in zip(batch, embeddings):
                highlight.embedding = embedding.tolist()
                highlight.save(update_fields=['embedding'])

            processed += len(batch)
            logger.info(f"[embeddings] ✓ {processed}/{total} completados")

        except EmbeddingModelUnavailable:
            logger.warning('[embeddings] Modelo no disponible, abortando batch.')
            return "Modelo no disponible"
        except Exception as e:
            logger.error(f"[embeddings] ✗ Error en sub-lote: {e}", exc_info=True)
            raise

    logger.info(f"[embeddings] ✓ Batch finalizado: {processed}/{total} embeddings generados.")
    return f"Generados {processed}/{total} embeddings"


# Importar tasks de Goodreads para que Celery las registre al autodiscover
from .goodreads_tasks import sync_all_goodreads_feeds, sync_goodreads_reading, sync_goodreads_rss  # noqa: F401,E402


@shared_task
def promote_trust_levels_task():
    """
    Modelo C: Promoción automática de nivel de confianza.

    Sube de depth=0 a depth=1 a usuarios con >= 30 días de antigüedad
    que no fueron promovidos manualmente.

    Programado diariamente via CELERY_BEAT_SCHEDULE.
    """
    from datetime import timedelta

    from django.utils import timezone

    from accounts.models import Profile

    cutoff_date = timezone.now() - timedelta(days=30)
    promoted = Profile.objects.filter(
        created_at__lte=cutoff_date,
        comment_allowance_depth=0,
        trust_promoted_at__isnull=True,
    ).update(
        comment_allowance_depth=1,
        trust_promoted_at=timezone.now(),
    )

    logger.info(f'[trust] Promovidos {promoted} perfil(es) a depth=1')
    return {'promoted': promoted}


@shared_task
def beat_heartbeat():
    """
    Tarea de latido del Celery Beat + Worker.

    Beat la agenda cada minuto; el worker la ejecuta y escribe el timestamp
    en Redis. El healthcheck del contenedor beat valida que esta clave esté
    actualizada, verificando que AMBOS procesos (beat + worker) estén vivos.
    """
    import time

    import redis as redis_client
    from django.conf import settings

    redis_url = getattr(settings, 'REDIS_URL', 'redis://redis:6379/0')
    r = redis_client.from_url(redis_url, socket_connect_timeout=2)
    r.setex('celerybeat:heartbeat', 120, str(time.time()))
    logger.debug('[beat] Heartbeat actualizado en Redis')
    return 'heartbeat_ok'
