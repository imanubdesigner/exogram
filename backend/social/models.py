"""
Modelos de la app Social.

Comment — Comentario en un highlight público.
Incluye moderación automática pre-publicación.
"""
from django.db import models
from django.utils import timezone

from accounts.models import Profile
from books.models import Highlight


class Comment(models.Model):
    """
    Comentario en un highlight público.

    Reglas:
    - Solo se puede comentar en highlights públicos
    - Los comentarios pasan por moderación automática antes de publicarse
    - No hay likes ni contadores de popularidad (filosofía Zen)
    """

    STATUS_CHOICES = [
        ('pending', 'Pendiente de moderación'),
        ('approved', 'Aprobado'),
        ('rejected', 'Rechazado'),
    ]

    author = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='Autor'
    )
    highlight = models.ForeignKey(
        Highlight,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='Highlight'
    )
    content = models.TextField(
        max_length=1000,
        verbose_name='Contenido',
        help_text='Máximo 1000 caracteres. Sin markdown.'
    )

    # Moderación
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Estado de moderación'
    )
    toxicity_score = models.FloatField(
        default=0.0,
        verbose_name='Score de toxicidad',
        help_text='0.0 = seguro, 1.0 = tóxico'
    )
    moderation_reason = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Razón de moderación'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    moderated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Comentario'
        verbose_name_plural = 'Comentarios'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['highlight', 'status']),
            models.Index(fields=['author']),
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        preview = self.content[:50] + '...' if len(self.content) > 50 else self.content
        return f'{self.author.nickname}: {preview}'

    def approve(self):
        """Aprueba el comentario."""
        self.status = 'approved'
        self.moderated_at = timezone.now()
        self.save(update_fields=['status', 'moderated_at'])

    def reject(self, reason=''):
        """Rechaza el comentario."""
        self.status = 'rejected'
        self.moderation_reason = reason
        self.moderated_at = timezone.now()
        self.save(update_fields=['status', 'moderation_reason', 'moderated_at'])


class UserFollow(models.Model):
    """
    Relación de seguimiento entre dos perfiles.

    Filosofía Zen: Nadie sabe quién lo sigue ni cuántos seguidores tiene.
    Solo sirve para ver los highlights de esta persona en tu propio feed.
    """
    follower = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='following',
        verbose_name='Seguidor'
    )
    following = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='followers',
        verbose_name='Siguiendo a'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Seguidor'
        verbose_name_plural = 'Seguidores'
        unique_together = ('follower', 'following')
        indexes = [
            models.Index(fields=['follower', 'following']),
            models.Index(fields=['following']),
        ]

    def __str__(self):
        return f'{self.follower.nickname} sigue a {self.following.nickname}'
