"""Vistas CRUD para notas tipo journal."""

from rest_framework import status, views, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import Profile

from .models import Note
from .serializers import NoteSerializer


class NoteViewSet(viewsets.ModelViewSet):
    """CRUD para notas del usuario autenticado."""

    serializer_class = NoteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Devuelve solo las notas del usuario autenticado."""
        return Note.objects.filter(user=self.request.user.profile).order_by('-created_at')

    def perform_create(self, serializer):
        """Asocia automáticamente la nota al usuario autenticado."""
        serializer.save(user=self.request.user.profile)

    @action(detail=True, methods=['post'])
    def toggle_favorite(self, request, pk=None):
        """Toggle is_favorite de una nota."""
        note = self.get_object()
        note.is_favorite = not note.is_favorite
        note.save()
        serializer = self.get_serializer(note)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def favorites(self, request):
        """Devuelve solo las notas marcadas como favoritas."""
        queryset = self.get_queryset().filter(is_favorite=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class PublicNoteListView(views.APIView):
    """
    Lista las notas públicas de un usuario específico.

    GET /api/users/<nickname>/notes/
    """
    permission_classes = []

    def get(self, request, nickname):
        actor_profile = request.user.profile if request.user.is_authenticated else None
        is_owner = actor_profile is not None and actor_profile.nickname == nickname

        if is_owner:
            profile = actor_profile
        else:
            try:
                profile = Profile.objects.get(
                    nickname=nickname,
                    is_hermit_mode=False
                )
            except Profile.DoesNotExist:
                return Response(
                    {'error': 'Perfil no encontrado o no es público'},
                    status=status.HTTP_404_NOT_FOUND
                )

        notes = Note.objects.filter(
            user=profile,
            visibility='public'
        ).order_by('-created_at')
        serializer = NoteSerializer(notes, many=True)
        return Response(serializer.data)
