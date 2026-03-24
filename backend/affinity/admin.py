from django.contrib import admin

from .models import ReadingSession, UserCluster


@admin.register(UserCluster)
class UserClusterAdmin(admin.ModelAdmin):
    list_display = ('profile', 'cluster_label', 'highlights_count', 'last_computed')
    list_filter = ('cluster_label', 'last_computed')
    search_fields = ('profile__nickname',)
    readonly_fields = ('centroid', 'last_computed')


@admin.register(ReadingSession)
class ReadingSessionAdmin(admin.ModelAdmin):
    list_display = ('profile', 'book', 'status', 'progress', 'started_at')
    list_filter = ('status', 'started_at')
    search_fields = ('profile__nickname', 'book__title')
