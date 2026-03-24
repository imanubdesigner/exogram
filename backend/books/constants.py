"""
Constantes y enumeraciones para la app Books.

Define tipos de visibilidad y configuración de embeddings.
"""

from enum import Enum


class HighlightVisibility(Enum):
    """Estados de visibilidad de highlights."""
    PRIVATE = 'private'    # Solo el propietario
    UNLISTED = 'unlisted'  # Solo con link directo
    PUBLIC = 'public'      # Visible en búsquedas


# Choices para Django model
VISIBILITY_CHOICES = [
    ('private', 'Privado'),
    ('unlisted', 'Oculto'),
    ('public', 'Público'),
]


class ProfileVisibility(Enum):
    """Estados de visibilidad de perfil."""
    PRIVATE = 'private'    # Solo yo
    UNLISTED = 'unlisted'  # Con link directo
    PUBLIC = 'public'      # Visible en búsquedas


PROFILE_VISIBILITY_CHOICES = [
    ('private', 'Privado'),
    ('unlisted', 'Oculto'),
    ('public', 'Público'),
]


# Embedding configuration
EMBEDDING_MODEL = 'paraphrase-multilingual-MiniLM-L12-v2'
EMBEDDING_DIMENSIONS = 384
EMBEDDING_BATCH_SIZE = 32
