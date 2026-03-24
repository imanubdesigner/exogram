from django.urls import path

from .views import ThreadDetailView, ThreadListCreateView, ThreadMessageCreateView

urlpatterns = [
    path('', ThreadListCreateView.as_view(), name='thread_list_create'),
    path('<int:thread_id>/', ThreadDetailView.as_view(), name='thread_detail'),
    path('<int:thread_id>/messages/', ThreadMessageCreateView.as_view(), name='thread_messages'),
]
