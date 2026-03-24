"""
Modelos de la app Threads.

Thread    — Hilo privado entre dos lectores afines.
ThreadMessage — Mensaje dentro de un hilo.

Filosofía:
- Sin likes, sin contadores de popularidad.
- Sin notificaciones push (polling simple desde el cliente).
- Solo pueden abrir hilo usuarios dentro de la distancia de red permitida.
"""
from django.db import models

from accounts.models import Profile


class Thread(models.Model):
    """
    Conversación privada entre dos lectores.

    Los participantes se fijan al crear el hilo.
    No hay grupos: máximo 2 participantes.
    """
    participants = models.ManyToManyField(
        Profile,
        related_name='threads',
        verbose_name='Participantes',
    )
    # Contexto opcional: el libro que originó la charla
    context_book_title = models.CharField(
        max_length=500,
        blank=True,
        verbose_name='Libro de contexto',
        help_text='Título del libro que dio origen al hilo, si aplica.',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Creado el')
    last_message_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Último mensaje el',
    )

    class Meta:
        verbose_name = 'Hilo'
        verbose_name_plural = 'Hilos'
        ordering = ['-last_message_at', '-created_at']

    def __str__(self):
        nicknames = ', '.join(p.nickname for p in self.participants.all()[:2])
        return f'Hilo [{nicknames}]'

    def get_other_participant(self, profile):
        """Retorna el otro participante del hilo."""
        return self.participants.exclude(id=profile.id).first()


class ThreadMessage(models.Model):
    """
    Mensaje dentro de un hilo privado.
    """
    thread = models.ForeignKey(
        Thread,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name='Hilo',
    )
    author = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='thread_messages',
        verbose_name='Autor',
    )
    content = models.TextField(
        max_length=2000,
        verbose_name='Contenido',
        help_text='Máximo 2000 caracteres. Sin markdown.',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Enviado el')

    class Meta:
        verbose_name = 'Mensaje'
        verbose_name_plural = 'Mensajes'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['thread', 'created_at']),
        ]

    def __str__(self):
        preview = self.content[:60] + '...' if len(self.content) > 60 else self.content
        return f'@{self.author.nickname}: {preview}'
