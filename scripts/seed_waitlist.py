"""
Seed de lista de espera para desarrollo local.

Uso:
  python scripts/seed_waitlist.py

Env vars:
  WAITLIST_COUNT=25
  RESET_INVITES_NICKNAME=reader_philosophy
"""

from __future__ import annotations

import os
import random
import secrets
import sys
from pathlib import Path


def setup_django():
    repo_root = Path(__file__).resolve().parents[1]
    backend_dir = repo_root / 'backend'
    sys.path.insert(0, str(backend_dir))

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'exogram.settings')

    import django  # noqa: PLC0415

    django.setup()


def random_email():
    token = secrets.token_hex(6)
    return f'waitlist_{token}@example.com'


_MESSAGE_SNIPPETS = [
    'Me interesa participar y aprender con la comunidad.',
    'Quiero sumarme para leer, discutir y recomendar libros.',
    'Busco un espacio tranquilo para compartir notas y highlights.',
    'Me gustaría entrar para probar el producto y dar feedback.',
    'Vengo por las invitaciones y la red de lectura.',
]


def random_message():
    base = random.choice(_MESSAGE_SNIPPETS)
    suffix = secrets.token_hex(2)
    return f'{base} ({suffix})'


def run():
    setup_django()

    from django.conf import settings  # noqa: PLC0415
    from accounts.models import Invitation, Profile, Waitlist  # noqa: PLC0415

    count = int(os.environ.get('WAITLIST_COUNT', '25'))
    nickname = (os.environ.get('RESET_INVITES_NICKNAME') or 'reader_philosophy').strip()

    print(f'Creating {count} waitlist entries...')
    for _ in range(max(0, count)):
        Waitlist.objects.create(
            email=random_email(),
            message=random_message(),
        )

    if nickname:
        try:
            profile = Profile.objects.get(nickname=nickname)
        except Profile.DoesNotExist:
            print(f'Skipping invite reset; user @{nickname} not found.')
        else:
            deleted, _ = Invitation.objects.filter(invited_by=profile.user).delete()
            print(
                f'Deleted {deleted} invitations for @{nickname}. '
                f'Invites remaining: {profile.invitations_remaining}/{settings.MAX_INVITATIONS_PER_USER}.'
            )


if __name__ == '__main__':
    run()
