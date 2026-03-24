from rest_framework import serializers

from .models import Article


class ArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = ['slug', 'title', 'subtitle', 'content', 'placement', 'created_at']
