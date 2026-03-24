"""
Management command: promueve automáticamente el nivel de confianza
de usuarios con >= 30 días de antigüedad que están en depth=0.

Modelo C: nivel de confianza progresivo.

Uso:
    python manage.py promote_trust_levels
    python manage.py promote_trust_levels --dry-run
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import Profile


class Command(BaseCommand):
    help = 'Promueve usuarios con 30+ días de antigüedad de comment_allowance_depth=0 a 1.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Muestra cuántos perfiles serían promovidos sin hacer cambios.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        cutoff_date = timezone.now() - timedelta(days=30)

        candidates = Profile.objects.filter(
            created_at__lte=cutoff_date,
            comment_allowance_depth=0,
            trust_promoted_at__isnull=True,
        )

        count = candidates.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS('No hay perfiles que promover.'))
            return

        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'[DRY RUN] {count} perfil(es) serían promovidos a depth=1.')
            )
            for profile in candidates[:20]:  # muestra hasta 20 como preview
                self.stdout.write(f'  - @{profile.nickname} (creado: {profile.created_at.date()})')
            return

        now = timezone.now()
        promoted = candidates.update(
            comment_allowance_depth=1,
            trust_promoted_at=now,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f'Promovidos: {promoted} perfil(es) → comment_allowance_depth=1.'
            )
        )
