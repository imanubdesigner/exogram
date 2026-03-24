import logging

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import generics, status, views
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from accounts.models import Profile
from affinity.tasks import recalculate_user_centroid
from social.services import (
    CommentServiceError,
    assert_can_view_comments,
    create_comment_for_highlight,
    get_highlight_or_error,
)

from .highlight_serializers import (
    CommentSerializer,
    HighlightCreateSerializer,
    HighlightImportResponseSerializer,
    HighlightSerializer,
    HighlightUploadResponseSerializer,
)
from .models import Author, Book, Highlight
from .parsers.kindle_parser import KindleClippingsParser, group_by_book
from .tasks import batch_generate_embeddings

logger = logging.getLogger(__name__)


class HighlightUploadView(views.APIView):
    """
    Upload y preview de archivo My Clippings.txt.

    POST /api/highlights/upload/

    Parsea el archivo y retorna JSON para preview.
    NO guarda nada en la base de datos.
    Marca cada highlight como is_new/is_existing.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB

    def post(self, request):
        file_obj = request.FILES.get('file')

        if not file_obj:
            return Response({
                'error': 'No file provided'
            }, status=status.HTTP_400_BAD_REQUEST)

        if file_obj.size > self.MAX_UPLOAD_SIZE:
            return Response({
                'error': 'El archivo es demasiado grande. El tamaño máximo es 5 MB.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Leer contenido del archivo
        try:
            content = file_obj.read().decode('utf-8')
        except UnicodeDecodeError:
            return Response({
                'error': 'File must be UTF-8 encoded'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Parsear highlights
        parser = KindleClippingsParser()
        parsed_highlights = parser.parse(content)

        if not parsed_highlights:
            return Response({
                'error': 'No highlights found in file'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Agrupar por libro
        grouped = group_by_book(parsed_highlights)
        books_found = len(grouped)

        # Detectar duplicados y marcar nuevos/existentes
        parsed_contents = [h['content'] for h in parsed_highlights]
        existing_contents = set(
            Highlight.objects.filter(
                user=request.user.profile,
                content__in=parsed_contents
            ).values_list('content', flat=True)
        )

        new_count = 0
        existing_count = 0

        for h in parsed_highlights:
            if h['content'] in existing_contents:
                h['is_new'] = False
                existing_count += 1
            else:
                h['is_new'] = True
                new_count += 1

        response_data = {
            'total_parsed': len(parsed_highlights),
            'highlights': parsed_highlights,
            'books_found': books_found,
            'duplicates_detected': existing_count,
            'new_count': new_count,
            'existing_count': existing_count
        }

        serializer = HighlightUploadResponseSerializer(data=response_data)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.data)


class HighlightImportView(views.APIView):
    """
    Importa highlights a la base de datos.
    SIEMPRE importa como privado. La visibilidad se cambia
    individualmente después desde la biblioteca.

    POST /api/highlights/import/
    {
        "highlights": [...]
    }

    Después de la importación, encola una tarea Celery para generar
    embeddings de todos los highlights pendientes del usuario
    (incluye los recién creados y los preexistentes sin embedding).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        highlights_data = request.data.get('highlights', [])

        if not highlights_data:
            return Response({
                'error': 'No highlights provided'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Forzar visibilidad privada en todos
        for h_data in highlights_data:
            h_data['visibility'] = 'private'

        serializer = HighlightCreateSerializer(data=highlights_data, many=True)
        serializer.is_valid(raise_exception=True)

        # Importar en transacción
        with transaction.atomic():
            result = self._import_highlights(
                request.user.profile,
                serializer.validated_data
            )

        # Encolar tarea Celery para embeddings pendientes.
        # Se consulta DESPUÉS de cerrar la transacción para que los highlights
        # recién creados ya estén commiteados y visibles para el worker.
        # Incluye tanto nuevos como preexistentes sin embedding,
        # cubriendo el caso en que todo el import sea "duplicado".
        pending_ids = list(
            Highlight.objects.filter(
                user=request.user.profile,
                embedding__isnull=True
            ).values_list('id', flat=True)
        )
        if pending_ids:
            batch_generate_embeddings.delay(pending_ids)
            logger.info(
                f'[embeddings] Tarea Celery encolada para {len(pending_ids)} '
                f'highlights pendientes del usuario {request.user.profile}.'
            )

        response_serializer = HighlightImportResponseSerializer(data=result)
        response_serializer.is_valid(raise_exception=True)

        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def _import_highlights(self, user_profile, highlights_data):
        # 1. Pre-fetch existing highlights to avoid N queries for duplicates
        contents = [h['content'] for h in highlights_data]
        existing_highlights = {
            h.content: h for h in Highlight.objects.filter(user=user_profile, content__in=contents)
        }

        # 2. Pre-fetch books and authors to avoid redundant lookups
        titles = {h['title'] for h in highlights_data}
        author_names = {h['author'] for h in highlights_data}

        # Cache existing books (using lower() for case-insensitive matching in memory)
        books_cache = {b.title.lower(): b for b in Book.objects.filter(title__in=titles)}
        authors_cache = {a.name: a for a in Author.objects.filter(name__in=author_names)}

        to_create_highlights = []
        imported = 0
        skipped_duplicates = 0
        books_created = 0
        books_matched = 0

        for h_data in highlights_data:
            content = h_data['content']

            # Handle duplicates
            if content in existing_highlights:
                existing = existing_highlights[content]
                # If parsed file has a note for this duplicate, update it
                if h_data.get('note'):
                    if not existing.note:
                        existing.note = h_data['note']
                        existing.save(update_fields=['note'])
                    elif h_data['note'] not in existing.note:
                        existing.note += f"\n\n{h_data['note']}"
                        existing.save(update_fields=['note'])

                skipped_duplicates += 1
                continue

            # Resolve Book & Author
            title = h_data['title']
            author_name = h_data['author']

            book = books_cache.get(title.lower())
            if not book:
                # Resolve Author
                author = authors_cache.get(author_name)
                if not author:
                    author = Author.objects.create(name=author_name)
                    authors_cache[author_name] = author

                # Create Book
                book = Book.objects.create(title=title)
                book.authors.add(author)
                books_cache[title.lower()] = book
                books_created += 1
            else:
                books_matched += 1

            # Prepare Highlight object for bulk_create
            to_create_highlights.append(Highlight(
                user=user_profile,
                book=book,
                content=content,
                note=h_data.get('note', ''),
                location=h_data['location'],
                created_at=h_data['created_at'],
                visibility='private'
            ))
            imported += 1

        if to_create_highlights:
            Highlight.objects.bulk_create(to_create_highlights)
            # Trigger centroid recalculation explicitly once
            # (bulk_create doesn't fire signals)
            recalculate_user_centroid.delay(user_profile.id)

        return {
            'imported': imported,
            'skipped_duplicates': skipped_duplicates,
            'books_created': books_created,
            'books_matched': books_matched
        }


class HighlightListView(generics.ListAPIView):
    """
    Lista TODOS los highlights del usuario autenticado.

    GET /api/highlights/
    GET /api/highlights/?book_id=N  (filtrar por libro)
    """
    permission_classes = [IsAuthenticated]
    serializer_class = HighlightSerializer

    def get_queryset(self):
        highlights = Highlight.objects.filter(
            user=self.request.user.profile
        ).select_related('book').prefetch_related('book__authors').order_by('-created_at')

        # Filtro por libro
        book_id = self.request.query_params.get('book_id')
        if book_id:
            highlights = highlights.filter(book_id=book_id)

        return highlights


class HighlightUpdateView(views.APIView):
    """
    Actualiza o elimina un highlight individual.

    PATCH /api/highlights/<id>/
    {
        "is_public": true,   // o "visibility": "public"
        "note": "Nota",
        "is_favorite": true
    }

    DELETE /api/highlights/<id>/
    Elimina el highlight permanentemente.
    """
    permission_classes = [IsAuthenticated]

    def _get_highlight_or_404(self, highlight_id, profile):
        try:
            return Highlight.objects.get(id=highlight_id, user=profile)
        except Highlight.DoesNotExist:
            return None

    def patch(self, request, highlight_id):
        highlight = self._get_highlight_or_404(highlight_id, request.user.profile)
        if not highlight:
            return Response(
                {'error': 'Highlight no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Campos actualizables
        visibility = request.data.get('visibility')
        is_public = request.data.get('is_public')
        note = request.data.get('note')
        is_favorite = request.data.get('is_favorite')

        if visibility is not None and is_public is not None:
            return Response(
                {'error': 'Envía solo uno de estos campos: "visibility" o "is_public"'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if is_public is not None:
            if not isinstance(is_public, bool):
                return Response(
                    {'error': '"is_public" debe ser booleano (true/false)'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            visibility = 'public' if is_public else 'private'

        if visibility is not None:
            if visibility not in ('private', 'public', 'unlisted'):
                return Response(
                    {'error': 'Visibilidad inválida'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            # Asignar published_at la primera vez que se hace público
            if visibility == 'public' and highlight.visibility != 'public' and not highlight.published_at:
                highlight.published_at = timezone.now()
            highlight.visibility = visibility

        if note is not None:
            highlight.note = note

        if is_favorite is not None:
            highlight.is_favorite = is_favorite

        highlight.save()
        serializer = HighlightSerializer(highlight)
        return Response(serializer.data)

    def delete(self, request, highlight_id):
        highlight = self._get_highlight_or_404(highlight_id, request.user.profile)
        if not highlight:
            return Response(
                {'error': 'Highlight no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )

        highlight.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PublicHighlightListView(views.APIView):
    """
    Lista los highlights públicos de un usuario específico.

    GET /api/users/<nickname>/highlights/
    """
    # No requiere autenticación para ver perfiles públicos
    permission_classes = []

    def get(self, request, nickname):
        actor_profile = request.user.profile if request.user.is_authenticated else None
        is_owner = actor_profile is not None and actor_profile.nickname == nickname

        if is_owner:
            profile = actor_profile
        else:
            # Solo perfiles visibles (no ermitaños).
            try:
                profile = Profile.objects.get(
                    nickname=nickname,
                    is_hermit_mode=False
                )
            except Profile.DoesNotExist:
                return Response(
                    {'error': 'Perfil no encontrado o no es público'},
                    status=status.HTTP_404_NOT_FOUND
                )

        highlights = Highlight.objects.filter(
            user=profile,
            visibility='public'
        ).select_related('book').prefetch_related('book__authors').annotate(
            comment_count=Count('comments', filter=Q(comments__status='approved'), distinct=True)
        ).order_by('-published_at', '-created_at')

        from .highlight_serializers import HighlightSerializer
        serializer = HighlightSerializer(highlights, many=True)
        return Response(serializer.data)


class HighlightCommentView(views.APIView):
    """
    Gestiona los comentarios de un highlight público.

    GET /api/highlights/<id>/comments/ -> Lista comentarios (Público si el highlight lo es)
    POST /api/highlights/<id>/comments/ -> Publica comentario (Requiere auth y valida permiso)
    """
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, highlight_id):
        try:
            highlight = get_highlight_or_error(highlight_id)
            actor_profile = request.user.profile if request.user.is_authenticated else None
            assert_can_view_comments(highlight, actor_profile=actor_profile)
        except CommentServiceError as exc:
            return Response(exc.detail, status=exc.status_code)

        # Solo mostrar comentarios aprobados
        comments = highlight.comments.filter(status='approved').select_related('author').order_by('created_at')
        serializer = CommentSerializer(comments, many=True)
        return Response(serializer.data)

    def post(self, request, highlight_id):
        actor_profile = request.user.profile if request.user.is_authenticated else None
        try:
            highlight = get_highlight_or_error(highlight_id)
            comment, notice = create_comment_for_highlight(
                highlight=highlight,
                actor_profile=actor_profile,
                content=request.data.get('content')
            )
        except CommentServiceError as exc:
            return Response(exc.detail, status=exc.status_code)

        serializer = CommentSerializer(comment)
        response_data = serializer.data
        if notice:
            response_data['notice'] = notice

        return Response(response_data, status=status.HTTP_201_CREATED)


class BookListView(views.APIView):
    """
    Lista los libros del usuario autenticado con conteo de highlights.

    GET /api/books/
    [
      {"id": 1, "title": "...", "authors": ["..."], "highlights_count": 42},
      ...
    ]
    Ordenados por highlights_count descendente.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        books = (
            Book.objects
            .filter(highlights__user=request.user.profile)
            .prefetch_related('authors')
            .annotate(highlights_count=Count('highlights', filter=Q(highlights__user=request.user.profile)))
            .order_by('-highlights_count')
        )
        data = [
            {
                'id': b.id,
                'title': b.title,
                'authors': [a.name for a in b.authors.all()],
                'highlights_count': b.highlights_count,
            }
            for b in books
        ]
        return Response(data)
