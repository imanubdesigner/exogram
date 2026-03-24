"""
Serializers de la app Social.
"""
from rest_framework import serializers

from .models import Comment


class CommentSerializer(serializers.ModelSerializer):
    """Serializer para comentarios aprobados (lectura)."""
    author_nickname = serializers.CharField(
        source='author.nickname',
        read_only=True
    )
    highlight_preview = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            'id', 'author_nickname', 'highlight',
            'highlight_preview', 'content', 'status',
            'created_at'
        ]
        read_only_fields = ['status', 'created_at']

    def get_highlight_preview(self, obj):
        return obj.highlight.content[:80] + '...' if len(obj.highlight.content) > 80 else obj.highlight.content


class CommentCreateSerializer(serializers.Serializer):
    """Serializer para crear un comentario."""
    highlight_id = serializers.IntegerField()
    content = serializers.CharField(max_length=1000)
