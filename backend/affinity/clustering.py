"""
Lógica de clustering para afinidad entre usuarios.

Lee centroides precomputados y ejecuta búsquedas de afinidad
sin recalcular embeddings en requests síncronas.
"""
from pgvector.django import CosineDistance

from .models import UserCluster


def get_user_centroid(profile):
    """
    Lee el centroide persistido del usuario desde UserCluster.

    Modelo eventualmente consistente: el valor puede estar levemente
    desactualizado si acaba de entrar un highlight, y eso es aceptable.
    """
    cluster = UserCluster.objects.filter(profile=profile).only('centroid').first()
    if cluster is None or cluster.centroid is None:
        return None
    return cluster.centroid


def compute_user_centroid(profile):
    """Compatibilidad: retorna el centroide persistido del usuario."""
    return get_user_centroid(profile)


def update_user_cluster(profile):
    """
    Helper legacy para disparar recálculo asíncrono del cluster.

    Args:
        profile: instancia de Profile

    Returns:
        Cluster persistido actual si existe; None si aún no está listo
    """
    # Helper legacy: dispara recálculo async y devuelve el estado actual.
    from .tasks import recalculate_user_centroid

    recalculate_user_centroid.delay(profile.id)
    return UserCluster.objects.filter(profile=profile, centroid__isnull=False).first()


def find_similar_readers(profile, limit=10):
    """
    Encuentra lectores con intereses similares basándose
    en la similitud coseno de sus centroides.

    Respeta:
    - Modo Ermitaño: excluye usuarios con is_hermit_mode=True

    Args:
        profile: instancia de Profile del usuario actual
        limit: cantidad máxima de resultados

    Returns:
        QuerySet de UserCluster ordenado por similitud
    """
    my_centroid = get_user_centroid(profile)
    if my_centroid is None:
        return UserCluster.objects.none()

    return UserCluster.objects.filter(
        profile__is_hermit_mode=False,
        profile__is_discoverable=True,
        centroid__isnull=False
    ).exclude(
        profile=profile
    ).order_by(
        CosineDistance('centroid', my_centroid)
    )[:limit]


def find_readers_of_book(book, exclude_profile=None, limit=10):
    """
    Encuentra otros lectores del mismo libro.

    "María también está leyendo X — ¿querés compartir tus ideas con ella?"

    Args:
        book: instancia de Book
        exclude_profile: perfil a excluir (usuario actual)
        limit: cantidad máxima

    Returns:
        Lista de perfiles que están leyendo o leyeron el libro
    """
    from .models import ReadingSession

    qs = ReadingSession.objects.filter(
        book=book,
        profile__is_hermit_mode=False,
        profile__is_discoverable=True
    ).select_related('profile')

    if exclude_profile:
        qs = qs.exclude(profile=exclude_profile)

    return qs[:limit]
