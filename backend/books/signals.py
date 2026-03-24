from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Highlight


@receiver(post_save, sender=Highlight, dispatch_uid='books.highlight.recalculate_centroid')
def enqueue_centroid_recalculation(sender, instance, raw=False, **kwargs):
    if raw:
        return

    # Siempre en background para no bloquear requests de API.
    from affinity.tasks import recalculate_user_centroid

    recalculate_user_centroid.delay(instance.user_id)
