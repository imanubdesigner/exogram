"""
Constantes de la app Accounts.

Dominios de email bloqueados/permitidos y validación de dominio.
"""

# Blocked email domains (disposable email providers)
BLOCKED_EMAIL_DOMAINS = {
    'tempmail.com',
    '10minutemail.com',
    'guerrillamail.com',
    'mailinator.com',
    'throwaway.email',
    'maildrop.cc',
    'temp-mail.org',
    'yopmail.com',
    'sharklasers.com',
}

# Allowed email domains (optional whitelist - empty = allow all)
ALLOWED_EMAIL_DOMAINS = set()  # Por ahora permitimos todos


def is_email_domain_allowed(email: str) -> bool:
    """Valida que el dominio del email sea permitido."""
    domain = email.split('@')[1].lower()

    # Bloquear dominios disposables
    if domain in BLOCKED_EMAIL_DOMAINS:
        return False

    # Si hay whitelist, verificar que esté en ella
    if ALLOWED_EMAIL_DOMAINS and domain not in ALLOWED_EMAIL_DOMAINS:
        return False

    return True
