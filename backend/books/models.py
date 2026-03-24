import uuid

from django.db import models
from django.utils import timezone
from pgvector.django import HnswIndex, VectorField

from accounts.models import Profile


class Author(models.Model):
    """Autor de un libro."""
    name = models.CharField(max_length=255, verbose_name="Nombre")
    openlibrary_id = models.CharField(max_length=100, blank=True, verbose_name="ID de OpenLibrary")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['name'])]
        verbose_name = "Autor"
        verbose_name_plural = "Autores"
        ordering = ['name']

    def __str__(self):
        return self.name


class Book(models.Model):
    """Libro con metadatos enriquecidos."""
    title = models.CharField(max_length=500, verbose_name="Título")
    authors = models.ManyToManyField(Author, related_name='books', verbose_name="Autores")
    isbn = models.CharField(max_length=13, unique=True, null=True, blank=True, verbose_name="ISBN")
    cover_image = models.ImageField(upload_to='covers/', null=True, blank=True, verbose_name="Portada")
    openlibrary_id = models.CharField(max_length=100, blank=True, verbose_name="ID de OpenLibrary")
    average_rating = models.FloatField(null=True, blank=True, verbose_name="Calificación promedio")
    publish_year = models.IntegerField(null=True, blank=True, verbose_name="Año de publicación")
    genre = models.CharField(max_length=100, blank=True, verbose_name="Género")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['title']),
            models.Index(fields=['isbn']),
        ]
        verbose_name = "Libro"
        verbose_name_plural = "Libros"
        ordering = ['title']

    def __str__(self):
        authors_str = ', '.join(a.name for a in self.authors.all()[:2])
        return f"{self.title} - {authors_str}" if authors_str else self.title


class Highlight(models.Model):
    """Un highlight/subrayado de un libro."""

    VISIBILITY_CHOICES = [
        ('private', 'Privado'),
        ('unlisted', 'Oculto'),
        ('public', 'Público'),
    ]

    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='highlights')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='highlights')
    content = models.TextField(verbose_name="Contenido")
    note = models.TextField(blank=True, verbose_name="Nota personal")
    location = models.CharField(max_length=50, verbose_name="Ubicación")  # "Loc 450-455" o "Page 123"
    visibility = models.CharField(
        max_length=10,
        choices=VISIBILITY_CHOICES,
        default='private',
        verbose_name="Visibilidad"
    )

    # Embedding vectorial para similitud semántica
    # Modelo: paraphrase-multilingual-MiniLM-L12-v2 — 384 dimensiones, multilingüe
    embedding = VectorField(dimensions=384, null=True, blank=True)

    is_favorite = models.BooleanField(default=False, verbose_name="Favorito")

    created_at = models.DateTimeField(default=timezone.now, verbose_name="Fecha de creación")
    imported_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de importación")
    published_at = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de publicación")

    class Meta:
        indexes = [
            models.Index(fields=['user', 'visibility']),
            models.Index(fields=['book']),
            models.Index(fields=['created_at']),
            HnswIndex(
                name='highlight_embedding_hnsw',
                fields=['embedding'],
                m=16,
                ef_construction=64,
                opclasses=['vector_cosine_ops'],
            ),
        ]
        verbose_name = "Highlight"
        verbose_name_plural = "Highlights"
        ordering = ['-created_at']

    def __str__(self):
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"{preview} ({self.book.title})"

    @property
    def is_public(self) -> bool:
        """Vista booleana de visibilidad para simplificar uso en frontend."""
        return self.visibility == 'public'


class Note(models.Model):
    """Notas de lectura tipo journal—no asociadas a un libro específico."""

    VISIBILITY_CHOICES = [
        ('private', 'Privado'),
        ('unlisted', 'Oculto'),
        ('public', 'Público'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='notes')
    content = models.TextField(verbose_name="Contenido")

    visibility = models.CharField(
        max_length=10,
        choices=VISIBILITY_CHOICES,
        default='private',
        verbose_name="Visibilidad"
    )

    is_favorite = models.BooleanField(default=False, verbose_name="Favorito")

    created_at = models.DateTimeField(default=timezone.now, verbose_name="Fecha de creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Fecha de actualización")

    class Meta:
        indexes = [
            models.Index(fields=['user', 'visibility']),
            models.Index(fields=['created_at']),
        ]
        verbose_name = "Nota"
        verbose_name_plural = "Notas"
        ordering = ['-created_at']

    def __str__(self):
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return preview

    @property
    def is_public(self) -> bool:
        """Vista booleana de visibilidad."""
        return self.visibility == 'public'
