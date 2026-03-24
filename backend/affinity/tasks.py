"""
Tareas Celery para la app Affinity.
"""
import numpy as np
from celery import shared_task
from django.utils import timezone

from accounts.models import Profile
from books.models import Highlight

from .models import UserCluster


def _resolve_profile(user_id: int):
    """
    Resuelve el identificador recibido por compatibilidad:
    - Highlight.user_id (Profile.pk)
    - User.id histórico usado por tareas legacy
    """
    profile = Profile.objects.filter(id=user_id).first()
    if profile:
        return profile
    return Profile.objects.filter(user_id=user_id).first()


@shared_task
def recalculate_user_centroid(user_id: int):
    """
    Recalcula y persiste el centroide de un usuario en UserCluster.centroid.

    Este task es el único lugar donde se escribe el centroide y es idempotente:
    ejecutar varias veces con el mismo estado de highlights produce el mismo valor.
    """
    profile = _resolve_profile(user_id)
    if profile is None:
        return f'Profile not found for user {user_id}'

    embeddings = list(
        Highlight.objects.filter(user=profile, embedding__isnull=False)
        .values_list('embedding', flat=True)
    )

    cluster, _ = UserCluster.objects.get_or_create(profile=profile)

    if not embeddings:
        cluster.centroid = None
        cluster.highlights_count = 0
        cluster.last_computed = timezone.now()
        cluster.save(update_fields=['centroid', 'highlights_count', 'last_computed', 'updated_at'])
        return f'No embeddings for {profile.nickname}'

    matrix = np.array(embeddings, dtype=np.float32)
    centroid = np.mean(matrix, axis=0)
    norm = np.linalg.norm(centroid)
    if norm > 0:
        centroid = centroid / norm

    cluster.centroid = centroid.tolist()
    cluster.highlights_count = len(embeddings)
    cluster.last_computed = timezone.now()
    cluster.save(update_fields=['centroid', 'highlights_count', 'last_computed', 'updated_at'])
    return f'Cluster updated for {profile.nickname}'


@shared_task
def rebuild_all_clusters(full=False):
    """
    Recalcula clusters de usuarios que tienen highlights nuevos.

    Por defecto (full=False) solo actualiza perfiles con highlights importados
    después de la última computación del centroide (delta incremental).
    Con full=True recalcula todos (útil para re-seed o cambio de modelo).

    Ejecutar periódicamente (ej: cada 6 horas via Celery Beat).
    """
    profiles = Profile.objects.filter(is_hermit_mode=False)

    if not full:
        # Incremental: solo perfiles con highlights nuevos desde último cálculo
        from django.db.models import OuterRef, Q, Subquery

        profiles = profiles.filter(
            Q(cluster__isnull=True)  # Nunca computado
            | Q(cluster__last_computed__isnull=True)  # Computado sin timestamp
            | Q(  # Tiene highlights más nuevos que el último cálculo
                highlights__imported_at__gt=Subquery(
                    UserCluster.objects.filter(
                        profile=OuterRef('pk')
                    ).values('last_computed')[:1]
                )
            )
        ).distinct()

    updated = 0
    for profile in profiles:
        result = recalculate_user_centroid(profile.id)
        if result.startswith('Cluster updated'):
            updated += 1

    total = profiles.count()
    return f'Updated {updated}/{total} clusters ({"full" if full else "incremental"})'


@shared_task
def rebuild_user_cluster(user_id: int):
    """
    Recalcula el cluster de un usuario específico.
    Se puede llamar después de importar highlights nuevos.
    """
    return recalculate_user_centroid(user_id)
