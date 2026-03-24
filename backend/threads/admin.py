from django.contrib import admin

from .models import Thread, ThreadMessage


@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    list_display = ['id', 'get_participants', 'context_book_title', 'last_message_at', 'created_at']
    list_filter = ['created_at']
    search_fields = ['participants__nickname', 'context_book_title']

    def get_participants(self, obj):
        return ', '.join(p.nickname for p in obj.participants.all())
    get_participants.short_description = 'Participantes'


@admin.register(ThreadMessage)
class ThreadMessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'thread', 'author', 'created_at']
    list_filter = ['created_at']
    raw_id_fields = ['thread', 'author']
