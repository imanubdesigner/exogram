import hmac
import logging
import re
import secrets
import smtplib
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.middleware.csrf import get_token
from django.utils import timezone
from rest_framework import generics, status, views
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from books.models import Highlight

from .emailing import send_invitation_email, send_password_reset_email
from .image_utils import sanitize_avatar

# InvitationToken se mantiene importado solo para compatibilidad con admin/serializers legacy.
# El flujo de invitaciones ya no crea InvitationToken — usa Invitation.token_hash directamente.
from .models import InvitationToken  # noqa: F401 — deprecado, no usar en lógica nueva
from .models import (
    INVITATION_TOKEN_TTL_HOURS,
    Invitation,
    PasswordResetToken,
    Profile,
    Waitlist,
    build_invitation_token_hash,
    build_password_reset_token_hash,
)
from .serializers import (
    DisplayPreferencesSerializer,
    PrivacySettingsSerializer,
    PrivateProfileSerializer,
    ProfileUpdateSerializer,
    PublicProfileSerializer,
    SentInvitationSerializer,
)
from .throttles import AuthThrottle
from .validators import validate_email_with_domain, validate_nickname, validate_password

logger = logging.getLogger(__name__)


def _cookie_max_age(delta):
    return int(delta.total_seconds())


def _invitation_expiry():
    return timezone.now() + timedelta(hours=INVITATION_TOKEN_TTL_HOURS)


def _set_auth_cookies(response, refresh_token):
    access_token = str(refresh_token.access_token)
    refresh_token_str = str(refresh_token)

    access_lifetime = settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME']
    refresh_lifetime = settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME']

    response.set_cookie(
        settings.JWT_ACCESS_COOKIE_NAME,
        access_token,
        max_age=_cookie_max_age(access_lifetime),
        httponly=True,
        secure=settings.JWT_COOKIE_SECURE,
        samesite=settings.JWT_COOKIE_SAMESITE,
        domain=settings.JWT_COOKIE_DOMAIN,
        path=settings.JWT_ACCESS_COOKIE_PATH,
    )
    response.set_cookie(
        settings.JWT_REFRESH_COOKIE_NAME,
        refresh_token_str,
        max_age=_cookie_max_age(refresh_lifetime),
        httponly=True,
        secure=settings.JWT_COOKIE_SECURE,
        samesite=settings.JWT_COOKIE_SAMESITE,
        domain=settings.JWT_COOKIE_DOMAIN,
        path=settings.JWT_REFRESH_COOKIE_PATH,
    )


def _clear_auth_cookies(response):
    response.delete_cookie(
        settings.JWT_ACCESS_COOKIE_NAME,
        path=settings.JWT_ACCESS_COOKIE_PATH,
        domain=settings.JWT_COOKIE_DOMAIN,
        samesite=settings.JWT_COOKIE_SAMESITE,
    )
    response.delete_cookie(
        settings.JWT_REFRESH_COOKIE_NAME,
        path=settings.JWT_REFRESH_COOKIE_PATH,
        domain=settings.JWT_COOKIE_DOMAIN,
        samesite=settings.JWT_COOKIE_SAMESITE,
    )


def _blacklist_refresh_token(raw_refresh):
    if not raw_refresh:
        return
    try:
        RefreshToken(raw_refresh).blacklist()
    except TokenError:
        # Token ya expirado o inválido — las cookies se limpian igual.
        logger.debug('No se pudo blacklistear refresh token (ya expirado o inválido)')


def _issue_email_invitation(inviter_user, email):
    normalized_email = (email or '').strip().lower()

    # El token se genera antes de la transacción para poder enviarlo por email
    # una vez que los locks de DB se hayan liberado (commit).
    raw_token = secrets.token_urlsafe(32)

    with transaction.atomic():
        locked_profile = Profile.objects.select_for_update().get(pk=inviter_user.profile.pk)
        invitation = (
            Invitation.objects.select_for_update()
            .filter(email=normalized_email)
            .first()
        )

        if invitation:
            if invitation.invited_by_id != inviter_user.id:
                raise ValueError('email_already_invited_by_other')
            if invitation.created_user_id or invitation.is_used:
                raise ValueError('email_already_active')
        elif locked_profile.invitations_remaining <= 0:
            raise ValueError('quota_exceeded')

        if (
            User.objects.filter(email__iexact=normalized_email).exists()
            or Profile.objects.filter(verified_email__iexact=normalized_email).exists()
        ):
            raise ValueError('email_already_active')

        created = invitation is None
        if created:
            try:
                invitation = Invitation.objects.create(
                    email=normalized_email,
                    invited_by=inviter_user,
                    expires_at=_invitation_expiry(),
                )
            except IntegrityError:
                raise ValueError('email_already_invited')

        invitation.expires_at = _invitation_expiry()
        # Actualizar el token de activación directamente en Invitation
        # (reemplaza la lógica que usaba InvitationToken como modelo separado).
        invitation.token_hash = build_invitation_token_hash(raw_token)
        invitation.token_created_at = timezone.now()
        invitation.save(update_fields=['expires_at', 'token_hash', 'token_created_at'])

    # El email se envía FUERA de la transacción: los locks de select_for_update
    # ya se liberaron al commitear. Enviar dentro del bloque atómico mantenía
    # los locks durante toda la conexión SMTP (5–30 s), bloqueando invitaciones
    # concurrentes al mismo perfil.
    send_invitation_email(
        invitation=invitation,
        raw_token=raw_token,
    )

    return invitation, created


class LoginView(views.APIView):
    """
    Login con nickname + password.

    POST /api/auth/login/
    {
        "nickname": "mi_nickname",
        "password": "contraseña"
    }

    IMPORTANTE: El email solo se usa en el registro inicial.
    El login siempre es con nickname.
    """
    permission_classes = [AllowAny]
    # Endpoints de auth llevan throttle estricto por seguridad (anti brute-force),
    # independiente de límites más relajados para polling de chat.
    throttle_classes = [AuthThrottle]

    def post(self, request):
        nickname = request.data.get('nickname')
        password = request.data.get('password')

        if not nickname or not password:
            return Response({
                'error': 'Nickname y contraseña son requeridos'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Buscar usuario por nickname
        try:
            profile = Profile.objects.get(nickname=nickname)
            user = profile.user
        except Profile.DoesNotExist:
            return Response({
                'error': 'Credenciales inválidas'
            }, status=status.HTTP_401_UNAUTHORIZED)

        # Autenticar con username (que es el email internamente)
        user = authenticate(username=user.username, password=password)
        if not user:
            logger.info('[AUTH] LOGIN_FAILURE nickname=%s', nickname)
            return Response({
                'error': 'Credenciales inválidas'
            }, status=status.HTTP_401_UNAUTHORIZED)

        refresh = RefreshToken.for_user(user)
        logger.info('[AUTH] LOGIN_SUCCESS user_id=%s nickname=%s', user.id, nickname)
        response = Response({
            'user': PrivateProfileSerializer(user.profile).data
        })
        _set_auth_cookies(response, refresh)
        # API-only backend: forzamos emisión de cookie CSRF en login para que el
        # frontend tenga token inmediato (sin depender de un GET con template).
        csrf_token = get_token(request)
        response.set_cookie(
            settings.CSRF_COOKIE_NAME,
            csrf_token,
            max_age=settings.CSRF_COOKIE_AGE,
            domain=settings.CSRF_COOKIE_DOMAIN,
            path=settings.CSRF_COOKIE_PATH,
            secure=settings.CSRF_COOKIE_SECURE,
            httponly=settings.CSRF_COOKIE_HTTPONLY,
            samesite=settings.CSRF_COOKIE_SAMESITE,
        )
        return response


class ForgotPasswordView(views.APIView):
    """
    Solicita restablecer la contraseña mediante email.
    """
    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]
    csrf_cookie_exempt = True

    def post(self, request):
        email = (request.data.get('email') or '').strip().lower()
        if not email:
            return Response(
                {'error': 'El email es requerido'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            validate_email_with_domain(email)
        except DjangoValidationError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        generic_message = (
            'Si ese email existe en nuestra base, te enviaremos instrucciones '
            'para restablecer la contraseña.'
        )
        # Usar verified_email como fuente autoritativa para evitar que un cambio
        # manual en user.email dirija el reset a una dirección no verificada.
        profile = Profile.objects.select_related('user').filter(
            verified_email__iexact=email
        ).first()
        user = profile.user if profile else None
        if not user:
            return Response({'message': generic_message}, status=status.HTTP_200_OK)

        logger.info('[AUTH] PASSWORD_RESET_REQUESTED user_id=%s', user.id)
        raw_token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(
            hours=getattr(settings, 'PASSWORD_RESET_TOKEN_TTL_HOURS', 2)
        )
        PasswordResetToken.objects.filter(user=user, used_at__isnull=True).delete()
        reset_token = PasswordResetToken.objects.create(
            user=user,
            token_hash=build_password_reset_token_hash(raw_token),
            expires_at=expires_at,
        )

        try:
            send_password_reset_email(
                user=user,
                reset_token=raw_token,
                expires_at=expires_at,
            )
        except (smtplib.SMTPException, OSError):
            reset_token.delete()
            logger.exception('No se pudo enviar email de restablecimiento para user_id=%s', user.id)

        return Response({'message': generic_message}, status=status.HTTP_200_OK)


class ResetPasswordView(views.APIView):
    """
    Completa el restablecimiento con token de un solo uso.
    """
    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]
    csrf_cookie_exempt = True

    def post(self, request):
        raw_token = (request.data.get('token') or '').strip()
        password = request.data.get('password') or ''
        password_confirm = request.data.get('password_confirm') or ''

        if not raw_token or not password or not password_confirm:
            return Response(
                {'error': 'Token, password y password_confirm son requeridos'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if password != password_confirm:
            return Response({'error': 'Las contraseñas no coinciden'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            validate_password(password)
        except DjangoValidationError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        token_hash = build_password_reset_token_hash(raw_token)
        reset_token = PasswordResetToken.objects.select_related('user', 'user__profile').filter(
            token_hash=token_hash
        ).first()
        if not reset_token or not hmac.compare_digest(reset_token.token_hash, token_hash) or not reset_token.is_valid:
            return Response(
                {'error': 'El enlace de restablecimiento es inválido o expiró'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            reset_token = PasswordResetToken.objects.select_for_update().select_related(
                'user'
            ).get(pk=reset_token.pk)
            if not reset_token.is_valid:
                return Response(
                    {'error': 'El enlace de restablecimiento es inválido o expiró'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user = reset_token.user
            user.set_password(password)
            user.save(update_fields=['password'])
            logger.info('[AUTH] PASSWORD_RESET_COMPLETED user_id=%s', user.id)

            profile = user.profile
            if profile.must_change_credentials:
                profile.must_change_credentials = False
                profile.save(update_fields=['must_change_credentials', 'updated_at'])

            reset_token.mark_as_used()
            PasswordResetToken.objects.filter(user=user, used_at__isnull=True).exclude(
                pk=reset_token.pk
            ).delete()

        for outstanding in OutstandingToken.objects.filter(user=user):
            _, _ = BlacklistedToken.objects.get_or_create(token=outstanding)

        return Response(
            {'message': 'Tu contraseña fue actualizada. Ya podés iniciar sesión.'},
            status=status.HTTP_200_OK,
        )


class TokenRefreshCookieView(views.APIView):
    """
    Refresca sesión JWT usando refresh token desde cookie HttpOnly.

    POST /api/auth/token/refresh/
    """
    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]

    def post(self, request):
        raw_refresh = request.data.get('refresh') or request.COOKIES.get(settings.JWT_REFRESH_COOKIE_NAME)
        if not raw_refresh:
            return Response({'error': 'Sesión expirada'}, status=status.HTTP_401_UNAUTHORIZED)

        serializer = TokenRefreshSerializer(data={'refresh': raw_refresh})
        if not serializer.is_valid():
            response = Response({'error': 'No se pudo refrescar la sesión'}, status=status.HTTP_401_UNAUTHORIZED)
            _clear_auth_cookies(response)
            return response

        access_token = serializer.validated_data.get('access')
        next_refresh = serializer.validated_data.get('refresh')

        response = Response({'status': 'refreshed'})

        response.set_cookie(
            settings.JWT_ACCESS_COOKIE_NAME,
            access_token,
            max_age=_cookie_max_age(settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME']),
            httponly=True,
            secure=settings.JWT_COOKIE_SECURE,
            samesite=settings.JWT_COOKIE_SAMESITE,
            domain=settings.JWT_COOKIE_DOMAIN,
            path=settings.JWT_ACCESS_COOKIE_PATH,
        )
        if next_refresh:
            response.set_cookie(
                settings.JWT_REFRESH_COOKIE_NAME,
                next_refresh,
                max_age=_cookie_max_age(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME']),
                httponly=True,
                secure=settings.JWT_COOKIE_SECURE,
                samesite=settings.JWT_COOKIE_SAMESITE,
                domain=settings.JWT_COOKIE_DOMAIN,
                path=settings.JWT_REFRESH_COOKIE_PATH,
            )
        return response


class LogoutView(views.APIView):
    """
    Cierra sesión y blanquea cookies.

    POST /api/auth/logout/
    """
    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]

    def post(self, request):
        raw_refresh = request.COOKIES.get(settings.JWT_REFRESH_COOKIE_NAME)
        _blacklist_refresh_token(raw_refresh)

        user = request.user
        if user and user.is_authenticated:
            logger.info('[AUTH] LOGOUT user_id=%s', user.id)
        response = Response({'status': 'logged_out'})
        _clear_auth_cookies(response)
        return response


class ValidateInvitationView(views.APIView):
    """
    Valida un token de invitación (link de invitación).

    GET /api/invitations/validate/<token>/
    """
    permission_classes = [AllowAny]
    # Throttle por IP: el token tiene 256 bits de entropía (brute force inviable),
    # pero aplicar el mismo límite que auth endpoints es consistente y elimina
    # cualquier abuso de enumeración del endpoint.
    throttle_classes = [AuthThrottle]

    def get(self, request, token):
        token_hash = build_invitation_token_hash(token)
        invitation = Invitation.objects.filter(token_hash=token_hash).first()
        if not invitation:
            return Response(
                {'valid': False, 'error': 'Token inválido o no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        if invitation.is_token_expired:
            return Response(
                {'valid': False, 'error': 'Esta invitación expiró'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response({
            'valid': True,
            'is_used': invitation.is_used,
            'email': invitation.email,
            'expires_at': invitation.token_expires_at.isoformat(),
        })


class AcceptInvitationView(views.APIView):
    """
    Acepta una invitación de un solo uso y crea la cuenta.

    POST /api/accounts/accept-invite/
    {
        "token": "...",
        "username": "mi_nickname",
        "password": "contraseña"
    }
    """
    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]
    csrf_cookie_exempt = True

    def post(self, request):
        raw_token = (request.data.get('token') or '').strip()
        username = (request.data.get('username') or '').strip()
        password = request.data.get('password') or ''

        if not raw_token or not username or not password:
            return Response(
                {'error': 'Token, username y password son requeridos'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            validate_nickname(username)
            validate_password(password)
        except DjangoValidationError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        token_hash = build_invitation_token_hash(raw_token)
        invitation = Invitation.objects.select_related('invited_by').filter(
            token_hash=token_hash
        ).first()
        if not invitation or not invitation.is_token_valid:
            return Response(
                {'error': 'El enlace de invitación es inválido o expiró'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            invitation = Invitation.objects.select_for_update().select_related(
                'invited_by',
            ).get(pk=invitation.pk)
            if not invitation.is_token_valid:
                return Response(
                    {'error': 'El enlace de invitación es inválido o expiró'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if Profile.objects.filter(nickname=username).exists() or User.objects.filter(username=username).exists():
                return Response(
                    {'error': 'Ese nickname ya está en uso'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if (
                User.objects.filter(email__iexact=invitation.email).exists()
                or Profile.objects.filter(verified_email__iexact=invitation.email).exists()
            ):
                return Response(
                    {'error': 'Ese email ya pertenece a un usuario activo'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            new_user = User.objects.create_user(
                username=username,
                email=invitation.email,
                password=password,
            )

            invited_profile = new_user.profile
            invited_profile.nickname = username
            invited_profile.invited_by = invitation.invited_by
            invited_profile.verified_email = invitation.email
            invited_profile.invitation_used = invitation
            invited_profile.must_change_credentials = False
            invited_profile.onboarding_completed = False
            invited_profile.comment_allowance_depth = 0
            invited_profile.invitation_depth = (
                invitation.invited_by.profile.invitation_depth + 1
                if hasattr(invitation.invited_by, 'profile')
                else 1
            )
            invited_profile.save(
                update_fields=[
                    'nickname',
                    'invited_by',
                    'verified_email',
                    'invitation_used',
                    'must_change_credentials',
                    'onboarding_completed',
                    'comment_allowance_depth',
                    'invitation_depth',
                    'updated_at',
                ]
            )

            invitation.mark_as_used(new_user)
            logger.info('[AUTH] INVITATION_ACCEPTED user_id=%s email=%s invited_by=%s',
                        new_user.id, invitation.email, invitation.invited_by_id)

        return Response(
            {'message': 'Tu invitación fue aceptada. Ya podés iniciar sesión.'},
            status=status.HTTP_201_CREATED,
        )


class RegisterView(views.APIView):
    """
    Endpoint legado: registro público deshabilitado.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        return Response({
            'error': 'El registro directo está deshabilitado. Pedí una invitación por email.'
        }, status=status.HTTP_410_GONE)


class SendInvitationView(views.APIView):
    """
    Envía invitación por email con link de activación.

    POST /api/invitations/send/
    {
        "email": "nuevo@correo.com"
    }

    Regla:
    - Cada usuario puede emitir hasta MAX_INVITATIONS_PER_USER invitaciones.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        profile = request.user.profile
        email = (request.data.get('email') or '').strip().lower()

        if profile.must_change_credentials:
            return Response(
                {'error': 'Debes actualizar tus credenciales antes de invitar a otros usuarios'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not email:
            return Response({'error': 'El email es requerido'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            validate_email_with_domain(email)
        except DjangoValidationError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            invitation, created = _issue_email_invitation(request.user, email)
        except ValueError as exc:
            if str(exc) == 'quota_exceeded':
                return Response(
                    {'error': f'Has alcanzado el límite de {settings.MAX_INVITATIONS_PER_USER} invitaciones'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if str(exc) in {'email_already_invited', 'email_already_invited_by_other'}:
                return Response(
                    {'error': 'Ese email ya fue invitado por otro usuario'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if str(exc) == 'email_already_active':
                return Response(
                    {'error': 'Ese email ya pertenece a un usuario activo'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(
                {'error': 'No se pudo crear/enviar la invitación por email'},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except (smtplib.SMTPException, OSError):
            logger.exception('No se pudo crear/enviar la invitación para email=%s', email)
            return Response(
                {'error': 'No se pudo crear/enviar la invitación por email'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        logger.info('[AUTH] INVITATION_SENT inviter_id=%s email=%s created=%s',
                    request.user.id, email, created)
        return Response({
            'message': 'Invitación enviada por email' if created else 'Invitación reenviada por email',
            'email': invitation.email,
            'invitations_remaining': profile.invitations_remaining
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class InvitationListView(views.APIView):
    """
    Lista invitaciones por email emitidas por el usuario autenticado.

    GET /api/invitations/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        invitations = (
            Invitation.objects
            .filter(invited_by=request.user)
            .select_related('created_user__profile')
            .order_by('-created_at')
        )
        serializer = SentInvitationSerializer(invitations, many=True)
        return Response(serializer.data)


class InvitationStatsView(views.APIView):
    """
    Estadísticas de invitaciones del usuario.

    GET /api/invitations/stats/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = request.user.profile
        invitations = (
            Invitation.objects
            .filter(invited_by=request.user)
            .select_related('created_user__profile')
            .order_by('-created_at')
        )
        total_sent = invitations.count()
        sent_data = SentInvitationSerializer(invitations[:25], many=True).data

        return Response({
            'total_sent': total_sent,
            'used': profile.invitations_used_count,
            'pending': profile.invitations_pending_count,
            'expired': profile.invitations_expired_count,
            'remaining': profile.invitations_remaining,
            'max_allowed': settings.MAX_INVITATIONS_PER_USER,
            'invitation_tree_depth': profile.invitation_tree_depth,
            'sent_invitations': sent_data,
        })


class ResetInvitedUserTempPasswordView(views.APIView):
    """
    Endpoint legacy deshabilitado.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, invited_user_id):
        return Response(
            {'error': 'Este flujo fue deshabilitado. Reenviá la invitación por email.'},
            status=status.HTTP_410_GONE
        )


# Vistas existentes de perfil
class CurrentUserView(generics.RetrieveAPIView):
    """
    Obtiene el perfil completo del usuario autenticado.

    GET /api/me/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = PrivateProfileSerializer

    def get_object(self):
        return self.request.user.profile


class CredentialsUpdateView(views.APIView):
    """
    Actualiza nickname y contraseña del usuario autenticado.

    POST /api/me/credentials/update/
    {
        "nickname": "nuevo_nickname",
        "password": "nueva_password",
        "password_confirm": "nueva_password"
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        profile = request.user.profile
        nickname = (request.data.get('nickname') or '').strip()
        password = request.data.get('password') or ''
        password_confirm = request.data.get('password_confirm') or ''

        if not nickname or not password or not password_confirm:
            return Response(
                {'error': 'Nickname, password y password_confirm son requeridos'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if password != password_confirm:
            return Response({'error': 'Las contraseñas no coinciden'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            validate_nickname(nickname)
            validate_password(password)
        except DjangoValidationError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        nickname_taken = Profile.objects.filter(nickname=nickname).exclude(user=request.user).exists()
        if nickname_taken:
            return Response({'error': 'Ese nickname ya está en uso'}, status=status.HTTP_400_BAD_REQUEST)

        username_taken = User.objects.filter(username=nickname).exclude(id=request.user.id).exists()
        if username_taken:
            return Response({'error': 'No se pudo usar ese nickname como username'}, status=status.HTTP_400_BAD_REQUEST)

        request.user.username = nickname
        request.user.set_password(password)
        request.user.save(update_fields=['username', 'password'])

        profile.nickname = nickname
        profile.must_change_credentials = False
        profile.save(update_fields=['nickname', 'must_change_credentials', 'updated_at'])

        old_refresh = request.COOKIES.get(settings.JWT_REFRESH_COOKIE_NAME)
        _blacklist_refresh_token(old_refresh)

        refresh = RefreshToken.for_user(request.user)
        response = Response({
            'message': 'Credenciales actualizadas',
            'user': PrivateProfileSerializer(profile).data,
        })
        _set_auth_cookies(response, refresh)
        return response


class ProfileUpdateView(generics.UpdateAPIView):
    """
    Actualiza el perfil del usuario autenticado.

    PATCH /api/me/profile/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ProfileUpdateSerializer

    def get_object(self):
        return self.request.user.profile

    def perform_update(self, serializer):
        previous_nickname = self.request.user.profile.nickname
        incoming_nickname = serializer.validated_data.get('nickname', previous_nickname)
        if incoming_nickname != previous_nickname and User.objects.filter(
            username=incoming_nickname
        ).exclude(id=self.request.user.id).exists():
            raise ValidationError({'nickname': 'No se pudo usar ese nickname como username'})

        # Re-codificar avatar para eliminar EXIF y metadatos antes de guardar.
        if 'avatar' in serializer.validated_data and serializer.validated_data['avatar']:
            serializer.validated_data['avatar'] = sanitize_avatar(
                serializer.validated_data['avatar']
            )

        profile = serializer.save()
        if profile.nickname != previous_nickname:
            self.request.user.username = profile.nickname
            self.request.user.save(update_fields=['username'])


class GoodreadsActivateView(views.APIView):
    """
    Activa la sincronización de Goodreads para el usuario autenticado.

    POST /api/me/goodreads/activate/
    {
        "goodreads_username": "1234567-maria"  # opcional si ya está guardado
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        profile = request.user.profile
        incoming_username = (request.data.get('goodreads_username') or '').strip()
        username = incoming_username or (profile.goodreads_username or '').strip()

        if not username:
            return Response(
                {'error': 'Debes configurar tu usuario de Goodreads antes de activar la sincronización'},
                status=status.HTTP_400_BAD_REQUEST
            )

        feed_url = self._build_goodreads_feed_url(username)

        profile.goodreads_username = username
        profile.goodreads_feed_url = feed_url or ''
        profile.save(update_fields=['goodreads_username', 'goodreads_feed_url', 'updated_at'])

        from books.goodreads_tasks import sync_goodreads_reading
        async_result = sync_goodreads_reading.delay(request.user.id)

        return Response(
            {
                'status': 'queued',
                'task_id': async_result.id,
                'goodreads_username': profile.goodreads_username,
                'goodreads_feed_url': profile.goodreads_feed_url,
            },
            status=status.HTTP_202_ACCEPTED
        )

    def _build_goodreads_feed_url(self, username: str):
        candidate = username.strip()
        if not candidate:
            return None

        # Caso recomendado: "1234567-maria" o "1234567"
        match_compact = re.match(r'^(\d+)(?:[-_].*)?$', candidate)
        if match_compact:
            user_id = match_compact.group(1)
            return f'https://www.goodreads.com/review/list_rss/{user_id}?shelf=read'

        # Caso URL completa de perfil
        match_url = re.search(r'/user/show/(\d+)', candidate)
        if match_url:
            user_id = match_url.group(1)
            return f'https://www.goodreads.com/review/list_rss/{user_id}?shelf=read'

        # Usernames/URLs sin ID explícito son válidos para scraping HTML,
        # aunque no permitan construir feed RSS directo.
        return None


class GoodreadsReadingView(views.APIView):
    """
    Retorna los libros actualmente en lectura sincronizados desde Goodreads.

    GET /api/me/goodreads/reading/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from affinity.models import ReadingSession

        sessions = (
            ReadingSession.objects
            .filter(profile=request.user.profile, status='reading')
            .select_related('book')
            .prefetch_related('book__authors')
            .order_by('-progress', 'book__title')
        )

        results = []
        for session in sessions:
            authors = [author.name for author in session.book.authors.all()]
            progress = max(0.0, min(1.0, float(session.progress or 0.0)))
            results.append({
                'book_id': session.book_id,
                'book_title': session.book.title,
                'book_authors': authors,
                'progress': progress,
                'progress_percent': int(round(progress * 100)),
                'status': session.status,
            })

        return Response({
            'results': results,
            'count': len(results),
        })


class PrivacySettingsView(generics.UpdateAPIView):
    """
    Actualiza solo configuraciones de privacidad.

    PATCH /api/me/privacy/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = PrivacySettingsSerializer

    def get_object(self):
        return self.request.user.profile


class DisplayPreferencesView(generics.UpdateAPIView):
    """
    Actualiza preferencias de visualización del usuario autenticado.

    PATCH /api/me/display/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = DisplayPreferencesSerializer

    def get_object(self):
        return self.request.user.profile


class PublicProfileView(generics.RetrieveAPIView):
    """
    Vista pública de un perfil por nickname.

    GET /api/users/<nickname>/
    """
    permission_classes = []  # No requiere autenticación
    serializer_class = PublicProfileSerializer
    lookup_field = 'nickname'

    def get_queryset(self):
        nickname = self.kwargs.get('nickname')
        user = getattr(self.request, 'user', None)
        is_owner = bool(
            user
            and user.is_authenticated
            and hasattr(user, 'profile')
            and user.profile.nickname == nickname
        )

        # El dueño puede ver su propio perfil público aunque esté en modo ermitaño.
        if is_owner:
            return Profile.objects.filter(nickname=nickname)

        return Profile.objects.filter(nickname=nickname, is_hermit_mode=False)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_onboarding(request):
    """
    Marca el onboarding como completado.

    POST /api/me/onboarding/complete/
    """
    profile = request.user.profile
    profile.onboarding_completed = True
    profile.save(update_fields=['onboarding_completed', 'updated_at'])

    return Response({
        'status': 'onboarding_completed',
        'profile': PrivateProfileSerializer(profile).data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_data(request):
    """
    Exporta todos los datos del usuario en formato JSON.

    GET /api/me/export/
    """
    profile = request.user.profile
    highlights = Highlight.objects.filter(user=profile)

    data = {
        'export_date': timezone.now().isoformat(),
        'profile': {
            'nickname': profile.nickname,
            'bio': profile.bio,
            'email': profile.verified_email,
            'full_name': profile.full_name,
            'is_hermit_mode': profile.is_hermit_mode,
            'is_discoverable': profile.is_discoverable,
            'created_at': profile.created_at.isoformat(),
            'invited_by': profile.invited_by.profile.nickname if profile.invited_by else 'Genesis User',
            'invitation_tree_depth': profile.invitation_tree_depth,
        },
        'invitations': {
            'sent': settings.MAX_INVITATIONS_PER_USER - profile.invitations_remaining,
            'used': profile.invitations_used_count,
            'pending': profile.invitations_pending_count,
            'expired': profile.invitations_expired_count,
            'remaining': profile.invitations_remaining,
        },
        'stats': {
            'total_highlights': highlights.count(),
            'total_books': highlights.values('book').distinct().count(),
        }
    }

    return Response(data)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_account(request):
    """
    Elimina COMPLETAMENTE la cuenta del usuario.

    DELETE /api/me/delete/

    ⚠️  HARD DELETE - No reversible

    Requiere confirmación:
    {
        "confirm": "DELETE_MY_ACCOUNT"
    }
    """
    confirmation = request.data.get('confirm', '')

    if confirmation != 'DELETE_MY_ACCOUNT':
        return Response({
            'error': 'Debes confirmar la eliminación con "DELETE_MY_ACCOUNT"'
        }, status=status.HTTP_400_BAD_REQUEST)

    user = request.user
    username = user.username
    user.delete()

    response = Response({
        'status': 'account_deleted',
        'message': f'Cuenta {username} eliminada permanentemente'
    }, status=status.HTTP_200_OK)
    _clear_auth_cookies(response)
    return response


class UserActivityView(views.APIView):
    """
    Retorna la actividad de lectura del usuario (highlights por día)
    para armar mapas de calor.
    GET /api/me/activity/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = request.user.profile

        # Agrupar highlights por fecha exacta (truncando horas/minutos)
        activity = (
            Highlight.objects.filter(user=profile)
            .annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(count=Count('id'))
            .order_by('date')
        )

        # Formatear salida
        data = [
            {
                "date": entry['date'].isoformat() if entry['date'] else None,
                "count": entry['count']
            }
            for entry in activity if entry['date']
        ]

        return Response(data)


class NetworkTreeView(views.APIView):
    """
    Retorna el árbol de invitaciones (nodos y arcos) para visualización en grafo.
    GET /api/me/network-tree/

    Limitado por profundidad y cantidad de nodos para evitar respuestas masivas.
    """
    permission_classes = [IsAuthenticated]
    DEFAULT_MAX_DEPTH = 4
    MAX_ALLOWED_DEPTH = 5   # Limitar para evitar enumeración masiva del grafo social
    DEFAULT_MAX_NODES = 180
    MAX_ALLOWED_NODES = 300  # Reducido de 1000 para limitar enumeración del grafo social

    def _parse_int_param(self, raw_value, *, default, min_value, max_value):
        try:
            parsed = int(raw_value)
        except (TypeError, ValueError):
            return default
        return max(min_value, min(parsed, max_value))

    def get(self, request):
        profile = request.user.profile
        max_depth = self._parse_int_param(
            request.query_params.get('max_depth'),
            default=self.DEFAULT_MAX_DEPTH,
            min_value=1,
            max_value=self.MAX_ALLOWED_DEPTH,
        )
        max_nodes = self._parse_int_param(
            request.query_params.get('max_nodes'),
            default=self.DEFAULT_MAX_NODES,
            min_value=10,
            max_value=self.MAX_ALLOWED_NODES,
        )
        truncated = False

        nodes = {}
        edges = {}

        # Nodo raíz (el usuario actual)
        nodes[profile.nickname] = {
            "name": profile.nickname,
            "is_root": True,
            "depth": 0,
            "avatar": request.build_absolute_uri(profile.avatar.url) if profile.avatar else None
        }

        def build_tree(current_user, current_nickname, depth):
            nonlocal truncated

            if depth >= max_depth:
                return

            invited_profiles = (
                Profile.objects
                .filter(invited_by=current_user)
                .select_related('user')
                .order_by('created_at')
            )

            for invited_profile in invited_profiles:
                invited_nickname = invited_profile.nickname

                # Prevenir ciclos
                if invited_nickname in nodes:
                    continue
                if len(nodes) >= max_nodes:
                    truncated = True
                    return

                nodes[invited_nickname] = {
                    "name": invited_nickname,
                    "is_root": False,
                    "depth": depth + 1,
                    "avatar": request.build_absolute_uri(invited_profile.avatar.url) if invited_profile.avatar else None
                }

                edge_id = f"edge_{current_nickname}_{invited_nickname}"
                edges[edge_id] = {
                    "source": current_nickname,
                    "target": invited_nickname
                }

                build_tree(invited_profile.user, invited_nickname, depth + 1)

        build_tree(request.user, profile.nickname, 0)

        return Response({
            "nodes": nodes,
            "edges": edges,
            "meta": {
                "max_depth": max_depth,
                "max_nodes": max_nodes,
                "truncated": truncated,
                "nodes_returned": len(nodes),
            },
        })


# ─── Modelo B: Tokens de invitación reutilizables ───────────────────────────

class CreateInvitationLinkView(views.APIView):
    """
    Endpoint legacy deshabilitado.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        return Response(
            {'error': 'Este flujo fue deshabilitado. Usá invitaciones por email.'},
            status=status.HTTP_410_GONE
        )


class RegisterByTokenView(views.APIView):
    """
    Endpoint legacy deshabilitado.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        return Response(
            {'error': 'Este flujo fue deshabilitado. Solicitá una invitación por email.'},
            status=status.HTTP_410_GONE
        )


# ─── Modelo A: Lista de espera ───────────────────────────────────────────────

class WaitlistView(views.APIView):
    """
    Lista de espera pública.

    POST /api/waitlist/ — anotar email (sin auth)
    GET  /api/waitlist/ — listar entradas (staff only)
    """
    permission_classes = [AllowAny]

    def post(self, request):
        email = (request.data.get('email') or '').strip().lower()
        message = (request.data.get('message') or '').strip()

        if not email:
            return Response({'error': 'El email es requerido'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            validate_email_with_domain(email)
        except DjangoValidationError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        if Waitlist.objects.filter(email=email).exists():
            # Idempotente: no revelamos si ya existe o no
            return Response({
                'message': 'Anotado. Te avisaremos cuando haya lugar.'
            }, status=status.HTTP_200_OK)

        Waitlist.objects.create(email=email, message=message[:500])
        return Response({
            'message': 'Anotado. Te avisaremos cuando haya lugar.'
        }, status=status.HTTP_201_CREATED)

    def get(self, request):
        if not request.user or not request.user.is_authenticated or not request.user.is_staff:
            return Response({'error': 'No autorizado'}, status=status.HTTP_403_FORBIDDEN)
        entries = Waitlist.objects.filter(is_activated=False).order_by('requested_at')
        data = [
            {
                'id': e.id,
                'email': e.email,
                'message': e.message,
                'requested_at': e.requested_at.isoformat(),
            }
            for e in entries
        ]
        return Response({'results': data, 'count': len(data)})


class WaitlistCommunityView(views.APIView):
    """
    Retorna la lista de espera de manera aleatoria y paginada
    para que la comunidad pueda invitar a los aspirantes.

    GET /api/waitlist/community/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        import hashlib

        from rest_framework.pagination import PageNumberPagination

        paginator = PageNumberPagination()
        paginator.page_size = 20

        # Orden pseudo-aleatorio pero estable por seed (evita duplicados entre páginas).
        seed = (request.query_params.get('seed') or '').strip()
        if not seed:
            seed = f"user:{request.user.id}"

        entries = list(
            Waitlist.objects
            .filter(is_activated=False)
            .values('id', 'message', 'requested_at')
        )
        entries.sort(
            key=lambda entry: hashlib.sha256(
                f"{seed}:{entry['id']}".encode('utf-8')
            ).hexdigest()
        )

        paginated_entries = paginator.paginate_queryset(entries, request)

        data = [
            {
                'id': e['id'],
                'message': e.get('message'),
                'requested_at': e['requested_at'].isoformat() if e.get('requested_at') else None,
            }
            for e in paginated_entries
        ]

        return paginator.get_paginated_response(data)


class WaitlistActivateView(views.APIView):
    """
    Activa una entrada de la lista de espera enviando invitación por email.

    POST /api/waitlist/<id>/activate/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, entry_id):
        profile = request.user.profile

        if profile.must_change_credentials:
            return Response(
                {'error': 'Debes actualizar tus credenciales antes de invitar a otros usuarios'},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Pre-check de cuota antes de adquirir lock de DB (evita round-trip innecesario
        # en el caso más común de falla). El check definitivo ocurre dentro de
        # _issue_email_invitation con select_for_update, por lo que no hay TOCTOU aquí.
        if profile.invitations_remaining <= 0:
            return Response(
                {'error': f'Has alcanzado el límite de {settings.MAX_INVITATIONS_PER_USER} invitaciones'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Lock atómico sobre la entrada de waitlist para prevenir doble activación
        # concurrente. Sin select_for_update, dos requests simultáneos al mismo
        # entry_id podían emitir dos invitaciones y consumir dos slots distintos.
        with transaction.atomic():
            try:
                entry = Waitlist.objects.select_for_update().get(id=entry_id, is_activated=False)
            except Waitlist.DoesNotExist:
                return Response({'error': 'Entrada no encontrada o ya activada'}, status=status.HTTP_404_NOT_FOUND)

            email = (entry.email or '').strip().lower()
            if not email:
                return Response({'error': 'La entrada no tiene email válido'}, status=status.HTTP_400_BAD_REQUEST)

            try:
                _, created = _issue_email_invitation(request.user, email)
            except ValueError as exc:
                if str(exc) == 'quota_exceeded':
                    return Response(
                        {'error': f'Has alcanzado el límite de {settings.MAX_INVITATIONS_PER_USER} invitaciones'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                if str(exc) in {'email_already_invited', 'email_already_invited_by_other'}:
                    return Response(
                        {'error': 'Ese email ya fue invitado por otro usuario'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                if str(exc) == 'email_already_active':
                    entry.activate(profile)
                    return Response({
                        'message': 'El email ya pertenece a un usuario activo',
                        'waitlist_email': email,
                        'invitations_remaining': profile.invitations_remaining,
                    }, status=status.HTTP_200_OK)
                return Response(
                    {'error': 'No se pudo crear/enviar la invitación por email'},
                    status=status.HTTP_502_BAD_GATEWAY,
                )
            except (smtplib.SMTPException, OSError):
                logger.exception('No se pudo activar waitlist para email=%s', email)
                return Response(
                    {'error': 'No se pudo crear/enviar la invitación por email'},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

            entry.activate(profile)

        return Response({
            'message': (
                'Invitación enviada desde lista de espera' if created
                else 'Invitación reenviada desde lista de espera'
            ),
            'waitlist_email': email,
            'invitations_remaining': profile.invitations_remaining,
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
