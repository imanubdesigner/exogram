from collections import deque

from accounts.models import Profile


def invitation_distance(source_profile, target_profile, max_depth=None):
    """
    Retorna la distancia mínima en el árbol de invitaciones entre source y target.

    La distancia se calcula sobre un grafo no dirigido:
    - Arista hacia arriba: perfil -> invitador
    - Arista hacia abajo: perfil -> invitados directos

    Si no hay camino (o supera max_depth, si se pasa), retorna None.
    """
    if source_profile == target_profile:
        return 0

    queue = deque([(source_profile, 0)])
    visited = {source_profile.id}

    while queue:
        current, distance = queue.popleft()
        if max_depth is not None and distance >= max_depth:
            continue

        neighbors = []

        if current.invited_by_id and hasattr(current.invited_by, 'profile'):
            neighbors.append(current.invited_by.profile)

        children = Profile.objects.filter(invited_by=current.user).only('id', 'user_id', 'invited_by_id')
        neighbors.extend(children)

        for neighbor in neighbors:
            if neighbor.id in visited:
                continue
            next_distance = distance + 1
            if neighbor == target_profile:
                return next_distance
            visited.add(neighbor.id)
            queue.append((neighbor, next_distance))

    return None


def can_comment(owner_profile, commenter_profile):
    """
    Verifica si commenter_profile tiene permitido comentar en un highlight
    perteneciente a owner_profile, basado en comment_allowance_depth.

    Regla: puede comentar si está a una distancia <= allowance en el árbol
    de invitaciones del owner, navegando hacia arriba (invitador) y hacia
    abajo (invitados).
    """
    if owner_profile == commenter_profile:
        return True

    allowance = owner_profile.comment_allowance_depth
    if allowance <= 0:
        return False

    return invitation_distance(owner_profile, commenter_profile, max_depth=allowance) is not None


def are_in_same_network(profile_a, profile_b):
    """
    Verifica si dos usuarios pertenecen al mismo árbol de invitaciones,
    sin importar sus comment_allowance_depth individuales.

    Usado para threads: cualquier vínculo en la red habilita la conversación
    privada, independientemente del nivel de trust de cada uno.

    Retorna True si existe algún camino en el grafo de invitaciones.
    """
    if profile_a == profile_b:
        return False  # No se puede enviar un thread a uno mismo
    return invitation_distance(profile_a, profile_b) is not None
