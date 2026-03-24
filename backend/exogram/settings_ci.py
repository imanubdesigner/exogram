"""
Settings para CI/tests.

Extiende settings base y desactiva controles que vuelven inestable
la suite automatizada (throttling por rate limit).
"""
from .settings import *  # noqa: F401,F403,F405

# CI/test client usa host "testserver" en varias rutas.
ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'testserver']

# En tests de integración API, el throttling provoca falsos negativos (429).
REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # noqa: F405
    'DEFAULT_THROTTLE_CLASSES': [],
    # Mantener scopes definidos para views con throttle explícito, pero con
    # límites altos en CI para evitar falsos negativos por rate limiting.
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100000/hour',
        'user': '100000/hour',
        'default_user': '100000/hour',
        'chat_polling': '100000/hour',
        'auth': '100000/hour',
        'search': '100000/hour',
    },
}

# Acelera creación/login de usuarios en la suite.
# FastPBKDF2 mantiene PBKDF2-SHA256 pero con iterations=1 para velocidad.
# MD5PasswordHasher está roto criptográficamente; nunca usar, ni en CI.
PASSWORD_HASHERS = [
    'exogram.test_hashers.FastPBKDF2PasswordHasher',
]
