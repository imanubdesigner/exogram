"""
App Social — Comentarios con moderación local.
"""
from django.apps import AppConfig


class SocialConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'social'
    verbose_name = 'Red Social'
