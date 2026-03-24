"""
Modelos de la app Affinity.

UserCluster — Cluster de intereses del usuario (centroides).
ReadingSession — Sesiones de lectura para tracking de progreso.
"""
from django.db import models
from pgvector.django import HnswIndex, VectorField

from accounts.models import Profile
from books.models import Book


class UserCluster(models.Model):
    """
    Cluster de intereses de un usuario.

    El centroide se calcula como el promedio de los embeddings
    de todos los highlights del usuario. Sirve para encontrar
    "almas gemelas intelectuales" (afinidad semántica).
    """
    profile = models.OneToOneField(
        Profile,
        on_delete=models.CASCADE,
        related_name='cluster',
        verbose_name='Perfil'
    )

    # Vector centroide: promedio de embeddings del usuario
    centroid = VectorField(
        dimensions=384,
        null=True,
        blank=True,
        verbose_name='Centroide'
    )

    # Metadata de clustering
    cluster_label = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Etiqueta de cluster',
        help_text='Grupo asignado por K-Means'
    )
    highlights_count = models.IntegerField(
        default=0,
        verbose_name='Cantidad de highlights usados'
    )

    # Timestamps
    last_computed = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Último cálculo'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Cluster de Usuario'
        verbose_name_plural = 'Clusters de Usuarios'
        indexes = [
            HnswIndex(
                name='usercluster_centroid_hnsw',
                fields=['centroid'],
                m=16,
                ef_construction=64,
                opclasses=['vector_cosine_ops'],
            ),
        ]

    def __str__(self):
        label = self.cluster_label if self.cluster_label is not None else '?'
        return f'{self.profile.nickname} — Cluster {label}'


class ReadingSession(models.Model):
    """
    Sesión de lectura de un usuario con un libro.

    Permite tracking de progreso: qué está leyendo, cuánto leyó,
    y cuándo terminó. Usado para "María también está leyendo X".
    """
    STATUS_CHOICES = [
        ('reading', 'Leyendo'),
        ('finished', 'Terminado'),
        ('abandoned', 'Abandonado'),
    ]

    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='reading_sessions',
        verbose_name='Lector'
    )
    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name='reading_sessions',
        verbose_name='Libro'
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='reading',
        verbose_name='Estado'
    )
    progress = models.FloatField(
        default=0.0,
        verbose_name='Progreso (%)',
        help_text='0.0 a 1.0'
    )

    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Sesión de Lectura'
        verbose_name_plural = 'Sesiones de Lectura'
        unique_together = ['profile', 'book']
        indexes = [
            models.Index(fields=['profile', 'status']),
            models.Index(fields=['book', 'status']),
        ]

    def __str__(self):
        return f'{self.profile.nickname} → {self.book.title} ({self.get_status_display()})'
