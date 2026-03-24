from rest_framework import serializers

from books.models import Highlight

from .models import ReadingSession


class SimilarReaderSerializer(serializers.Serializer):
    """
    Serializer para resultados de afinidad.
    Incluye libros en común para explicar por qué son afines.
    """
    nickname = serializers.CharField(source='profile.nickname')
    bio = serializers.CharField(source='profile.bio', default='')
    highlights_count = serializers.IntegerField()
    cluster_label = serializers.IntegerField(allow_null=True, default=None)
    similarity_score = serializers.FloatField(allow_null=True, default=None)
    common_books = serializers.SerializerMethodField()

    def get_common_books(self, obj):
        """
        Retorna los títulos de hasta 3 libros que tienen en común
        con el usuario que hace la consulta (pasado via context['request']).
        """
        request = self.context.get('request')
        if not request or not hasattr(request.user, 'profile'):
            return []

        my_profile = request.user.profile
        their_profile = obj.profile

        my_book_ids = set(
            Highlight.objects.filter(user=my_profile)
            .values_list('book_id', flat=True)
        )
        their_books = (
            Highlight.objects.filter(user=their_profile, book_id__in=my_book_ids)
            .values_list('book__title', flat=True)
        )

        # Deduplicar ignorando mayúsculas y espacios basura
        seen_normalized = set()
        unique_titles = []
        for title in their_books:
            if not title:
                continue
            norm = title.strip().lower()
            if norm not in seen_normalized:
                seen_normalized.add(norm)
                unique_titles.append(title.strip())

        return unique_titles[:3]


class ReadingSessionSerializer(serializers.ModelSerializer):
    """Serializer para sesiones de lectura."""
    reader_nickname = serializers.CharField(source='profile.nickname', read_only=True)
    book_title = serializers.CharField(source='book.title', read_only=True)
    book_authors = serializers.SerializerMethodField()

    class Meta:
        model = ReadingSession
        fields = [
            'id', 'reader_nickname', 'book_title', 'book_authors',
            'status', 'progress', 'started_at', 'finished_at'
        ]

    def get_book_authors(self, obj):
        return [a.name for a in obj.book.authors.all()]


class AlsoReadingSerializer(serializers.Serializer):
    """Serializer para 'María también lee X'."""
    nickname = serializers.CharField(source='profile.nickname')
    status = serializers.CharField()
    progress = serializers.FloatField()
