import hashlib
import hmac as _hmac
import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


def validate_avatar(image):
    """
    Valida tipo de imagen y tamaño máximo del avatar.

    La validación de Content-Type usa el header del cliente, que puede ser
    falseado. Se complementa con inspección de magic bytes del archivo real
    para evitar que se suban archivos disfrazados (p.ej. SVG con JS como PNG).

    SVG se rechaza explícitamente: aunque no coincide con ninguna firma de
    JPEG/PNG/WEBP, su detección explícita previene futuros falsos positivos
    si se agregan nuevos formatos o cambia la lógica de validación.
    """
    max_size_bytes = 2 * 1024 * 1024  # 2 MB

    if image.size > max_size_bytes:
        raise ValidationError('El avatar no puede superar los 2 MB.')

    # Leer los primeros 12 bytes para detectar el formato real
    image.seek(0)
    header = image.read(12)
    image.seek(0)

    # Rechazar SVG explícitamente (puede contener JS embebido → XSS)
    svg_signatures = (b'<svg', b'<?xml', b'<SVG')
    if any(header.lstrip()[:5].startswith(sig) for sig in svg_signatures):
        raise ValidationError('El avatar debe ser una imagen JPG, PNG o WEBP válida.')

    is_jpeg = header[:3] == b'\xff\xd8\xff'
    is_png = header[:8] == b'\x89PNG\r\n\x1a\n'
    # WebP: RIFF[4 bytes de tamaño]WEBP — los bytes 8-12 deben ser "WEBP"
    is_webp = header[:4] == b'RIFF' and header[8:12] == b'WEBP'

    if not (is_jpeg or is_png or is_webp):
        raise ValidationError('El avatar debe ser una imagen JPG, PNG o WEBP válida.')


INVITATION_TOKEN_TTL_HOURS = 72


class Invitation(models.Model):
    """
    Invitación para unirse a Exogram.

    Reglas estrictas:
    - Cada usuario puede enviar máximo 10 invitaciones
    - Las invitaciones expiradas CUENTAN contra el límite
    - No se pueden re-usar slots de invitaciones expiradas

    El token de activación (hash HMAC + timestamp) vive directamente en este
    modelo desde la migración 0007, eliminando la necesidad de InvitationToken
    como modelo separado. InvitationToken queda deprecado.
    """
    email = models.EmailField(unique=True, null=True, blank=True, verbose_name="Email invitado")
    invited_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_invitations',
        verbose_name="Invitado por"
    )
    token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        verbose_name="Token UUID (legacy)"
    )

    # Token de activación (reemplaza InvitationToken)
    token_hash = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        verbose_name="Hash HMAC del token de activación",
    )
    token_created_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Token creado el",
    )

    # Estado
    is_used = models.BooleanField(default=False, verbose_name="Usada")
    used_at = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de uso")
    created_user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invitation_received',
        verbose_name="Usuario creado"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(verbose_name="Expira el")

    class Meta:
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['token']),
            models.Index(fields=['invited_by', 'is_used']),
        ]
        verbose_name = "Invitación"
        verbose_name_plural = "Invitaciones"

    def __str__(self):
        status = "usada" if self.is_used else ("expirada" if self.is_expired else "pendiente")
        return f"{self.email} ({status})"

    @property
    def is_expired(self):
        """Verifica si la invitación expiró."""
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        """Verifica si la invitación es válida (no usada y no expirada)."""
        return not self.is_used and not self.is_expired

    @property
    def token_expires_at(self):
        """Expiración del token de activación (72 h desde su emisión)."""
        if not self.token_created_at:
            return None
        return self.token_created_at + timedelta(hours=INVITATION_TOKEN_TTL_HOURS)

    @property
    def is_token_expired(self):
        """True si el token de activación expiró o nunca fue emitido."""
        exp = self.token_expires_at
        return exp is None or timezone.now() >= exp

    @property
    def is_token_valid(self):
        """True si hay un token activo, no usado y no expirado."""
        return (
            self.token_hash is not None
            and self.used_at is None
            and not self.is_token_expired
        )

    def mark_as_used(self, user):
        """Marca la invitación como usada."""
        self.is_used = True
        self.used_at = timezone.now()
        self.created_user = user
        self.save(update_fields=['is_used', 'used_at', 'created_user'])

    def save(self, *args, **kwargs):
        # Auto-calcular expires_at si no está seteado
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=settings.INVITATION_EXPIRY_DAYS)
        super().save(*args, **kwargs)


def build_password_reset_token_hash(raw_token):
    """HMAC-SHA256 con SECRET_KEY como clave. Más seguro que SHA256 sin sal."""
    return _hmac.new(
        settings.SECRET_KEY.encode('utf-8'),
        raw_token.encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()


def build_invitation_token_hash(raw_token):
    """HMAC-SHA256 con SECRET_KEY como clave. Más seguro que SHA256 sin sal."""
    return _hmac.new(
        settings.SECRET_KEY.encode('utf-8'),
        raw_token.encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()


class InvitationToken(models.Model):
    token = models.CharField(
        max_length=64,
        unique=True,
        verbose_name='Hash del token',
    )
    email = models.EmailField(verbose_name='Email invitado')
    invited_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='invitation_tokens',
        verbose_name='Invitado por',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Usado el',
    )

    class Meta:
        indexes = [
            models.Index(fields=['email', 'invited_by']),
            models.Index(fields=['created_at']),
        ]
        verbose_name = 'Token de invitación'
        verbose_name_plural = 'Tokens de invitación'

    def __str__(self):
        status = 'usado' if self.used_at else ('expirado' if self.is_expired else 'pendiente')
        return f'{self.email} ({status})'

    @property
    def expires_at(self):
        return self.created_at + timedelta(hours=INVITATION_TOKEN_TTL_HOURS)

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    @property
    def is_valid(self):
        return self.used_at is None and not self.is_expired

    def mark_as_used(self):
        self.used_at = timezone.now()
        self.save(update_fields=['used_at'])


class PasswordResetToken(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='password_reset_tokens',
        verbose_name='Usuario',
    )
    token_hash = models.CharField(
        max_length=64,
        unique=True,
        verbose_name='Hash del token',
    )
    expires_at = models.DateTimeField(verbose_name='Expira el')
    used_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Usado el',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['expires_at']),
        ]
        verbose_name = 'Token de reseteo de contraseña'
        verbose_name_plural = 'Tokens de reseteo de contraseña'

    def __str__(self):
        status = 'usado' if self.used_at else ('expirado' if self.is_expired else 'pendiente')
        return f'{self.user_id} ({status})'

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    @property
    def is_valid(self):
        return self.used_at is None and not self.is_expired

    def mark_as_used(self):
        self.used_at = timezone.now()
        self.save(update_fields=['used_at'])


class Profile(models.Model):
    """Perfil extendido del usuario con sistema de invitaciones."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')

    # Identidad pública (ÚNICA visible en la red social)
    nickname = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Nickname",
        help_text="Tu identidad pública. Nadie verá tu email."
    )
    bio = models.TextField(
        max_length=500,
        blank=True,
        verbose_name="Biografía"
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        null=True,
        blank=True,
        validators=[validate_avatar],
        verbose_name="Avatar"
    )

    # Sistema de invitaciones
    invited_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invited_users',
        verbose_name="Invitado por"
    )
    invitation_used = models.ForeignKey(
        'Invitation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='profile_created',
        verbose_name="Invitación usada"
    )

    # Preferencias de privacidad
    comment_allowance_depth = models.IntegerField(
        default=2,
        verbose_name="Niveles permitidos para comentar",
        help_text="Niveles hacia arriba (invitadores) y abajo (invitados) "
                  "habilitados para comentar en tus highlights públicos."
    )
    is_hermit_mode = models.BooleanField(
        default=False,
        verbose_name="Modo Ermitaño",
        help_text="Si está activado, tu perfil público y tus highlights públicos no son visibles para terceros."
    )
    is_discoverable = models.BooleanField(
        default=True,
        verbose_name="Aparecer en feed de descubrimiento",
        help_text="Si está desactivado, no aparecés en sugerencias del feed ni verás la sección de descubrimiento."
    )

    # Metadata (NUNCA expuesta en API pública)
    verified_email = models.EmailField(
        verbose_name="Email verificado",
        help_text="Solo para admin/soporte. Nunca público."
    )
    full_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Nombre completo",
        help_text="Solo para admin/soporte. Nunca público."
    )

    # Onboarding
    onboarding_completed = models.BooleanField(
        default=False,
        verbose_name="Onboarding completado"
    )
    must_change_credentials = models.BooleanField(
        default=False,
        verbose_name="Debe cambiar credenciales",
        help_text="Si está activo, el usuario debe definir nickname y contraseña propios."
    )
    discovery_activated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Discovery activado el"
    )
    trust_promoted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Confianza promovida el",
        help_text="Fecha en que el sistema promovió automáticamente el nivel de confianza del usuario."
    )
    invitation_depth = models.IntegerField(
        default=0,
        verbose_name="Profundidad en árbol de invitaciones",
        help_text="0 = genesis/superuser. Calculado al crear el perfil."
    )

    # Preferencias de visualización
    font_scale = models.FloatField(
        default=1.0,
        verbose_name="Escala de fuente",
        help_text="Multiplicador del tamaño de fuente base. Rango: 0.85–1.3."
    )
    content_max_width = models.IntegerField(
        default=640,
        verbose_name="Ancho máximo del contenido (px)",
        help_text="Ancho máximo del contenedor principal. Rango: 480–900."
    )

    # Legacy / Integrations
    goodreads_username = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Usuario de Goodreads",
        help_text="Opcional. Tu nombre de usuario en Goodreads."
    )
    goodreads_feed_url = models.URLField(blank=True, verbose_name="URL de Goodreads RSS")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Perfil"
        verbose_name_plural = "Perfiles"
        indexes = [
            models.Index(fields=['nickname']),
        ]

    def __str__(self):
        return f"@{self.nickname}"

    @property
    def invitations_remaining(self):
        """
        Calcula cuántas invitaciones por email puede seguir emitiendo.

        Regla de negocio:
        - La cuota se consume al emitir la invitación (no al primer login).
        - Invitaciones expiradas también cuentan contra el límite.
        """
        sent_count = Invitation.objects.filter(invited_by=self.user).count()
        return max(0, settings.MAX_INVITATIONS_PER_USER - sent_count)

    @property
    def invitations_used_count(self):
        """Cuenta invitaciones efectivamente usadas."""
        return Invitation.objects.filter(invited_by=self.user, is_used=True).count()

    @property
    def invitations_pending_count(self):
        """Cuenta invitaciones no usadas y no expiradas."""
        now = timezone.now()
        return Invitation.objects.filter(
            invited_by=self.user,
            is_used=False,
            expires_at__gt=now,
        ).count()

    @property
    def invitations_expired_count(self):
        """Cuenta invitaciones no usadas y expiradas."""
        now = timezone.now()
        return Invitation.objects.filter(
            invited_by=self.user,
            is_used=False,
            expires_at__lte=now,
        ).count()

    @property
    def invitation_tree_depth(self):
        """
        Profundidad en el árbol de invitaciones (0 = genesis/superuser).

        Usa el campo denormalizado `invitation_depth` si está disponible.
        Fallback al recorrido recursivo para perfiles legacy creados antes
        de la migración que agregó el campo. El fallback carga el árbol
        completo en memoria con select_related para evitar N+1 queries.
        """
        if self.invitation_depth > 0:
            return self.invitation_depth
        if not self.invited_by_id:
            return 0

        # Fallback legacy: recorrer árbol con 1 query por nivel.
        # invited_by_id es el entero crudo del FK — no dispara query adicional.
        depth = 0
        current_user_id = self.invited_by_id
        seen = set()
        while current_user_id and depth <= 100:
            if current_user_id in seen:
                break  # Rompe ciclos inesperados en datos corruptos
            seen.add(current_user_id)
            try:
                ancestor = Profile.objects.only('invited_by_id').get(user_id=current_user_id)
            except Profile.DoesNotExist:
                break
            depth += 1
            current_user_id = ancestor.invited_by_id
        return depth


class Waitlist(models.Model):
    """
    Lista de espera para acceso a Exogram.

    Cualquiera puede anotarse. Un usuario con cuota disponible
    puede activar a alguien de la lista generándole credenciales temporales.
    """
    email = models.EmailField(unique=True, verbose_name="Email")
    message = models.TextField(
        max_length=500,
        blank=True,
        verbose_name="Por qué quiero unirme",
        help_text="Opcional. Contexto para quien decida activar la cuenta."
    )
    requested_at = models.DateTimeField(auto_now_add=True, verbose_name="Solicitado el")
    activated_by = models.ForeignKey(
        'Profile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='waitlist_activations',
        verbose_name="Activado por"
    )
    activated_at = models.DateTimeField(null=True, blank=True, verbose_name="Activado el")
    is_activated = models.BooleanField(default=False, verbose_name="Activado")

    class Meta:
        verbose_name = "Lista de espera"
        verbose_name_plural = "Lista de espera"
        ordering = ['requested_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['is_activated', 'requested_at']),
        ]

    def __str__(self):
        status = "activado" if self.is_activated else "pendiente"
        return f"{self.email} ({status})"

    def activate(self, by_profile):
        """Marca la entrada como activada."""
        self.is_activated = True
        self.activated_by = by_profile
        self.activated_at = timezone.now()
        self.save()
