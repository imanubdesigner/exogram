"""
Vistas de la app Social.

CRUD de comentarios con moderación automática pre-publicación.
"""
from rest_framework import generics, status, views
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Comment
from .serializers import CommentCreateSerializer, CommentSerializer
from .services import (
    CommentServiceError,
    assert_can_view_comments,
    create_comment_for_highlight,
    get_highlight_or_error,
)

DEPRECATION_WARNING = '299 - Deprecated endpoint. Use /api/highlights/<id>/comments/.'


class CommentCreateView(views.APIView):
    """
    Crea un comentario en un highlight público.

    POST /api/social/comments/
    {
        "highlight_id": 42,
        "content": "Gran reflexión sobre la ciencia"
    }

    El comentario pasa por moderación automática:
    - Score < 0.3 → aprobado automáticamente
    - Score 0.3-0.7 → pendiente de revisión
    - Score > 0.7 → rechazado automáticamente
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CommentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        highlight_id = serializer.validated_data['highlight_id']
        content = serializer.validated_data['content'].strip()

        try:
            highlight = get_highlight_or_error(highlight_id)
            comment, notice = create_comment_for_highlight(
                highlight=highlight,
                actor_profile=request.user.profile,
                content=content,
            )
        except CommentServiceError as exc:
            return Response(exc.detail, status=exc.status_code)

        response_data = CommentSerializer(comment).data
        if notice:
            response_data['notice'] = notice

        response = Response(response_data, status=status.HTTP_201_CREATED)
        response['Warning'] = DEPRECATION_WARNING
        return response


class HighlightCommentsView(generics.ListAPIView):
    """
    Lista comentarios aprobados de un highlight.

    GET /api/social/highlights/<id>/comments/
    """
    serializer_class = CommentSerializer

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        response['Warning'] = DEPRECATION_WARNING
        return response

    def get_queryset(self):
        try:
            highlight = get_highlight_or_error(self.kwargs['highlight_id'])
            actor_profile = self.request.user.profile if self.request.user.is_authenticated else None
            assert_can_view_comments(highlight, actor_profile=actor_profile)
        except CommentServiceError as exc:
            if exc.status_code == status.HTTP_404_NOT_FOUND:
                raise NotFound(exc.detail.get('error', 'Highlight no encontrado')) from exc
            raise PermissionDenied(exc.detail.get('error', 'No autorizado')) from exc

        return Comment.objects.filter(
            highlight=highlight,
            status='approved'
        ).select_related('author')


class MyCommentsView(generics.ListAPIView):
    """
    Lista todos mis comentarios (cualquier estado).

    GET /api/social/me/comments/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = CommentSerializer

    def get_queryset(self):
        return Comment.objects.filter(
            author=self.request.user.profile
        ).select_related('author', 'highlight')


class CommentDeleteView(views.APIView):
    """
    Elimina un comentario propio.

    DELETE /api/social/comments/<id>/
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request, comment_id):
        try:
            comment = Comment.objects.get(
                id=comment_id,
                author=request.user.profile
            )
        except Comment.DoesNotExist:
            return Response(
                {'error': 'Comentario no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )

        comment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class FollowUserView(views.APIView):
    """
    Sigue a un usuario dado su nickname.

    POST /api/social/follow/<nickname>/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, nickname):
        follower = request.user.profile

        # Validación de auto-follow
        if follower.nickname == nickname:
            return Response(
                {'error': 'No puedes seguirte a ti mismo'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            from accounts.models import Profile
            following = Profile.objects.get(nickname=nickname)
        except Profile.DoesNotExist:
            return Response(
                {'error': 'Usuario no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Hermit mode validation
        if following.is_hermit_mode:
            return Response(
                {'error': 'Este usuario no puede ser seguido'},
                status=status.HTTP_403_FORBIDDEN
            )

        from .models import UserFollow
        UserFollow.objects.get_or_create(follower=follower, following=following)

        return Response({'status': 'ok'})


class UnfollowUserView(views.APIView):
    """
    Deja de seguir a un usuario.

    POST /api/social/unfollow/<nickname>/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, nickname):
        follower = request.user.profile
        try:
            from accounts.models import Profile
            following = Profile.objects.get(nickname=nickname)
            from .models import UserFollow
            UserFollow.objects.filter(follower=follower, following=following).delete()
        except Profile.DoesNotExist:
            pass  # Idempotent operations are better

        return Response({'status': 'ok'})


class CheckFollowStatusView(views.APIView):
    """
    Verifica si el usuario actual sigue a <nickname>.

    GET /api/social/check-follow/<nickname>/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, nickname):
        follower = request.user.profile
        from .models import UserFollow
        is_following = UserFollow.objects.filter(
            follower=follower,
            following__nickname=nickname
        ).exists()

        return Response({'is_following': is_following})


class FollowingUsersView(views.APIView):
    """
    Lista de usuarios a los que sigo.
    GET /api/social/following/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        follower = request.user.profile
        from django.db.models import OuterRef, Subquery

        from accounts.models import Profile
        from books.models import Highlight

        latest_highlight_content = Highlight.objects.filter(
            user=OuterRef('pk'), visibility='public'
        ).order_by('-created_at').values('content')[:1]

        latest_book_title = Highlight.objects.filter(
            user=OuterRef('pk'), visibility='public'
        ).order_by('-created_at').values('book__title')[:1]

        # Filtramos por usuarios a los que seguimos y que no están en modo ermitaño
        following_profiles = Profile.objects.filter(
            followers__follower=follower,
            is_hermit_mode=False
        ).annotate(
            latest_highlight=Subquery(latest_highlight_content),
            latest_book=Subquery(latest_book_title)
        ).order_by('-followers__created_at')

        data = []
        for p in following_profiles:
            data.append({
                'nickname': p.nickname,
                'bio': p.bio,
                'latest_highlight': p.latest_highlight,
                'book_title': p.latest_book,
                'latest_book': p.latest_book,
            })

        return Response({'results': data})
