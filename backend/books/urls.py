from django.urls import path
from rest_framework.routers import DefaultRouter

from .card_views import QuoteCardView
from .export_views import BookMarkdownExportView, ObsidianExportView
from .highlight_views import (
    BookListView,
    HighlightCommentView,
    HighlightImportView,
    HighlightListView,
    HighlightUpdateView,
    HighlightUploadView,
    PublicHighlightListView,
)
from .note_views import NoteViewSet, PublicNoteListView
from .similarity_views import HighlightEmbeddingStatusView, SemanticSearchView, SimilarHighlightsView

# Router para NoteViewSet
router = DefaultRouter()
router.register(r'notes', NoteViewSet, basename='note')

urlpatterns = router.urls + [
    # Exportación de libros (Obsidian y Markdown)
    path('me/export/obsidian/', ObsidianExportView.as_view(), name='export_obsidian'),
    path('me/export/books/<int:book_id>/markdown/', BookMarkdownExportView.as_view(), name='export_book_markdown'),

    # Books
    path('books/', BookListView.as_view(), name='books_list'),

    # Highlights
    path('highlights/', HighlightListView.as_view(), name='highlights_list'),
    path('highlights/upload/', HighlightUploadView.as_view(), name='highlights_upload'),
    path('highlights/import/', HighlightImportView.as_view(), name='highlights_import'),
    path('highlights/search/', SemanticSearchView.as_view(), name='semantic_search'),
    path('highlights/<int:highlight_id>/', HighlightUpdateView.as_view(), name='highlight_update'),
    path('highlights/<int:highlight_id>/comments/', HighlightCommentView.as_view(), name='highlight_comments'),
    path('highlights/<int:highlight_id>/similar/', SimilarHighlightsView.as_view(), name='similar_highlights'),
    path('highlights/embedding-status/', HighlightEmbeddingStatusView.as_view(), name='embedding_status'),
    path('highlights/<int:highlight_id>/card/', QuoteCardView.as_view(), name='quote_card'),

    # Perfiles públicos: highlights y notas
    path('users/<str:nickname>/highlights/', PublicHighlightListView.as_view(), name='public_highlights'),
    path('users/<str:nickname>/notes/', PublicNoteListView.as_view(), name='public_notes'),
]
