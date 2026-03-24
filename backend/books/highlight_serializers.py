from rest_framework import serializers

from .models import Highlight


class HighlightSerializer(serializers.ModelSerializer):
    """Serializer para highlights en respuestas."""

    book_id = serializers.IntegerField(source='book.id', read_only=True)
    book_title = serializers.CharField(source='book.title', read_only=True)
    book_authors = serializers.SerializerMethodField()
    is_public = serializers.BooleanField(read_only=True)
    comment_count = serializers.SerializerMethodField()

    class Meta:
        model = Highlight
        fields = [
            'id', 'content', 'note', 'location',
            'visibility', 'is_public', 'created_at', 'imported_at', 'published_at',
            'book_id', 'book_title', 'book_authors', 'is_favorite', 'comment_count'
        ]
        read_only_fields = ['imported_at', 'published_at']

    def get_book_authors(self, obj):
        return [author.name for author in obj.book.authors.all()]

    def get_comment_count(self, obj):
        annotated = getattr(obj, 'comment_count', None)
        if annotated is not None:
            return int(annotated)
        return obj.comments.filter(status='approved').count()


class HighlightCreateSerializer(serializers.Serializer):
    """Serializer para crear highlights desde importación."""

    title = serializers.CharField(max_length=500)
    author = serializers.CharField(max_length=255)
    content = serializers.CharField()
    note = serializers.CharField(required=False, allow_blank=True, default='')
    location = serializers.CharField(max_length=50)
    created_at = serializers.DateTimeField()
    visibility = serializers.ChoiceField(
        choices=['private', 'unlisted', 'public'],
        default='private'
    )
    is_new = serializers.BooleanField(required=False, default=True)


class HighlightUploadResponseSerializer(serializers.Serializer):
    """Response del endpoint de upload/preview."""

    total_parsed = serializers.IntegerField()
    highlights = HighlightCreateSerializer(many=True)
    books_found = serializers.IntegerField()
    duplicates_detected = serializers.IntegerField()
    new_count = serializers.IntegerField()
    existing_count = serializers.IntegerField()


class HighlightImportResponseSerializer(serializers.Serializer):
    """Response del endpoint de import."""

    imported = serializers.IntegerField()
    skipped_duplicates = serializers.IntegerField()
    books_created = serializers.IntegerField()
    books_matched = serializers.IntegerField()


class CommentSerializer(serializers.ModelSerializer):
    """Serializer para comentarios devueltos."""
    author_nickname = serializers.CharField(source='author.nickname', read_only=True)
    author_avatar = serializers.ImageField(source='author.avatar', read_only=True)

    class Meta:
        from social.models import Comment
        model = Comment
        fields = ['id', 'content', 'created_at', 'author_nickname', 'author_avatar']
        read_only_fields = ['id', 'created_at', 'author_nickname', 'author_avatar']
