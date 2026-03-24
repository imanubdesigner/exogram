"""
Vistas de la app Threads.

Hilos privados entre lectores afines.
"""
from django.db.models import Prefetch
from rest_framework import status, views
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import Profile
from accounts.utils import are_in_same_network

from .models import Thread, ThreadMessage
from .throttles import ChatPollingThrottle

# ─── Helpers ────────────────────────────────────────────────────────────────


def _serialize_message(msg):
    return {
        'id': msg.id,
        'author': msg.author.nickname,
        'content': msg.content,
        'created_at': msg.created_at.isoformat(),
    }


def _serialize_thread(thread, my_profile):
    other = thread.get_other_participant(my_profile)
    # Usar cache de Prefetch si está disponible (evita N+1 en la lista).
    prefetched = getattr(thread, 'prefetched_messages', None)
    last_msg = prefetched[0] if prefetched else thread.messages.order_by('-created_at').first()
    return {
        'id': thread.id,
        'other_nickname': other.nickname if other else None,
        'other_bio': (other.bio[:100] if other and other.bio else ''),
        'context_book_title': thread.context_book_title,
        'last_message': _serialize_message(last_msg) if last_msg else None,
        'last_message_at': thread.last_message_at.isoformat() if thread.last_message_at else None,
        'created_at': thread.created_at.isoformat(),
    }


# ─── Vistas ──────────────────────────────────────────────────────────────────

class ThreadListCreateView(views.APIView):
    """
    Lista mis hilos o crea uno nuevo.

    GET  /api/threads/         → listar hilos donde soy participante
    POST /api/threads/         → crear hilo con otro usuario
    {
        "other_nickname": "fulano",
        "context_book_title": "El libro (opcional)"  # contexto de por qué se conectan
    }

    Restricción: solo se puede iniciar un hilo si los dos usuarios
    están dentro de la distancia de red permitida (igual que comentarios).
    Si ya existe un hilo entre ambos, se retorna el existente.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = request.user.profile
        threads = (
            Thread.objects
            .filter(participants=profile)
            .prefetch_related(
                'participants',
                Prefetch(
                    'messages',
                    queryset=ThreadMessage.objects.select_related('author').order_by('-created_at'),
                    to_attr='prefetched_messages',
                ),
            )
            .order_by('-last_message_at', '-created_at')
        )
        data = [_serialize_thread(t, profile) for t in threads]
        return Response({'results': data, 'count': len(data)})

    def post(self, request):
        profile = request.user.profile
        other_nickname = (request.data.get('other_nickname') or '').strip()
        context_book = (request.data.get('context_book_title') or '').strip()[:500]

        if not other_nickname:
            return Response(
                {'error': 'other_nickname es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if other_nickname == profile.nickname:
            return Response(
                {'error': 'No podés iniciar un hilo con vos mismo'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            other_profile = Profile.objects.get(nickname=other_nickname)
        except Profile.DoesNotExist:
            return Response(
                {'error': 'Usuario no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )

        if other_profile.is_hermit_mode:
            return Response(
                {'error': 'Este usuario no acepta mensajes'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Verificar que pertenecen a la misma red de invitaciones
        if not are_in_same_network(profile, other_profile):
            return Response(
                {'error': 'No pertenecen a la misma red. Solo podés chatear con lectores de tu árbol de invitaciones.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Si ya existe un hilo entre ambos, retornar el existente
        existing = Thread.objects.filter(
            participants=profile
        ).filter(
            participants=other_profile
        ).first()

        if existing:
            return Response(
                _serialize_thread(existing, profile),
                status=status.HTTP_200_OK
            )

        thread = Thread.objects.create(context_book_title=context_book)
        thread.participants.add(profile, other_profile)

        return Response(
            _serialize_thread(thread, profile),
            status=status.HTTP_201_CREATED
        )


class ThreadDetailView(views.APIView):
    """
    Detalle de un hilo: lista mensajes.

    GET  /api/threads/<id>/    → mensajes del hilo (paginación simple con ?before=<msg_id>)
    """
    permission_classes = [IsAuthenticated]

    def get_throttles(self):
        # GET de este endpoint se usa como polling continuo en el chat:
        # requiere un throttle más permisivo que operaciones mutables.
        if self.request.method == 'GET':
            return [ChatPollingThrottle()]
        return super().get_throttles()

    def _get_thread_or_403(self, thread_id, profile):
        try:
            thread = Thread.objects.prefetch_related('participants').get(id=thread_id)
        except Thread.DoesNotExist:
            return None, Response({'error': 'Hilo no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        if not thread.participants.filter(id=profile.id).exists():
            return None, Response({'error': 'No tenés acceso a este hilo'}, status=status.HTTP_403_FORBIDDEN)
        return thread, None

    def get(self, request, thread_id):
        profile = request.user.profile
        thread, err = self._get_thread_or_403(thread_id, profile)
        if err:
            return err

        # Paginación simple: últimos 50 mensajes, o desde before=<id>
        before_id = request.query_params.get('before')
        qs = thread.messages.select_related('author').order_by('created_at')
        if before_id:
            try:
                qs = qs.filter(id__lt=int(before_id))
            except (ValueError, TypeError):
                pass
        messages = list(qs.order_by('-created_at')[:50])
        messages.reverse()

        return Response({
            'thread': _serialize_thread(thread, profile),
            'messages': [_serialize_message(m) for m in messages],
            'count': len(messages),
        })


class ThreadMessageCreateView(views.APIView):
    """
    Envía un mensaje a un hilo.

    POST /api/threads/<id>/messages/
    { "content": "tu mensaje" }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, thread_id):
        profile = request.user.profile

        try:
            thread = Thread.objects.prefetch_related('participants').get(id=thread_id)
        except Thread.DoesNotExist:
            return Response({'error': 'Hilo no encontrado'}, status=status.HTTP_404_NOT_FOUND)

        if not thread.participants.filter(id=profile.id).exists():
            return Response({'error': 'No tenés acceso a este hilo'}, status=status.HTTP_403_FORBIDDEN)

        content = (request.data.get('content') or '').strip()
        if not content:
            return Response({'error': 'El contenido no puede estar vacío'}, status=status.HTTP_400_BAD_REQUEST)
        if len(content) > 2000:
            return Response(
                {'error': 'El mensaje no puede superar los 2000 caracteres'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        msg = ThreadMessage.objects.create(
            thread=thread,
            author=profile,
            content=content,
        )

        # Actualizar timestamp del hilo para ordenamiento
        thread.last_message_at = msg.created_at
        thread.save(update_fields=['last_message_at'])

        return Response(_serialize_message(msg), status=status.HTTP_201_CREATED)
