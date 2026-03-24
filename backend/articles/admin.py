from django.contrib import admin

from .models import Article


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'placement', 'order', 'is_published', 'updated_at')
    list_filter = ('placement', 'is_published')
    prepopulated_fields = {'slug': ('title',)}
    search_fields = ('title', 'content')
