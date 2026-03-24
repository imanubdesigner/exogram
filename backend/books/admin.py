from django.contrib import admin

from accounts.models import Profile

from .models import Author, Book, Highlight


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ('name', 'openlibrary_id', 'created_at')
    search_fields = ('name',)
    list_filter = ('created_at',)


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'get_authors', 'isbn', 'publish_year', 'average_rating')
    search_fields = ('title', 'isbn')
    list_filter = ('publish_year', 'genre', 'created_at')
    filter_horizontal = ('authors',)

    def get_authors(self, obj):
        return ", ".join([a.name for a in obj.authors.all()[:3]])
    get_authors.short_description = 'Autores'


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_hermit_mode', 'is_discoverable', 'created_at')
    list_filter = ('is_hermit_mode', 'is_discoverable', 'created_at')
    search_fields = ('user__username', 'user__email')


@admin.register(Highlight)
class HighlightAdmin(admin.ModelAdmin):
    list_display = ('get_preview', 'book', 'user', 'visibility', 'created_at')
    list_filter = ('visibility', 'created_at', 'imported_at')
    search_fields = ('content', 'note', 'book__title', 'user__user__username')
    readonly_fields = ('embedding', 'imported_at')

    def get_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
    get_preview.short_description = 'Preview'
