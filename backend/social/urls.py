from django.urls import path

from . import views
from .views import (
    CommentCreateView,
    CommentDeleteView,
    MyCommentsView,
)

urlpatterns = [
    # POST con highlight_id en body (usado desde panel de admin / integraciones)
    path('comments/', CommentCreateView.as_view(), name='comment_create'),
    path('comments/<int:comment_id>/', CommentDeleteView.as_view(), name='comment_delete'),
    path('me/comments/', MyCommentsView.as_view(), name='my_comments'),

    # Follow feature
    path('following/', views.FollowingUsersView.as_view(), name='following_users'),
    path('follow/<str:nickname>/', views.FollowUserView.as_view(), name='follow_user'),
    path('unfollow/<str:nickname>/', views.UnfollowUserView.as_view(), name='unfollow_user'),
    path('check-follow/<str:nickname>/', views.CheckFollowStatusView.as_view(), name='check_follow'),
]
