from django.urls import path

from .views import AlsoReadingView, MyClusterView, SimilarReadersView

urlpatterns = [
    path('similar-readers/', SimilarReadersView.as_view(), name='similar_readers'),
    path('also-reading/<int:book_id>/', AlsoReadingView.as_view(), name='also_reading'),
    path('me/cluster/', MyClusterView.as_view(), name='my_cluster'),
]
