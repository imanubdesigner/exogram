from django.conf import settings
from rest_framework import exceptions
from rest_framework.authentication import CSRFCheck
from rest_framework_simplejwt.authentication import JWTAuthentication


class CookieJWTAuthentication(JWTAuthentication):
    """
    JWT auth que acepta token en:
    1) Authorization header (compatibilidad)
    2) Cookie HttpOnly configurada en settings
    """

    @staticmethod
    def enforce_csrf(request):
        django_request = getattr(request, '_request', request)
        callback = getattr(getattr(django_request, 'resolver_match', None), 'func', None)

        # DRF marca todas las APIView como csrf_exempt a nivel Django; eso no
        # nos sirve porque acá queremos exigir CSRF para cookie-auth salvo en
        # endpoints que explícitamente optan por quedar exentos.
        callback_cls = getattr(callback, 'cls', None)
        if getattr(callback_cls, 'csrf_cookie_exempt', False):
            return

        check = CSRFCheck(lambda req: None)
        check.process_request(django_request)
        reason = check.process_view(django_request, None, (), {})
        if reason:
            raise exceptions.PermissionDenied(f'CSRF Failed: {reason}')

    def authenticate(self, request):
        header = self.get_header(request)
        token_from_cookie = False

        if header is not None:
            raw_token = self.get_raw_token(header)
        else:
            cookie_name = getattr(settings, 'JWT_ACCESS_COOKIE_NAME', 'access_token')
            raw_token = request.COOKIES.get(cookie_name)
            token_from_cookie = True

        if raw_token is None:
            return None

        validated_token = self.get_validated_token(raw_token)
        user = self.get_user(validated_token)

        if token_from_cookie and request.method in {'POST', 'PUT', 'PATCH', 'DELETE'}:
            # Aquí unimos explícitamente cookie-auth + CSRF: sin enforce_csrf DRF
            # asumiría auth no-cookie y omitiría esta validación.
            self.enforce_csrf(request)

        return user, validated_token
