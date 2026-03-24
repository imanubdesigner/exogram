"""
Servicios compartidos para permisos y creación de comentarios.

Se utiliza desde `books.highlight_views` y `social.views` para evitar
duplicación de reglas de negocio.
"""
from typing import Optional, Tuple

from rest_framework import status

from accounts.utils import can_comment
from books.models import Highlight

from .models import Comment
from .moderation import moderate_comment


class CommentServiceError(Exception):
    def __init__(self, detail: dict, status_code: int):
        super().__init__(detail.get('error', 'Comment service error'))
        self.detail = detail
        self.status_code = status_code


def get_highlight_or_error(highlight_id: int) -> Highlight:
    try:
        return Highlight.objects.select_related('user').get(id=highlight_id)
    except Highlight.DoesNotExist as exc:
        raise CommentServiceError(
            detail={'error': 'Highlight no encontrado'},
            status_code=status.HTTP_404_NOT_FOUND
        ) from exc


def assert_can_view_comments(highlight: Highlight, actor_profile=None) -> bool:
    """
    Valida si se pueden listar comentarios de un highlight.

    Retorna si el actor es dueño del highlight.
    """
    is_owner = actor_profile is not None and highlight.user_id == actor_profile.id
    if highlight.visibility != 'public' and not is_owner:
        raise CommentServiceError(
            detail={'error': 'No autorizado para ver este highlight'},
            status_code=status.HTTP_403_FORBIDDEN
        )
    return is_owner


def create_comment_for_highlight(
    highlight: Highlight,
    actor_profile,
    content: Optional[str],
) -> Tuple[Comment, Optional[str]]:
    """
    Crea un comentario aplicando permisos, afinidad y moderación.

    Retorna `(comment, notice)` donde `notice` se usa para estado `pending`.
    """
    if actor_profile is None:
        raise CommentServiceError(
            detail={'error': 'Inicia sesión para comentar.'},
            status_code=status.HTTP_401_UNAUTHORIZED
        )

    clean_content = (content or '').strip()
    if not clean_content:
        raise CommentServiceError(
            detail={'error': 'El contenido no puede estar vacío'},
            status_code=status.HTTP_400_BAD_REQUEST
        )
    clean_content = clean_content[:1000]

    is_owner = highlight.user_id == actor_profile.id

    # Highlights privados: solo su dueño puede comentar (notas personales)
    if highlight.visibility != 'public' and not is_owner:
        raise CommentServiceError(
            detail={'error': 'No autorizado para comentar aquí'},
            status_code=status.HTTP_403_FORBIDDEN
        )

    # Modo ermitaño: bloquea comentarios externos
    if highlight.user.is_hermit_mode and not is_owner:
        raise CommentServiceError(
            detail={'error': 'Este usuario no acepta comentarios'},
            status_code=status.HTTP_403_FORBIDDEN
        )

    # Highlights públicos: validar afinidad/red para comentar.
    # No se exponen owner_comment_allowance_depth ni network_distance: permitirían
    # mapear el grafo social haciendo POST a distintos highlights y observando
    # los valores de cada respuesta.
    if highlight.visibility == 'public' and not is_owner and not can_comment(highlight.user, actor_profile):
        raise CommentServiceError(
            detail={'error': 'Tu nivel de relación en la red no te permite comentar en esta nota.'},
            status_code=status.HTTP_403_FORBIDDEN
        )

    # Dueño: nota personal aprobada en el acto. Terceros: moderación automática.
    if is_owner:
        mod_status, toxicity_score, reason = 'approved', 0.0, ''
    else:
        mod_status, toxicity_score, reason = moderate_comment(clean_content)

    if mod_status == 'rejected':
        raise CommentServiceError(
            detail={
                'error': 'Tu comentario fue rechazado por el filtro de moderación',
                'reason': reason
            },
            status_code=status.HTTP_400_BAD_REQUEST
        )

    comment = Comment.objects.create(
        highlight=highlight,
        author=actor_profile,
        content=clean_content,
        status=mod_status,
        toxicity_score=toxicity_score,
        moderation_reason=reason
    )
    notice = 'Tu comentario está pendiente de revisión' if mod_status == 'pending' else None
    return comment, notice
