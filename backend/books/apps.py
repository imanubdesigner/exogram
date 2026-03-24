from django.apps import AppConfig


class BooksConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'books'
    verbose_name = 'Libros y Highlights'

    def ready(self):
        # Import side-effect: registra signal handlers de books/signals.py
        import books.signals  # noqa: F401
