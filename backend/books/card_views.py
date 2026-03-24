"""
Vista para generar tarjetas de citas como imágenes JPEG.
"""
from django.http import HttpResponse
from rest_framework import status, views
from rest_framework.permissions import IsAuthenticated

from .card_generator import generate_quote_card
from .models import Highlight


class QuoteCardView(views.APIView):
    """
    Genera una tarjeta de cita como imagen JPEG.

    GET /api/highlights/<id>/card/

    Retorna una imagen JPEG de 1080x1080 con el highlight
    formateado como tarjeta para compartir en redes.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, highlight_id):
        try:
            highlight = Highlight.objects.select_related(
                'book'
            ).prefetch_related(
                'book__authors'
            ).get(
                id=highlight_id,
                user=request.user.profile
            )
        except Highlight.DoesNotExist:
            return HttpResponse(
                'Highlight no encontrado',
                status=status.HTTP_404_NOT_FOUND
            )

        # Obtener datos
        authors = [a.name for a in highlight.book.authors.all()]
        author_str = ', '.join(authors) if authors else 'Autor desconocido'

        # Generar imagen
        image_bytes = generate_quote_card(
            content=highlight.content,
            book_title=highlight.book.title,
            author_name=author_str,
            location=highlight.location
        )

        response = HttpResponse(image_bytes, content_type='image/jpeg')
        response['Content-Disposition'] = (
            f'inline; filename="quote-{highlight_id}.jpg"'
        )
        return response
