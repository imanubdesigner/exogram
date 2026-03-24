"""
Hasher rápido para tests/CI.

PBKDF2 con iterations=1 mantiene el algoritmo criptográficamente correcto
(SHA-256) pero elimina el coste de CPU que vuelve los tests lentos.
NO usar en producción.
"""
from django.contrib.auth.hashers import PBKDF2PasswordHasher


class FastPBKDF2PasswordHasher(PBKDF2PasswordHasher):
    iterations = 1
