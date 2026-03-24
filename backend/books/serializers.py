from rest_framework import serializers

from .models import Author, Book, Note


class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = ['id', 'name', 'openlibrary_id']


class BookSerializer(serializers.ModelSerializer):
    authors = AuthorSerializer(many=True, read_only=True)

    class Meta:
        model = Book
        fields = [
            'id', 'title', 'authors', 'isbn', 'cover_image',
            'openlibrary_id', 'average_rating', 'publish_year', 'genre'
        ]


class NoteSerializer(serializers.ModelSerializer):
    """Serializador para notas tipo journal."""
    class Meta:
        model = Note
        fields = [
            'id', 'content', 'visibility', 'is_favorite',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
