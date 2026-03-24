from django.urls import path

from .views import DiscoverFeedView, FollowingFeedView

urlpatterns = [
    path('feed/', DiscoverFeedView.as_view(), name='discover_feed'),
    path('feed/following/', FollowingFeedView.as_view(), name='following_feed'),
]
