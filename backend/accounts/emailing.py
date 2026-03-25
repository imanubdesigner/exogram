from django.conf import settings
from django.core.mail import send_mail


def build_invitation_accept_url(token):
    base = getattr(settings, 'FRONTEND_BASE_URL', 'http://localhost:5173').rstrip('/')
    return f'{base}/accept-invite?token={token}'


def build_password_reset_url(token):
    base = getattr(settings, 'FRONTEND_BASE_URL', 'http://localhost:5173').rstrip('/')
    return f'{base}/reset-password?token={token}'


def send_invitation_email(*, invitation, raw_token):
    """
    Envía correo de invitación con enlace de activación de un solo uso.
    """
    inviter_nickname = invitation.invited_by.profile.nickname
    accept_url = build_invitation_accept_url(raw_token)

    subject = 'Tu invitación a Exogram'
    body = (
        f'Hola,\n\n'
        f'{inviter_nickname} te invitó a Exogram.\n\n'
        f'Usá este enlace de un solo uso para crear tu cuenta:\n'
        f'{accept_url}\n\n'
        f'Este enlace expira el: {invitation.expires_at.isoformat()}\n\n'
        f'Si no esperabas este correo, podés ignorarlo.'
    )

    send_mail(
        subject=subject,
        message=body,
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@exogram.local'),
        recipient_list=[invitation.email],
        fail_silently=False,
    )


def send_root_user_credentials_email(*, email, nickname, password):
    """
    Envía al usuario raíz recién creado sus credenciales temporales y
    el enlace al login para que complete el onboarding.
    """
    login_url = getattr(settings, 'FRONTEND_BASE_URL', 'http://localhost:5173').rstrip('/')

    subject = 'Bienvenido a Exogram — tus credenciales de acceso'
    body = (
        f'Hola,\n\n'
        f'Se creó una cuenta en Exogram para vos.\n\n'
        f'Tus credenciales temporales son:\n'
        f'  Nickname:   {nickname}\n'
        f'  Contraseña: {password}\n\n'
        f'Ingresá en:\n'
        f'{login_url}\n\n'
        f'Al iniciar sesión por primera vez se te pedirá que elijas un nickname '
        f'y una contraseña definitiva.\n\n'
        f'Si no esperabas este correo, podés ignorarlo.'
    )

    send_mail(
        subject=subject,
        message=body,
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@exogram.local'),
        recipient_list=[email],
        fail_silently=False,
    )


def send_password_reset_email(*, user, reset_token, expires_at):
    """
    Envía correo de restablecimiento con enlace de un solo uso.
    """
    nickname = user.profile.nickname
    reset_url = build_password_reset_url(reset_token)

    subject = 'Exogram — restablecé tu contraseña'
    body = (
        f'Hola {nickname},\n\n'
        f'Hiciste una solicitud para restablecer tu contraseña.\n\n'
        f'Usá este enlace de un solo uso para definir una nueva contraseña:\n'
        f'{reset_url}\n\n'
        f'El enlace expira el {expires_at.isoformat()}.\n\n'
        f'Si no pediste este cambio, podés ignorar este correo. '
        f'Tu contraseña actual no será modificada hasta que completes el formulario.'
    )

    # Enviar siempre al verified_email (fuente autoritativa), no a user.email.
    recipient = user.profile.verified_email or user.email
    send_mail(
        subject=subject,
        message=body,
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@exogram.local'),
        recipient_list=[recipient],
        fail_silently=False,
    )
