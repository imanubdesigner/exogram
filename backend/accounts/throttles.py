from rest_framework.throttling import SimpleRateThrottle


class AuthThrottle(SimpleRateThrottle):
    """
    Throttle estricto para endpoints de autenticación sensibles.

    Usa la IP como clave de cache (igual que AnonRateThrottle) en lugar del
    user_id, porque la mayoría de estos endpoints los llaman usuarios que aún
    NO están autenticados (login, forgot-password, accept-invite).

    UserRateThrottle devuelve cache_key=None para usuarios anónimos, lo que
    significa que no los throttlea en absoluto. Este throttle siempre aplica,
    independientemente del estado de autenticación.
    """

    scope = 'auth'

    def get_cache_key(self, request, view):
        return self.cache_format % {
            'scope': self.scope,
            'ident': self.get_ident(request),
        }
