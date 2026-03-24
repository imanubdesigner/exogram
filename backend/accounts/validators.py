"""
Validadores personalizados para Exogram.

Incluye validaciones para emails, nicknames, contraseñas, etc.
"""

import re

from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator

from .constants import is_email_domain_allowed


class EmailDomainValidator:
    """Valida que el email no sea de un dominio disposable."""

    def __init__(self, message='Este dominio de email no está permitido'):
        self.message = message

    def __call__(self, value):
        """Valida el email."""
        if '@' not in value:
            raise ValidationError('Email inválido')

        if not is_email_domain_allowed(value):
            raise ValidationError(self.message)


class NicknameValidator:
    """Valida que el nickname cumpla con los requisitos."""

    def __init__(self):
        self.pattern = re.compile(r'^[a-zA-Z0-9_-]{3,50}$')
        self.message = 'El nickname debe tener 3-50 caracteres y contener solo letras, números, guiones y barras bajas'

    def __call__(self, value):
        """Valida el nickname."""
        if not self.pattern.match(value):
            raise ValidationError(self.message)

        # Prohibir palabras reservadas
        reserved_words = {'api', 'admin', 'auth', 'account', 'profile', 'settings'}
        if value.lower() in reserved_words:
            raise ValidationError(f'El nickname "{value}" está reservado')


class PasswordValidator:
    """Valida requisitos mínimos de contraseña."""

    def __init__(self):
        self.min_length = 8

    def __call__(self, value):
        """Valida la contraseña."""
        errors = []

        if len(value) < self.min_length:
            errors.append(f'Debe tener al menos {self.min_length} caracteres.')

        if not re.search(r'[A-Z]', value):
            errors.append('Debe incluir al menos una letra mayúscula.')

        if not re.search(r'\d', value):
            errors.append('Debe incluir al menos un número.')

        if errors:
            raise ValidationError(errors)


def validate_email_with_domain(email):
    """Combinación de validadores para email."""
    email_validator = EmailValidator()
    domain_validator = EmailDomainValidator()

    email_validator(email)
    domain_validator(email)


def validate_nickname(nickname):
    """Valida un nickname."""
    validator = NicknameValidator()
    validator(nickname)


def validate_password(password):
    """Valida una contraseña."""
    validator = PasswordValidator()
    validator(password)
