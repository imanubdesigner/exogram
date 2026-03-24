"""
Vistas de la app Discovery.

Feed de contenido público de usuarios con afinidades semánticas.
"""
from pgvector.django import CosineDistance
from rest_framework import views
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import Profile
from affinity.clustering import get_user_centroid
from affinity.models import UserCluster
from books.highlight_serializers import HighlightSerializer
from books.models import Highlight


def _parse_limit(raw_value, default=20, max_value=50):
    """Parsea y acota limit para evitar 500 por valores inválidos."""
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return default
    return max(1, min(value, max_value))


class DiscoverFeedView(views.APIView):
    """
    Feed de descubrimiento: highlights públicos de usuarios
    con intereses similares.

    GET /api/discovery/feed/?limit=20

    Algoritmo:
    1. Lee el centroide ya persistido del usuario actual
    2. Encuentra los N usuarios más similares
    3. Retorna sus highlights públicos más recientes

    Respeta Modo Ermitaño y privacidad.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = request.user.profile

        if profile.is_hermit_mode:
            return Response({
                'error': 'El Modo Ermitaño está activado. Desactivalo para descubrir lectores afines.',
                'hermit_mode': True
            }, status=403)
        if not profile.is_discoverable:
            return Response({
                'error': (
                    'Tenés el feed desactivado desde privacidad. '
                    'Activá "feed de descubrimiento" para usar esta sección.'
                ),
                'discover_disabled': True
            }, status=403)

        limit = _parse_limit(request.query_params.get('limit', 20), default=20, max_value=50)

        my_centroid = get_user_centroid(profile)
        if my_centroid is None:
            # Estado temporal: el centroide se actualiza en background por Celery
            # cuando procesa el primer highlight con embedding.
            return Response({
                'results': [],
                'count': 0,
                'not_ready': True,
                'message': 'Tu perfil semántico todavía se está preparando. Volvé a intentar en unos minutos.'
            })

        # Encontrar clusters similares
        similar_clusters = UserCluster.objects.filter(
            profile__is_hermit_mode=False,
            profile__is_discoverable=True,
            centroid__isnull=False
        ).exclude(
            profile=profile
        ).order_by(
            CosineDistance('centroid', my_centroid)
        )[:10]  # Top 10 usuarios similares

        # Obtener highlights públicos de esos usuarios y de los seguidos
        similar_profiles = [c.profile for c in similar_clusters]

        followed_profiles = Profile.objects.filter(
            followers__follower=profile
        )

        all_profiles_to_show = list(set(similar_profiles + list(followed_profiles)))

        highlights = Highlight.objects.filter(
            user__in=all_profiles_to_show,
            visibility='public',
            user__is_hermit_mode=False,
            user__is_discoverable=True,
        ).select_related('book', 'user').prefetch_related(
            'book__authors'
        ).order_by('-created_at')

        from rest_framework.pagination import PageNumberPagination
        paginator = PageNumberPagination()
        paginator.page_size = limit
        paginated_highlights = paginator.paginate_queryset(highlights, request)

        serializer = HighlightSerializer(paginated_highlights, many=True)

        return Response({
            'results': serializer.data,
            'count': paginator.page.paginator.count,
            'not_ready': False,
            'next': bool(paginator.get_next_link()),
            'previous': bool(paginator.get_previous_link()),
            'similar_readers': len(similar_profiles)
        })


class FollowingFeedView(views.APIView):
    """
    Feed exclusivo de usuarios seguidos.
    GET /api/discovery/feed/following/?limit=20
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = request.user.profile

        limit = _parse_limit(request.query_params.get('limit', 20), default=20, max_value=50)

        # Buscar perfiles seguidos
        from accounts.models import Profile
        followed_profiles = Profile.objects.filter(
            followers__follower=profile,
            is_hermit_mode=False
        )

        highlights = Highlight.objects.filter(
            user__in=followed_profiles,
            visibility='public',
            user__is_hermit_mode=False,
        ).select_related('book', 'user').prefetch_related(
            'book__authors'
        ).order_by('-created_at')

        from rest_framework.pagination import PageNumberPagination
        paginator = PageNumberPagination()
        paginator.page_size = limit
        paginated_highlights = paginator.paginate_queryset(highlights, request)

        serializer = HighlightSerializer(paginated_highlights, many=True)

        return Response({
            'results': serializer.data,
            'count': paginator.page.paginator.count,
            'next': bool(paginator.get_next_link()),
            'previous': bool(paginator.get_previous_link()),
        })
