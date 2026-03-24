"""
Vistas de la app Affinity.

Endpoints para descubrimiento de afinidades entre lectores.
"""
from rest_framework import status, views
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from books.models import Book

from .clustering import find_readers_of_book, find_similar_readers, get_user_centroid
from .models import UserCluster
from .serializers import AlsoReadingSerializer, SimilarReaderSerializer


def _parse_limit(raw_value, default=10, max_value=50):
    """Parsea y acota limit para evitar 500 por valores inválidos."""
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return default
    return max(1, min(value, max_value))


class SimilarReadersView(views.APIView):
    """
    Encuentra lectores con intereses similares.

    GET /api/affinity/similar-readers/?limit=10

    Usa similitud coseno entre centroides de usuario
    (calculados a partir de embeddings de highlights).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = request.user.profile

        if profile.is_hermit_mode:
            return Response({
                'error': 'Tenés el Modo Ermitaño activado. Desactivalo para ver lectores afines.'
            }, status=status.HTTP_403_FORBIDDEN)
        if not profile.is_discoverable:
            return Response({
                'error': (
                    'Tenés el feed desactivado desde privacidad. '
                    'Activá "feed de descubrimiento" para usar esta sección.'
                )
            }, status=status.HTTP_403_FORBIDDEN)

        limit = _parse_limit(request.query_params.get('limit', 10), default=10, max_value=50)
        my_centroid = get_user_centroid(profile)
        if my_centroid is None:
            # Estado temporal: el centroide llega de forma asíncrona por Celery
            # después del primer highlight procesado.
            return Response({
                'results': [],
                'count': 0,
                'not_ready': True,
                'message': 'Tu perfil semántico todavía se está preparando. Volvé a intentar en unos minutos.'
            })

        # Buscar similares
        similar = find_similar_readers(profile, limit=limit)
        serializer = SimilarReaderSerializer(similar, many=True, context={'request': request})

        return Response({
            'results': serializer.data,
            'count': len(serializer.data),
            'not_ready': False,
        })


class AlsoReadingView(views.APIView):
    """
    "María también está leyendo X — ¿querés compartir tus ideas?"

    GET /api/affinity/also-reading/<book_id>/

    Encuentra otros usuarios que están leyendo o leyeron el mismo libro.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, book_id):
        if not request.user.profile.is_discoverable:
            return Response(
                {'error': 'Tenés el feed desactivado desde privacidad.'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            book = Book.objects.get(id=book_id)
        except Book.DoesNotExist:
            return Response(
                {'error': 'Libro no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )

        readers = find_readers_of_book(
            book,
            exclude_profile=request.user.profile,
            limit=10
        )
        serializer = AlsoReadingSerializer(readers, many=True)

        return Response({
            'book': book.title,
            'readers': serializer.data,
            'count': len(serializer.data),
            'message': (
                f'{len(serializer.data)} personas también están leyendo "{book.title}"'
                if serializer.data else None
            )
        })


class MyClusterView(views.APIView):
    """
    Información del cluster del usuario actual.

    GET /api/affinity/me/cluster/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = request.user.profile
        centroid = get_user_centroid(profile)
        cluster = UserCluster.objects.filter(profile=profile).first()

        if centroid is None or cluster is None:
            return Response({
                'has_cluster': False,
                'not_ready': True,
                'message': 'Tu perfil semántico todavía se está preparando. Volvé a intentar en unos minutos.'
            })

        return Response({
            'has_cluster': True,
            'not_ready': False,
            'cluster_label': cluster.cluster_label,
            'highlights_count': cluster.highlights_count,
            'last_computed': cluster.last_computed
        })
