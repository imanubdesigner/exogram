from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.models import Profile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Crea automáticamente un Profile cuando se crea un User.

    El nickname temporal se reemplazará durante el onboarding.
    El perfil se guarda SOLO en la creación — no en cada save posterior,
    para evitar queries redundantes y posibles loops de signals.

    invitation_depth se completa al aceptar una invitación para evitar
    el recorrido O(N) del árbol en cada lectura. Genesis users = 0.
    """
    if created:
        Profile.objects.create(
            user=instance,
            nickname=f"user_{instance.id}",  # Temporal
            verified_email=instance.email,
            invitation_depth=0,  # Se actualiza al aceptar la invitación
        )
