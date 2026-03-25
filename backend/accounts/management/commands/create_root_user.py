"""
Management command: crea un usuario raíz (nodo sin invitador).

El usuario creado:
- No tiene invited_by (nodo raíz del árbol de invitaciones).
- Tiene invitation_depth=0.
- Tiene must_change_credentials=True: debe definir nickname y contraseña
  en el primer login a través del flujo de onboarding existente.
- El nickname placeholder se actualiza en el onboarding vía
  UpdateCredentialsView (POST /api/me/credentials/update/).

Uso:
    python manage.py create_root_user --email usuario@ejemplo.com
    python manage.py create_root_user --email usuario@ejemplo.com --password contraseña_temporal
"""
import secrets
import smtplib
import string

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


def _generate_password(length=16):
    alphabet = string.ascii_letters + string.digits + '!@#$%^&*'
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def _generate_placeholder(prefix='root'):
    """Genera un username/nickname placeholder único basado en hex aleatorio."""
    return f'{prefix}_{secrets.token_hex(5)}'


class Command(BaseCommand):
    help = 'Crea un usuario raíz (sin invitador) listo para el onboarding.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            required=True,
            help='Email del nuevo usuario raíz.',
        )
        parser.add_argument(
            '--password',
            default=None,
            help='Contraseña temporal. Si se omite, se genera una aleatoria.',
        )

    def handle(self, *args, **options):
        email = options['email'].strip().lower()
        password = options['password'] or _generate_password()

        from accounts.models import Profile

        if Profile.objects.filter(verified_email=email).exists():
            raise CommandError(f'Ya existe un usuario con el email: {email}')

        placeholder = _generate_placeholder()

        while User.objects.filter(username=placeholder).exists():
            placeholder = _generate_placeholder()

        with transaction.atomic():
            user = User.objects.create_user(
                username=placeholder,
                password=password,
            )

            profile = user.profile
            profile.nickname = placeholder
            profile.verified_email = email
            profile.must_change_credentials = True
            profile.onboarding_completed = False
            profile.invited_by = None
            profile.invitation_depth = 0
            profile.save(update_fields=[
                'nickname',
                'verified_email',
                'must_change_credentials',
                'onboarding_completed',
                'invited_by',
                'invitation_depth',
                'updated_at',
            ])

        from accounts.emailing import send_root_user_credentials_email
        try:
            send_root_user_credentials_email(email=email, nickname=placeholder, password=password)
            email_status = self.style.SUCCESS('Email enviado correctamente.')
        except (smtplib.SMTPException, OSError) as exc:
            email_status = self.style.ERROR(f'No se pudo enviar el email: {exc}')

        self.stdout.write(self.style.SUCCESS('Usuario raíz creado exitosamente.'))
        self.stdout.write(f'  Email:      {email}')
        self.stdout.write(f'  Contraseña: {password}')
        self.stdout.write(email_status)
        self.stdout.write(
            self.style.WARNING(
                '  El usuario deberá definir su nickname y contraseña definitiva en el primer login.'
            )
        )
