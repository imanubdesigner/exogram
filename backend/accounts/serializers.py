"""
Serializers de la app Accounts.

Profile, invitaciones, privacidad.
"""
from rest_framework import serializers

from books.models import Book

from .models import Invitation, Profile
from .validators import validate_nickname


class PublicProfileSerializer(serializers.ModelSerializer):
    """
    Serializador público: SOLO nickname, bio y avatar.

    NUNCA incluye:
    - Email
    - Nombre real
    - Sistema de invitaciones
    - Configuraciones de privacidad
    """
    class Meta:
        model = Profile
        fields = ['nickname', 'bio', 'avatar']


class PrivateProfileSerializer(serializers.ModelSerializer):
    """
    Serializador privado: datos completos del usuario autenticado.

    Solo accesible por el usuario dueño del perfil.
    """
    email = serializers.EmailField(source='verified_email', read_only=True)
    invited_by_nickname = serializers.SerializerMethodField()

    # Stats de lectura
    highlights_count = serializers.SerializerMethodField()
    books_count = serializers.SerializerMethodField()
    notes_count = serializers.SerializerMethodField()

    # Stats de invitaciones
    invitations_remaining = serializers.IntegerField(read_only=True)
    invitations_used_count = serializers.IntegerField(read_only=True)
    invitations_pending_count = serializers.IntegerField(read_only=True)
    invitations_expired_count = serializers.IntegerField(read_only=True)
    invitation_tree_depth = serializers.IntegerField(read_only=True)

    class Meta:
        model = Profile
        fields = [
            # Identidad pública (editable)
            'nickname', 'bio', 'avatar', 'goodreads_username',

            # Privacidad (editable)
            'is_hermit_mode', 'is_discoverable', 'comment_allowance_depth',

            # Metadata (solo lectura)
            'email', 'full_name', 'invited_by_nickname',

            # Stats de lectura (solo lectura)
            'highlights_count', 'books_count', 'notes_count',

            # Stats de invitaciones (solo lectura)
            'invitations_remaining', 'invitations_used_count',
            'invitations_pending_count', 'invitations_expired_count',
            'invitation_tree_depth',

            # Onboarding
            'onboarding_completed', 'must_change_credentials', 'discovery_activated_at',

            # Timestamps
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'email', 'full_name', 'invited_by_nickname',
            'highlights_count', 'books_count', 'notes_count',
            'invitations_remaining', 'invitations_used_count',
            'invitations_pending_count', 'invitations_expired_count',
            'invitation_tree_depth',
            'must_change_credentials',
            'discovery_activated_at', 'created_at', 'updated_at'
        ]

    def get_invited_by_nickname(self, obj):
        if obj.invited_by:
            return obj.invited_by.profile.nickname
        return 'Genesis User'

    def get_highlights_count(self, obj):
        return obj.highlights.count()

    def get_books_count(self, obj):
        return Book.objects.filter(highlights__user=obj).distinct().count()

    def get_notes_count(self, obj):
        return obj.notes.count()


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """Para actualizar solo campos editables por el usuario."""
    class Meta:
        model = Profile
        fields = ['nickname', 'bio', 'avatar', 'goodreads_username', 'comment_allowance_depth']

    def validate_nickname(self, value):
        validate_nickname(value)
        return value

    def validate_comment_allowance_depth(self, value):
        if value < 0 or value > 10:
            raise serializers.ValidationError('comment_allowance_depth debe estar entre 0 y 10')
        return value


class PrivacySettingsSerializer(serializers.ModelSerializer):
    """Para actualizar solo configuraciones de privacidad."""
    class Meta:
        model = Profile
        fields = ['is_hermit_mode', 'is_discoverable', 'comment_allowance_depth']

    def validate_comment_allowance_depth(self, value):
        if value < 0 or value > 10:
            raise serializers.ValidationError('comment_allowance_depth debe estar entre 0 y 10')
        return value


class InvitationSerializer(serializers.ModelSerializer):
    """Para listar invitaciones enviadas."""
    invited_by_nickname = serializers.CharField(source='invited_by.profile.nickname', read_only=True)
    created_user_nickname = serializers.SerializerMethodField()
    is_valid = serializers.BooleanField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = Invitation
        fields = [
            'id', 'email',
            'invited_by_nickname',
            'is_used', 'is_valid', 'is_expired',
            'created_user_nickname',
            'created_at', 'expires_at', 'used_at'
        ]
        read_only_fields = ['created_at', 'expires_at', 'used_at']

    def get_created_user_nickname(self, obj):
        if obj.created_user:
            return obj.created_user.profile.nickname
        return None


class SentInvitationSerializer(serializers.ModelSerializer):
    """
    Invitaciones enviadas por email por el usuario autenticado.

    No expone token para evitar re-distribución accidental desde el cliente.
    """
    invited_by_nickname = serializers.CharField(source='invited_by.profile.nickname', read_only=True)
    created_user_nickname = serializers.SerializerMethodField()
    created_user_must_change_credentials = serializers.SerializerMethodField()
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = Invitation
        fields = [
            'id',
            'email',
            'invited_by_nickname',
            'is_used',
            'is_expired',
            'created_user_nickname',
            'created_user_must_change_credentials',
            'created_at',
            'expires_at',
            'used_at',
        ]

    def get_created_user_nickname(self, obj):
        if obj.created_user and hasattr(obj.created_user, 'profile'):
            return obj.created_user.profile.nickname
        return None

    def get_created_user_must_change_credentials(self, obj):
        if obj.created_user and hasattr(obj.created_user, 'profile'):
            return bool(obj.created_user.profile.must_change_credentials)
        return None


class InvitedUserSerializer(serializers.ModelSerializer):
    """Lista de usuarios invitados directamente por el actor autenticado."""
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    invited_at = serializers.DateTimeField(source='created_at', read_only=True)

    class Meta:
        model = Profile
        fields = [
            'user_id',
            'nickname',
            'must_change_credentials',
            'invited_at',
        ]
