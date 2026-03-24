"""
Vistas de similitud semántica usando pgvector.

Endpoints:
- GET /api/highlights/<id>/similar/ — highlights similares a uno dado
- POST /api/highlights/search/ — búsqueda semántica por texto libre
"""
import logging

from django.db.models import Q
from pgvector.django import CosineDistance
from rest_framework import status, views
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from exogram.throttles import SearchThrottle

from .embeddings import encode_text
from .highlight_serializers import HighlightSerializer
from .models import Highlight

logger = logging.getLogger(__name__)


def _parse_limit(raw_value, default=10, max_value=50):
    """Parsea y acota el parámetro limit para evitar 500 por input inválido."""
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return default
    return max(1, min(value, max_value))


class SimilarHighlightsView(views.APIView):
    """
    Obtiene highlights semánticamente similares a uno dado.

    GET /api/highlights/<id>/similar/?limit=10&scope=mine|public|all

    Parámetros:
    - limit: cantidad máxima de resultados (default 10, max 50)
    - scope: 'mine' (solo mis highlights), 'public' (públicos de otros),
             'all' (ambos). Default: 'all'

    Respeta:
    - Modo Ermitaño: usuarios con is_hermit_mode=True no aparecen
    - Visibilidad: solo highlights públicos de otros usuarios
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [SearchThrottle]

    def get(self, request, highlight_id):
        try:
            highlight = Highlight.objects.get(
                id=highlight_id,
                user=request.user.profile
            )
        except Highlight.DoesNotExist:
            return Response(
                {'error': 'Highlight no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )

        if highlight.embedding is None:
            return Response(
                {'error': 'Este highlight aún no tiene embedding generado'},
                status=status.HTTP_400_BAD_REQUEST
            )

        limit = _parse_limit(request.query_params.get('limit', 10), default=10, max_value=50)
        scope = request.query_params.get('scope', 'all')

        # Base queryset: excluir el highlight original, su mismo libro, y sin embedding
        qs = Highlight.objects.exclude(
            id=highlight_id
        ).exclude(
            book_id=highlight.book_id
        ).exclude(
            embedding__isnull=True
        )

        if scope == 'mine':
            qs = qs.filter(user=request.user.profile)
        elif scope == 'public':
            qs = self._apply_privacy_filters(qs, request.user.profile)
        else:  # 'all'
            qs = qs.filter(
                Q(user=request.user.profile) |
                Q(
                    visibility='public',
                    user__is_hermit_mode=False
                )
            )

        # Ordenar por similitud coseno (menor distancia = más similar)
        # Umbral: 0.45 de distancia coseno (~0.55 similitud)
        similar = qs.annotate(
            distance=CosineDistance('embedding', highlight.embedding)
        ).filter(
            distance__lt=0.45
        ).order_by('distance')[:limit]

        serializer = HighlightSerializer(similar, many=True)

        return Response({
            'source_highlight_id': highlight_id,
            'results': serializer.data,
            'count': len(serializer.data)
        })

    def _apply_privacy_filters(self, qs, current_profile):
        """Filtra respetando Modo Ermitaño y visibilidad."""
        return qs.filter(
            visibility='public',
            user__is_hermit_mode=False
        ).exclude(
            user=current_profile
        )


class SemanticSearchView(views.APIView):
    """
    Búsqueda semántica por texto libre.

    POST /api/highlights/search/
    {
        "query": "la ciencia es una manera de pensar",
        "limit": 10,
        "scope": "mine"  // Opcional: mine|public|all (default: mine)
    }

    Genera un embedding del texto de búsqueda y encuentra highlights
    similares usando pgvector cosine distance.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [SearchThrottle]

    def post(self, request):
        query = request.data.get('query', '').strip()
        if not query:
            return Response(
                {'error': 'El campo query es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )

        limit = _parse_limit(request.data.get('limit', 10), default=10, max_value=50)
        scope = request.data.get('scope', 'mine')

        # Generar embedding del texto de búsqueda
        try:
            query_embedding = encode_text(query).tolist()
        except Exception:
            logger.exception("Error generando embedding para query='%s'", query[:80])
            return Response(
                {'error': 'No se pudo procesar la búsqueda. Intentá de nuevo más tarde.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Filtrar por scope
        qs = Highlight.objects.exclude(embedding__isnull=True)

        if scope == 'mine':
            qs = qs.filter(user=request.user.profile)
        elif scope == 'public':
            qs = qs.filter(
                visibility='public',
                user__is_hermit_mode=False
            ).exclude(user=request.user.profile)
        else:  # 'all'
            qs = qs.filter(
                Q(user=request.user.profile) |
                Q(
                    visibility='public',
                    user__is_hermit_mode=False
                )
            )

        # Búsqueda por similitud con umbral
        results = qs.annotate(
            distance=CosineDistance('embedding', query_embedding)
        ).filter(
            distance__lt=0.45
        ).order_by('distance')[:limit]

        serializer = HighlightSerializer(results, many=True)

        return Response({
            'query': query,
            'results': serializer.data,
            'count': len(serializer.data)
        })


class HighlightEmbeddingStatusView(views.APIView):
    """
    Retorna el estado del procesamiento de embeddings del usuario.

    GET /api/highlights/embedding-status/

    Response:
    {
        "total": 1500,
        "missing": 42
    }
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Highlight.objects.filter(user=request.user.profile)
        total = qs.count()
        missing = qs.filter(embedding__isnull=True).count()

        return Response({
            'total': total,
            'missing': missing
        })
