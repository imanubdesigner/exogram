"""
App: threads

Hilos privados entre lectores afines.
Mini-foro de la antigua internet: sin likes, sin contadores, sin algoritmos.
Solo texto y tiempo.
"""
from django.apps import AppConfig


class ThreadsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'threads'
    verbose_name = 'Hilos privados'
