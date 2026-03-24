from django.conf import settings


class ContentSecurityPolicyMiddleware:
    """
    Agrega el header Content-Security-Policy a todas las respuestas HTML.

    En producción Caddy ya lo emite para la SPA y los endpoints API.
    Este middleware cubre el admin de Django y cualquier entorno sin Caddy
    (dev, tests de integración, etc.).
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.csp = getattr(settings, 'CONTENT_SECURITY_POLICY', None)

    def __call__(self, request):
        response = self.get_response(request)
        if self.csp and 'Content-Security-Policy' not in response:
            response['Content-Security-Policy'] = self.csp
        return response
