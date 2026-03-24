"""
Worker para sincronización pasiva de Goodreads.

Sincroniza currently-reading desde el HTML público de Goodreads.
Solo lectura. No se envían datos de vuelta a Goodreads.
"""
import logging
import re
from datetime import timedelta
from time import sleep

from celery import shared_task
from django.utils import timezone

from .goodreads_reading_scraper import GoodreadsReadingScraper

logger = logging.getLogger(__name__)


# Throttling ético
REQUEST_DELAY = 5  # segundos entre requests
MIN_SYNC_INTERVAL = timedelta(hours=1)  # mínimo 1 hora entre syncs


def _sync_goodreads_reading_impl(task_self, user_id: int):
    """Implementación compartida de sincronización de currently-reading."""
    from accounts.models import Profile
    from affinity.models import ReadingSession
    from books.models import Author, Book

    try:
        profile = Profile.objects.get(user_id=user_id)
    except Profile.DoesNotExist:
        return f'Profile not found for user {user_id}'

    if not profile.goodreads_username and not profile.goodreads_feed_url:
        return f'No Goodreads username/feed configured for {profile.nickname}'

    try:
        sleep(REQUEST_DELAY)  # Throttling ético

        scrape_username = (profile.goodreads_username or "").strip() or None
        scrape_profile_url = None
        if not scrape_username and profile.goodreads_feed_url:
            match = re.search(r'/review/list_rss/(\d+)', profile.goodreads_feed_url)
            if match:
                scrape_profile_url = f'https://www.goodreads.com/user/show/{match.group(1)}'

        scraper = GoodreadsReadingScraper(
            profile_url=scrape_profile_url,
            username=scrape_username,
            timeout=25
        )
        books_in_progress = scraper.fetch_data()

        if not books_in_progress:
            return f'No currently-reading books found for {profile.nickname}'

        synced = 0
        seen_book_ids = set()
        for item in books_in_progress:
            title = (item.title or '').strip()
            if not title:
                continue

            book = Book.objects.filter(title__iexact=title).first()
            if not book:
                author_name = (item.author or 'Unknown Author').strip()
                author, _ = Author.objects.get_or_create(name=author_name)
                book = Book.objects.create(title=title)
                book.authors.add(author)
            elif item.author:
                # Si encontramos autor en scraping y el libro no tiene autores, lo completamos.
                if not book.authors.exists():
                    author, _ = Author.objects.get_or_create(name=item.author.strip())
                    book.authors.add(author)

            progress = 0.0
            if item.percent is not None:
                progress = max(0.0, min(1.0, item.percent / 100.0))
            elif item.pages_read is not None and item.pages_total and item.pages_total > 0:
                progress = max(0.0, min(1.0, item.pages_read / item.pages_total))

            ReadingSession.objects.update_or_create(
                profile=profile,
                book=book,
                defaults={
                    'status': 'reading',
                    'progress': progress,
                    'finished_at': None,
                }
            )
            seen_book_ids.add(book.id)
            synced += 1
            sleep(REQUEST_DELAY)

        # Cerrar sesiones "reading" que antes estaban sincronizadas y ya no aparecen.
        if seen_book_ids:
            ReadingSession.objects.filter(
                profile=profile,
                status='reading'
            ).exclude(book_id__in=seen_book_ids).update(
                status='finished',
                finished_at=timezone.now()
            )

        return f'Synced {synced} currently-reading books for {profile.nickname}'

    except Exception as exc:
        logger.exception("Goodreads sync failed for user_id=%s", user_id)
        raise task_self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=2, name='books.goodreads_tasks.sync_goodreads_reading')
def sync_goodreads_reading(self, user_id: int):
    """
    Sincroniza currently-reading de Goodreads de un usuario.
    Nombre canónico de task.
    """
    return _sync_goodreads_reading_impl(self, user_id)


@shared_task(bind=True, max_retries=2, name='books.goodreads_tasks.sync_goodreads_rss')
def sync_goodreads_rss(self, user_id: int):
    """
    Alias legacy para compatibilidad retroactiva.
    """
    return _sync_goodreads_reading_impl(self, user_id)


@shared_task
def sync_all_goodreads_feeds():
    """
    Sincroniza todos los feeds de Goodreads configurados.
    Ejecutar periódicamente (ej: cada 6 horas).
    """
    from accounts.models import Profile

    # Incluir usuarios con goodreads_username O goodreads_feed_url configurados.
    # Antes solo se filtraba por goodreads_username, ignorando los de feed_url.
    profiles = Profile.objects.exclude(
        goodreads_username='',
        goodreads_feed_url='',
    ).values_list('user_id', flat=True)

    count = profiles.count()

    for user_id in profiles:
        # Encolar cada sync como task independiente. El delay entre requests
        # está en _sync_goodreads_reading_impl — no corresponde dormir acá:
        # sleep() bloquearía este worker de coordinación por minutos.
        sync_goodreads_reading.delay(user_id)

    return f'Enqueued sync for {count} Goodreads feeds'
