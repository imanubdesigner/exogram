from django.contrib import admin

from .models import Comment, UserFollow


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('author', 'get_highlight_preview', 'status', 'toxicity_score', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('content', 'author__nickname')
    readonly_fields = ('toxicity_score', 'moderation_reason', 'moderated_at')
    actions = ['approve_comments', 'reject_comments']

    def get_highlight_preview(self, obj):
        return obj.highlight.content[:40] + '...'
    get_highlight_preview.short_description = 'Highlight'

    def approve_comments(self, request, queryset):
        for comment in queryset:
            comment.approve()
        self.message_user(request, f'{queryset.count()} comentarios aprobados.')
    approve_comments.short_description = 'Aprobar comentarios seleccionados'

    def reject_comments(self, request, queryset):
        for comment in queryset:
            comment.reject('Rechazado manualmente por admin')
        self.message_user(request, f'{queryset.count()} comentarios rechazados.')
    reject_comments.short_description = 'Rechazar comentarios seleccionados'


@admin.register(UserFollow)
class UserFollowAdmin(admin.ModelAdmin):
    list_display = ('follower', 'following', 'created_at')
    search_fields = ('follower__nickname', 'following__nickname')
    list_filter = ('created_at',)
