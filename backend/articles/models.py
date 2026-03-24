"""
Modelo Article para artículos éticos integrados en la UI.

Los artículos educan al usuario sobre las decisiones de ingeniería
del sistema, transparentando los algoritmos y la ética detrás.
"""
from django.db import models


class Article(models.Model):
    """
    Artículo divulgativo integrado en la UI.

    Cada artículo tiene un 'placement' que indica dónde se muestra:
    - 'onboarding' → durante el proceso de registro
    - 'footer' → en el footer de la app
    - 'discovery' → en la sección de sugerencias
    - 'comments' → en el panel de comentarios
    - 'import' → durante la importación de Goodreads
    """

    PLACEMENT_CHOICES = [
        ('onboarding', 'Onboarding / Footer'),
        ('discovery', 'Sugerencias de Red'),
        ('comments', 'Panel de Comentarios'),
        ('import', 'Importación de Goodreads'),
    ]

    slug = models.SlugField(unique=True, max_length=100)
    title = models.CharField(max_length=200, verbose_name='Título')
    subtitle = models.CharField(max_length=300, blank=True, verbose_name='Subtítulo')
    content = models.TextField(
        verbose_name='Contenido (Markdown)',
        help_text='Formato Markdown. Se renderiza en el frontend.'
    )
    placement = models.CharField(
        max_length=20,
        choices=PLACEMENT_CHOICES,
        verbose_name='Ubicación en la UI'
    )
    order = models.IntegerField(
        default=0,
        verbose_name='Orden',
        help_text='Orden de aparición dentro de su placement'
    )
    is_published = models.BooleanField(
        default=True,
        verbose_name='Publicado'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Artículo Ético'
        verbose_name_plural = 'Artículos Éticos'
        ordering = ['placement', 'order']

    def __str__(self):
        return f'{self.title} ({self.get_placement_display()})'
