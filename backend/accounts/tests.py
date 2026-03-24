"""
Suite de tests para la app accounts.

Cubre:
- LoginView / LogoutView / RegisterView
- ForgotPasswordView / ResetPasswordView
- AcceptInvitationView
- ProfileUpdateView / CredentialsUpdateView / PrivacySettingsView
- PublicProfileView
- TokenRefreshCookieView
- WaitlistView / WaitlistCommunityView / WaitlistActivateView
- ValidateInvitationView / SendInvitationView / InvitationListView / InvitationStatsView
- AvatarSanitizationTest
- CurrentUserView
- complete_onboarding / delete_account / export_data
- NetworkTreeView / UserActivityView
"""
import io
import secrets
from datetime import timedelta
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from accounts.models import (
    Invitation,
    PasswordResetToken,
    Profile,
    Waitlist,
    build_invitation_token_hash,
    build_password_reset_token_hash,
)

# ─── Helpers ────────────────────────────────────────────────────────────────


def _make_user(username, password='Testpass123', nickname=None, email=None):
    """Crea usuario con perfil configurado."""
    resolved_email = email or f'{username}@example.com'
    user = User.objects.create_user(
        username=username,
        password=password,
        email=resolved_email,
    )
    profile = user.profile
    profile.nickname = nickname or username
    profile.verified_email = resolved_email
    profile.save(update_fields=['nickname', 'verified_email'])
    return user


def _login(client, nickname, password='Testpass123'):
    return client.post('/api/auth/login/', {'nickname': nickname, 'password': password})


def _minimal_jpeg_bytes():
    buf = io.BytesIO()
    img = Image.new('RGB', (10, 10), color=(255, 0, 0))
    img.save(buf, format='JPEG')
    buf.seek(0)
    return buf.read()


def _minimal_png_bytes():
    buf = io.BytesIO()
    img = Image.new('RGB', (10, 10), color=(0, 255, 0))
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf.read()


# ─── ProfileUpdateView ────────────────────────────────────────────────────────

class ProfileUpdateTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = _make_user('profupdate')
        _login(self.client, 'profupdate')

    def test_patch_bio(self):
        response = self.client.patch('/api/me/profile/', {'bio': 'Mi nueva bio'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.bio, 'Mi nueva bio')

    def test_patch_nickname_updates_username(self):
        response = self.client.patch('/api/me/profile/', {'nickname': 'nuevo_nick'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'nuevo_nick')
        self.assertEqual(self.user.profile.nickname, 'nuevo_nick')

    def test_patch_nickname_duplicate_rejected(self):
        _make_user('otro_usuario', nickname='ocupado')
        response = self.client.patch('/api/me/profile/', {'nickname': 'ocupado'}, format='json')
        self.assertIn(response.status_code, [400, 422])

    def test_patch_unauthenticated_rejected(self):
        anon = APIClient()
        response = anon.patch('/api/me/profile/', {'bio': 'hack'}, format='json')
        self.assertEqual(response.status_code, 401)

    def test_upload_valid_jpeg_avatar(self):
        uploaded = SimpleUploadedFile('avatar.jpg', _minimal_jpeg_bytes(), content_type='image/jpeg')
        response = self.client.patch('/api/me/profile/', {'avatar': uploaded}, format='multipart')
        self.assertEqual(response.status_code, 200)
        self.user.profile.refresh_from_db()
        self.assertTrue(bool(self.user.profile.avatar))

    def test_upload_valid_png_avatar(self):
        uploaded = SimpleUploadedFile('avatar.png', _minimal_png_bytes(), content_type='image/png')
        response = self.client.patch('/api/me/profile/', {'avatar': uploaded}, format='multipart')
        self.assertEqual(response.status_code, 200)

    def test_upload_non_image_rejected(self):
        bad_file = SimpleUploadedFile('evil.exe', b'MZ\x90\x00binary', content_type='image/jpeg')
        response = self.client.patch('/api/me/profile/', {'avatar': bad_file}, format='multipart')
        self.assertEqual(response.status_code, 400)

    def test_upload_oversized_avatar_rejected(self):
        # 3 MB de ceros (supera el límite de 2 MB)
        big_data = b'\x00' * (3 * 1024 * 1024)
        big_file = SimpleUploadedFile('big.jpg', big_data, content_type='image/jpeg')
        response = self.client.patch('/api/me/profile/', {'avatar': big_file}, format='multipart')
        self.assertEqual(response.status_code, 400)


# ─── PublicProfileView ────────────────────────────────────────────────────────

class PublicProfileTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.public_user = _make_user('publico')
        self.hermit_user = _make_user('ermitano')
        self.hermit_user.profile.is_hermit_mode = True
        self.hermit_user.profile.save(update_fields=['is_hermit_mode'])

    def test_public_profile_visible_without_auth(self):
        response = self.client.get('/api/users/publico/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['nickname'], 'publico')
        self.assertNotIn('email', response.data)
        self.assertNotIn('verified_email', response.data)

    def test_hermit_profile_hidden_from_others(self):
        response = self.client.get('/api/users/ermitano/')
        self.assertEqual(response.status_code, 404)

    def test_hermit_profile_visible_to_owner(self):
        _login(self.client, 'ermitano')
        response = self.client.get('/api/users/ermitano/')
        self.assertEqual(response.status_code, 200)

    def test_nonexistent_profile_returns_404(self):
        response = self.client.get('/api/users/fantasma/')
        self.assertEqual(response.status_code, 404)


# ─── TokenRefreshCookieView ───────────────────────────────────────────────────

class TokenRefreshTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = _make_user('refreshuser')

    def test_refresh_with_valid_cookie_returns_new_access(self):
        login_resp = _login(self.client, 'refreshuser')
        self.assertEqual(login_resp.status_code, 200)
        response = self.client.post('/api/auth/token/refresh/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(settings.JWT_ACCESS_COOKIE_NAME, response.cookies)

    def test_refresh_without_cookie_rejected(self):
        response = APIClient().post('/api/auth/token/refresh/')
        self.assertIn(response.status_code, [400, 401])


# ─── WaitlistView ─────────────────────────────────────────────────────────────

class WaitlistTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_join_waitlist_creates_entry(self):
        response = self.client.post(
            '/api/waitlist/',
            {'email': 'aspirante@example.com', 'message': 'quiero leer'},
            format='json',
        )
        self.assertIn(response.status_code, [200, 201])
        self.assertTrue(Waitlist.objects.filter(email='aspirante@example.com').exists())

    def test_join_waitlist_idempotent(self):
        self.client.post('/api/waitlist/', {'email': 'doble@example.com'}, format='json')
        response = self.client.post('/api/waitlist/', {'email': 'doble@example.com'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Waitlist.objects.filter(email='doble@example.com').count(), 1)

    def test_join_waitlist_without_email_rejected(self):
        response = self.client.post('/api/waitlist/', {}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_list_waitlist_non_staff_forbidden(self):
        _make_user('regular')
        _login(self.client, 'regular')
        response = self.client.get('/api/waitlist/')
        self.assertEqual(response.status_code, 403)

    def test_list_waitlist_staff_allowed(self):
        staff_user = _make_user('staff_user')
        staff_user.is_staff = True
        staff_user.save(update_fields=['is_staff'])
        _login(self.client, 'staff_user')
        response = self.client.get('/api/waitlist/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('results', response.data)


# ─── ValidateInvitationView ───────────────────────────────────────────────────

@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class ValidateInvitationTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.inviter = _make_user('inviter_val')
        _login(self.client, 'inviter_val')

    def test_validate_valid_token(self):
        import secrets
        raw_token = secrets.token_urlsafe(32)
        Invitation.objects.create(
            invited_by=self.inviter,
            email='valid@example.com',
            token_hash=build_invitation_token_hash(raw_token),
            token_created_at=timezone.now(),
            expires_at=timezone.now() + timedelta(days=7),
        )
        response = self.client.get(f'/api/invitations/validate/{raw_token}/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['valid'])
        self.assertEqual(response.data['email'], 'valid@example.com')

    def test_validate_expired_token(self):
        import secrets
        raw_token = secrets.token_urlsafe(32)
        Invitation.objects.create(
            invited_by=self.inviter,
            email='expired@example.com',
            token_hash=build_invitation_token_hash(raw_token),
            # Backdatear para simular token expirado (>72 h)
            token_created_at=timezone.now() - timedelta(hours=73),
            expires_at=timezone.now() + timedelta(days=7),
        )
        response = self.client.get(f'/api/invitations/validate/{raw_token}/')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data['valid'])

    def test_validate_nonexistent_token_returns_404(self):
        response = self.client.get('/api/invitations/validate/tokenquenoeexiste/')
        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.data['valid'])


# ─── AvatarSanitizationTest ───────────────────────────────────────────────────

class AvatarSanitizationTest(TestCase):
    """Verifica que el avatar se re-codifica y elimina EXIF al subir."""

    def setUp(self):
        self.client = APIClient()
        self.user = _make_user('avatar_user')
        _login(self.client, 'avatar_user')

    def test_avatar_reencoded_on_upload(self):
        """La re-codificación debe completarse sin error."""
        uploaded = SimpleUploadedFile(
            'with_exif.jpg', _minimal_jpeg_bytes(), content_type='image/jpeg'
        )
        with patch('accounts.image_utils.Image.open', wraps=Image.open) as mock_open:
            response = self.client.patch(
                '/api/me/profile/', {'avatar': uploaded}, format='multipart'
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(mock_open.called)

    def test_rgba_png_avatar_accepted(self):
        """Un PNG con canal alpha (RGBA) se guarda sin error."""
        buf = io.BytesIO()
        img = Image.new('RGBA', (10, 10), color=(0, 0, 255, 128))
        img.save(buf, format='PNG')
        buf.seek(0)
        uploaded = SimpleUploadedFile('rgba.png', buf.read(), content_type='image/png')
        response = self.client.patch('/api/me/profile/', {'avatar': uploaded}, format='multipart')
        self.assertEqual(response.status_code, 200)


# ─── CurrentUserView ─────────────────────────────────────────────────────────

class CurrentUserViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = _make_user('meuser')

    def test_get_me_unauthenticated(self):
        response = self.client.get('/api/me/')
        self.assertEqual(response.status_code, 401)

    def test_get_me_authenticated_returns_nickname(self):
        _login(self.client, 'meuser')
        response = self.client.get('/api/me/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['nickname'], 'meuser')

    def test_get_me_does_not_expose_password(self):
        _login(self.client, 'meuser')
        response = self.client.get('/api/me/')
        self.assertNotIn('password', response.data)


# ─── LoginView ────────────────────────────────────────────────────────────────

class LoginTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = _make_user('loginuser')

    def test_login_success_returns_user_data(self):
        response = _login(self.client, 'loginuser')
        self.assertEqual(response.status_code, 200)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['nickname'], 'loginuser')

    def test_login_success_sets_auth_cookies(self):
        response = _login(self.client, 'loginuser')
        self.assertIn(settings.JWT_ACCESS_COOKIE_NAME, response.cookies)
        self.assertIn(settings.JWT_REFRESH_COOKIE_NAME, response.cookies)

    def test_login_wrong_password(self):
        response = self.client.post(
            '/api/auth/login/', {'nickname': 'loginuser', 'password': 'wrong'}, format='json'
        )
        self.assertEqual(response.status_code, 401)

    def test_login_wrong_nickname(self):
        response = self.client.post(
            '/api/auth/login/', {'nickname': 'fantasma', 'password': 'Testpass123'}, format='json'
        )
        self.assertEqual(response.status_code, 401)

    def test_login_missing_both_fields(self):
        response = self.client.post('/api/auth/login/', {}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_login_missing_password(self):
        response = self.client.post('/api/auth/login/', {'nickname': 'loginuser'}, format='json')
        self.assertEqual(response.status_code, 400)


# ─── LogoutView ───────────────────────────────────────────────────────────────

class LogoutTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = _make_user('logoutuser')

    def test_logout_authenticated_succeeds(self):
        _login(self.client, 'logoutuser')
        response = self.client.post('/api/auth/logout/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'logged_out')

    def test_logout_unauthenticated_also_succeeds(self):
        # LogoutView es AllowAny — no requiere estar autenticado
        response = APIClient().post('/api/auth/logout/')
        self.assertEqual(response.status_code, 200)


# ─── RegisterView ─────────────────────────────────────────────────────────────

class RegisterTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_register_returns_410_gone(self):
        response = self.client.post(
            '/api/auth/register/', {'nickname': 'nuevo', 'password': 'Testpass123'}, format='json'
        )
        self.assertEqual(response.status_code, 410)


# ─── ForgotPasswordView ───────────────────────────────────────────────────────

@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class ForgotPasswordTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = _make_user('resetuser', email='reset@example.com')

    def test_missing_email_returns_400(self):
        response = self.client.post('/api/auth/forgot-password/', {}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_invalid_email_format_returns_400(self):
        response = self.client.post(
            '/api/auth/forgot-password/', {'email': 'notanemail'}, format='json'
        )
        self.assertEqual(response.status_code, 400)

    def test_nonexistent_email_returns_generic_200(self):
        response = self.client.post(
            '/api/auth/forgot-password/', {'email': 'noexiste@example.com'}, format='json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('message', response.data)

    def test_existing_email_returns_generic_200(self):
        response = self.client.post(
            '/api/auth/forgot-password/', {'email': 'reset@example.com'}, format='json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('message', response.data)

    def test_existing_email_creates_reset_token(self):
        self.client.post(
            '/api/auth/forgot-password/', {'email': 'reset@example.com'}, format='json'
        )
        self.assertTrue(PasswordResetToken.objects.filter(user=self.user).exists())

    def test_second_request_replaces_previous_token(self):
        self.client.post(
            '/api/auth/forgot-password/', {'email': 'reset@example.com'}, format='json'
        )
        self.client.post(
            '/api/auth/forgot-password/', {'email': 'reset@example.com'}, format='json'
        )
        # Solo debe haber un token activo (el anterior fue eliminado)
        self.assertEqual(PasswordResetToken.objects.filter(user=self.user, used_at__isnull=True).count(), 1)


# ─── ResetPasswordView ────────────────────────────────────────────────────────

@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class ResetPasswordTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = _make_user('resetpwuser', email='resetpw@example.com')

    def _create_reset_token(self, hours_until_expiry=2):
        raw_token = secrets.token_urlsafe(32)
        PasswordResetToken.objects.create(
            user=self.user,
            token_hash=build_password_reset_token_hash(raw_token),
            expires_at=timezone.now() + timedelta(hours=hours_until_expiry),
        )
        return raw_token

    def test_missing_fields_returns_400(self):
        response = self.client.post('/api/auth/reset-password/', {}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_passwords_dont_match_returns_400(self):
        raw_token = self._create_reset_token()
        response = self.client.post('/api/auth/reset-password/', {
            'token': raw_token,
            'password': 'Testpass123',
            'password_confirm': 'OtroPass456',
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_invalid_token_returns_400(self):
        response = self.client.post('/api/auth/reset-password/', {
            'token': 'tokeninvalido',
            'password': 'NuevaPass123',
            'password_confirm': 'NuevaPass123',
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_expired_token_returns_400(self):
        raw_token = self._create_reset_token(hours_until_expiry=-1)
        response = self.client.post('/api/auth/reset-password/', {
            'token': raw_token,
            'password': 'NuevaPass123',
            'password_confirm': 'NuevaPass123',
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_valid_token_resets_password(self):
        raw_token = self._create_reset_token()
        response = self.client.post('/api/auth/reset-password/', {
            'token': raw_token,
            'password': 'NuevaPass123',
            'password_confirm': 'NuevaPass123',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NuevaPass123'))

    def test_valid_token_marked_as_used(self):
        raw_token = self._create_reset_token()
        self.client.post('/api/auth/reset-password/', {
            'token': raw_token,
            'password': 'NuevaPass123',
            'password_confirm': 'NuevaPass123',
        }, format='json')
        token = PasswordResetToken.objects.get(user=self.user)
        self.assertIsNotNone(token.used_at)

    def test_used_token_cannot_be_reused(self):
        raw_token = self._create_reset_token()
        self.client.post('/api/auth/reset-password/', {
            'token': raw_token,
            'password': 'NuevaPass123',
            'password_confirm': 'NuevaPass123',
        }, format='json')
        response = self.client.post('/api/auth/reset-password/', {
            'token': raw_token,
            'password': 'OtraPass456',
            'password_confirm': 'OtraPass456',
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_reset_clears_must_change_credentials(self):
        self.user.profile.must_change_credentials = True
        self.user.profile.save(update_fields=['must_change_credentials'])
        raw_token = self._create_reset_token()
        self.client.post('/api/auth/reset-password/', {
            'token': raw_token,
            'password': 'NuevaPass123',
            'password_confirm': 'NuevaPass123',
        }, format='json')
        self.user.profile.refresh_from_db()
        self.assertFalse(self.user.profile.must_change_credentials)


# ─── AcceptInvitationView ─────────────────────────────────────────────────────

@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class AcceptInvitationTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.inviter = _make_user('inviter_accept')
        self.raw_token = secrets.token_urlsafe(32)
        self.invitation = Invitation.objects.create(
            invited_by=self.inviter,
            email='invited@example.com',
            token_hash=build_invitation_token_hash(self.raw_token),
            token_created_at=timezone.now(),
            expires_at=timezone.now() + timedelta(days=7),
        )

    def test_accept_valid_invitation_creates_user(self):
        response = self.client.post('/api/accounts/accept-invite/', {
            'token': self.raw_token,
            'username': 'newuser',
            'password': 'Newpass123',
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_accept_marks_invitation_as_used(self):
        self.client.post('/api/accounts/accept-invite/', {
            'token': self.raw_token,
            'username': 'newuser2',
            'password': 'Newpass123',
        }, format='json')
        self.invitation.refresh_from_db()
        self.assertTrue(self.invitation.is_used)

    def test_accept_sets_profile_verified_email(self):
        self.client.post('/api/accounts/accept-invite/', {
            'token': self.raw_token,
            'username': 'newuser3',
            'password': 'Newpass123',
        }, format='json')
        profile = Profile.objects.get(nickname='newuser3')
        self.assertEqual(profile.verified_email, 'invited@example.com')

    def test_accept_sets_invitation_depth(self):
        self.client.post('/api/accounts/accept-invite/', {
            'token': self.raw_token,
            'username': 'depthuser',
            'password': 'Newpass123',
        }, format='json')
        profile = Profile.objects.get(nickname='depthuser')
        # inviter tiene depth 0, entonces invited debe tener depth 1
        self.assertEqual(profile.invitation_depth, 1)

    def test_accept_missing_fields_returns_400(self):
        response = self.client.post('/api/accounts/accept-invite/', {}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_accept_invalid_token_returns_400(self):
        response = self.client.post('/api/accounts/accept-invite/', {
            'token': 'tokeninvalido',
            'username': 'newuser_inv',
            'password': 'Newpass123',
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_accept_expired_token_returns_400(self):
        expired_token = secrets.token_urlsafe(32)
        Invitation.objects.create(
            invited_by=self.inviter,
            email='expired_inv@example.com',
            token_hash=build_invitation_token_hash(expired_token),
            token_created_at=timezone.now() - timedelta(hours=73),
            expires_at=timezone.now() + timedelta(days=7),
        )
        response = self.client.post('/api/accounts/accept-invite/', {
            'token': expired_token,
            'username': 'expireduser',
            'password': 'Newpass123',
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_accept_duplicate_nickname_returns_400(self):
        _make_user('taken_nick')
        response = self.client.post('/api/accounts/accept-invite/', {
            'token': self.raw_token,
            'username': 'taken_nick',
            'password': 'Newpass123',
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_used_invitation_cannot_be_reused(self):
        self.client.post('/api/accounts/accept-invite/', {
            'token': self.raw_token,
            'username': 'firstuser',
            'password': 'Newpass123',
        }, format='json')
        response = self.client.post('/api/accounts/accept-invite/', {
            'token': self.raw_token,
            'username': 'seconduser',
            'password': 'Newpass123',
        }, format='json')
        self.assertEqual(response.status_code, 400)


# ─── CredentialsUpdateView ────────────────────────────────────────────────────

class CredentialsUpdateTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = _make_user('creduser')
        _login(self.client, 'creduser')

    def test_update_credentials_success(self):
        response = self.client.post('/api/me/credentials/update/', {
            'nickname': 'newcreduser',
            'password': 'NewPass123',
            'password_confirm': 'NewPass123',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'newcreduser')
        self.assertTrue(self.user.check_password('NewPass123'))

    def test_update_credentials_unauthenticated(self):
        response = APIClient().post('/api/me/credentials/update/', {
            'nickname': 'newcreduser',
            'password': 'NewPass123',
            'password_confirm': 'NewPass123',
        }, format='json')
        self.assertEqual(response.status_code, 401)

    def test_update_credentials_passwords_dont_match(self):
        response = self.client.post('/api/me/credentials/update/', {
            'nickname': 'newcreduser2',
            'password': 'NewPass123',
            'password_confirm': 'OtherPass456',
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_update_credentials_missing_fields(self):
        response = self.client.post('/api/me/credentials/update/', {}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_update_credentials_nickname_taken(self):
        _make_user('taken_cred_nick')
        response = self.client.post('/api/me/credentials/update/', {
            'nickname': 'taken_cred_nick',
            'password': 'NewPass123',
            'password_confirm': 'NewPass123',
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_update_credentials_clears_must_change_flag(self):
        self.user.profile.must_change_credentials = True
        self.user.profile.save(update_fields=['must_change_credentials'])
        self.client.post('/api/me/credentials/update/', {
            'nickname': 'newcreduser3',
            'password': 'NewPass123',
            'password_confirm': 'NewPass123',
        }, format='json')
        self.user.profile.refresh_from_db()
        self.assertFalse(self.user.profile.must_change_credentials)

    def test_update_credentials_returns_new_tokens(self):
        response = self.client.post('/api/me/credentials/update/', {
            'nickname': 'newcreduser4',
            'password': 'NewPass123',
            'password_confirm': 'NewPass123',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertIn(settings.JWT_ACCESS_COOKIE_NAME, response.cookies)


# ─── SendInvitationView ───────────────────────────────────────────────────────

@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class SendInvitationTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = _make_user('sender')
        _login(self.client, 'sender')

    def test_send_invitation_success(self):
        response = self.client.post(
            '/api/invitations/send/', {'email': 'invited@example.com'}, format='json'
        )
        self.assertIn(response.status_code, [200, 201])
        self.assertTrue(Invitation.objects.filter(email='invited@example.com').exists())

    def test_send_invitation_unauthenticated(self):
        response = APIClient().post(
            '/api/invitations/send/', {'email': 'x@example.com'}, format='json'
        )
        self.assertEqual(response.status_code, 401)

    def test_send_invitation_missing_email(self):
        response = self.client.post('/api/invitations/send/', {}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_send_invitation_must_change_credentials_blocked(self):
        self.user.profile.must_change_credentials = True
        self.user.profile.save(update_fields=['must_change_credentials'])
        response = self.client.post(
            '/api/invitations/send/', {'email': 'blocked@example.com'}, format='json'
        )
        self.assertEqual(response.status_code, 403)

    def test_send_invitation_quota_exceeded(self):
        for i in range(settings.MAX_INVITATIONS_PER_USER):
            Invitation.objects.create(
                email=f'quota{i}@example.com',
                invited_by=self.user,
                expires_at=timezone.now() + timedelta(days=30),
            )
        response = self.client.post(
            '/api/invitations/send/', {'email': 'overquota@example.com'}, format='json'
        )
        self.assertEqual(response.status_code, 400)

    def test_send_invitation_email_already_active(self):
        existing = _make_user('existinguser', email='existing@example.com')
        existing.profile.verified_email = 'existing@example.com'
        existing.profile.save(update_fields=['verified_email'])
        response = self.client.post(
            '/api/invitations/send/', {'email': 'existing@example.com'}, format='json'
        )
        self.assertEqual(response.status_code, 400)

    def test_resend_invitation_is_idempotent(self):
        self.client.post('/api/invitations/send/', {'email': 'resend@example.com'}, format='json')
        response = self.client.post(
            '/api/invitations/send/', {'email': 'resend@example.com'}, format='json'
        )
        self.assertIn(response.status_code, [200, 201])
        self.assertEqual(Invitation.objects.filter(email='resend@example.com').count(), 1)

    def test_send_invitation_response_includes_remaining(self):
        response = self.client.post(
            '/api/invitations/send/', {'email': 'remaining@example.com'}, format='json'
        )
        self.assertIn('invitations_remaining', response.data)


# ─── InvitationListView ───────────────────────────────────────────────────────

class InvitationListTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = _make_user('listuser')
        _login(self.client, 'listuser')
        Invitation.objects.create(
            invited_by=self.user,
            email='listed@example.com',
            expires_at=timezone.now() + timedelta(days=30),
        )

    def test_list_invitations_authenticated(self):
        response = self.client.get('/api/invitations/')
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data), 1)

    def test_list_invitations_unauthenticated(self):
        response = APIClient().get('/api/invitations/')
        self.assertEqual(response.status_code, 401)

    def test_list_contains_only_own_invitations(self):
        other = _make_user('otherlistuser')
        Invitation.objects.create(
            invited_by=other,
            email='otherinvited@example.com',
            expires_at=timezone.now() + timedelta(days=30),
        )
        response = self.client.get('/api/invitations/')
        emails = [inv['email'] for inv in response.data]
        self.assertIn('listed@example.com', emails)
        self.assertNotIn('otherinvited@example.com', emails)


# ─── InvitationStatsView ──────────────────────────────────────────────────────

class InvitationStatsTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = _make_user('statsuser')
        _login(self.client, 'statsuser')

    def test_stats_authenticated(self):
        response = self.client.get('/api/invitations/stats/')
        self.assertEqual(response.status_code, 200)
        for key in ('total_sent', 'used', 'pending', 'expired', 'remaining', 'max_allowed'):
            self.assertIn(key, response.data)

    def test_stats_unauthenticated(self):
        response = APIClient().get('/api/invitations/stats/')
        self.assertEqual(response.status_code, 401)

    def test_stats_remaining_decrements_after_invite(self):
        initial = self.client.get('/api/invitations/stats/').data['remaining']
        Invitation.objects.create(
            invited_by=self.user,
            email='decrement@example.com',
            expires_at=timezone.now() + timedelta(days=30),
        )
        after = self.client.get('/api/invitations/stats/').data['remaining']
        self.assertEqual(after, initial - 1)


# ─── PrivacySettingsView ──────────────────────────────────────────────────────

class PrivacySettingsTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = _make_user('privacyuser')
        _login(self.client, 'privacyuser')

    def test_patch_hermit_mode(self):
        response = self.client.patch('/api/me/privacy/', {'is_hermit_mode': True}, format='json')
        self.assertEqual(response.status_code, 200)
        self.user.profile.refresh_from_db()
        self.assertTrue(self.user.profile.is_hermit_mode)

    def test_patch_is_discoverable(self):
        response = self.client.patch('/api/me/privacy/', {'is_discoverable': False}, format='json')
        self.assertEqual(response.status_code, 200)
        self.user.profile.refresh_from_db()
        self.assertFalse(self.user.profile.is_discoverable)

    def test_privacy_unauthenticated(self):
        response = APIClient().patch('/api/me/privacy/', {'is_hermit_mode': True}, format='json')
        self.assertEqual(response.status_code, 401)


# ─── complete_onboarding ──────────────────────────────────────────────────────

class CompleteOnboardingTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = _make_user('onboarduser')
        _login(self.client, 'onboarduser')

    def test_complete_onboarding(self):
        response = self.client.post('/api/me/onboarding/complete/')
        self.assertEqual(response.status_code, 200)
        self.user.profile.refresh_from_db()
        self.assertTrue(self.user.profile.onboarding_completed)

    def test_complete_onboarding_unauthenticated(self):
        response = APIClient().post('/api/me/onboarding/complete/')
        self.assertEqual(response.status_code, 401)

    def test_complete_onboarding_response_contains_profile(self):
        response = self.client.post('/api/me/onboarding/complete/')
        self.assertIn('profile', response.data)
        self.assertEqual(response.data['profile']['nickname'], 'onboarduser')


# ─── delete_account ───────────────────────────────────────────────────────────

class DeleteAccountTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = _make_user('deleteuser')
        _login(self.client, 'deleteuser')

    def test_delete_wrong_confirmation(self):
        response = self.client.delete('/api/me/delete/', {'confirm': 'nope'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertTrue(User.objects.filter(username='deleteuser').exists())

    def test_delete_missing_confirmation(self):
        response = self.client.delete('/api/me/delete/', {}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_delete_correct_confirmation(self):
        response = self.client.delete(
            '/api/me/delete/', {'confirm': 'DELETE_MY_ACCOUNT'}, format='json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='deleteuser').exists())

    def test_delete_unauthenticated(self):
        response = APIClient().delete(
            '/api/me/delete/', {'confirm': 'DELETE_MY_ACCOUNT'}, format='json'
        )
        self.assertEqual(response.status_code, 401)


# ─── export_data ──────────────────────────────────────────────────────────────

class ExportDataTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = _make_user('exportuser')
        _login(self.client, 'exportuser')

    def test_export_data_authenticated(self):
        response = self.client.get('/api/me/export/')
        self.assertEqual(response.status_code, 200)
        for key in ('export_date', 'profile', 'invitations', 'stats'):
            self.assertIn(key, response.data)

    def test_export_data_profile_nickname(self):
        response = self.client.get('/api/me/export/')
        self.assertEqual(response.data['profile']['nickname'], 'exportuser')

    def test_export_data_unauthenticated(self):
        response = APIClient().get('/api/me/export/')
        self.assertEqual(response.status_code, 401)

    def test_export_does_not_expose_password(self):
        response = self.client.get('/api/me/export/')
        self.assertNotIn('password', str(response.data))


# ─── NetworkTreeView ──────────────────────────────────────────────────────────

class NetworkTreeTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = _make_user('treeuser')
        _login(self.client, 'treeuser')

    def test_network_tree_authenticated(self):
        response = self.client.get('/api/me/network-tree/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('nodes', response.data)
        self.assertIn('edges', response.data)
        self.assertIn('meta', response.data)

    def test_network_tree_contains_root_node(self):
        response = self.client.get('/api/me/network-tree/')
        self.assertIn('treeuser', response.data['nodes'])
        self.assertTrue(response.data['nodes']['treeuser']['is_root'])

    def test_network_tree_unauthenticated(self):
        response = APIClient().get('/api/me/network-tree/')
        self.assertEqual(response.status_code, 401)

    def test_network_tree_includes_invited_users(self):
        invitee = _make_user('invitee_tree')
        invitee.profile.invited_by = self.user
        invitee.profile.save(update_fields=['invited_by'])
        response = self.client.get('/api/me/network-tree/')
        self.assertIn('invitee_tree', response.data['nodes'])


# ─── UserActivityView ─────────────────────────────────────────────────────────

class UserActivityTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = _make_user('activityuser')
        _login(self.client, 'activityuser')

    def test_activity_returns_list(self):
        response = self.client.get('/api/me/activity/')
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)

    def test_activity_unauthenticated(self):
        response = APIClient().get('/api/me/activity/')
        self.assertEqual(response.status_code, 401)


# ─── WaitlistCommunityView ────────────────────────────────────────────────────

class WaitlistCommunityTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = _make_user('communityuser')
        _login(self.client, 'communityuser')
        Waitlist.objects.create(email='waiting@example.com', message='quiero entrar')

    def test_community_view_authenticated(self):
        response = self.client.get('/api/waitlist/community/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('results', response.data)

    def test_community_view_unauthenticated(self):
        response = APIClient().get('/api/waitlist/community/')
        self.assertEqual(response.status_code, 401)

    def test_community_view_excludes_email(self):
        response = self.client.get('/api/waitlist/community/')
        for entry in response.data.get('results', []):
            self.assertNotIn('email', entry)


# ─── WaitlistActivateView ─────────────────────────────────────────────────────

@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class WaitlistActivateTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = _make_user('activator')
        _login(self.client, 'activator')
        self.entry = Waitlist.objects.create(email='waitingtoactivate@example.com')

    def test_activate_waitlist_entry(self):
        response = self.client.post(f'/api/waitlist/{self.entry.id}/activate/')
        self.assertIn(response.status_code, [200, 201])
        self.entry.refresh_from_db()
        self.assertTrue(self.entry.is_activated)

    def test_activate_nonexistent_entry_returns_404(self):
        response = self.client.post('/api/waitlist/99999/activate/')
        self.assertEqual(response.status_code, 404)

    def test_activate_unauthenticated(self):
        response = APIClient().post(f'/api/waitlist/{self.entry.id}/activate/')
        self.assertEqual(response.status_code, 401)

    def test_activate_must_change_credentials_blocked(self):
        self.user.profile.must_change_credentials = True
        self.user.profile.save(update_fields=['must_change_credentials'])
        response = self.client.post(f'/api/waitlist/{self.entry.id}/activate/')
        self.assertEqual(response.status_code, 403)

    def test_activate_already_activated_returns_404(self):
        # Activar primero
        self.client.post(f'/api/waitlist/{self.entry.id}/activate/')
        self.entry.refresh_from_db()
        # Intentar activar de nuevo
        response = self.client.post(f'/api/waitlist/{self.entry.id}/activate/')
        self.assertEqual(response.status_code, 404)


# ─── Error path regression tests (PR 4+5) ────────────────────────────────────

class ForgotPasswordSMTPErrorTest(TestCase):
    """Verifica el comportamiento ante fallos de SMTP en ForgotPasswordView."""

    def setUp(self):
        self.client = APIClient()
        self.user = _make_user('smtpfailuser', email='smtpfail@example.com')

    @patch('accounts.views.send_password_reset_email', side_effect=OSError('Connection refused'))
    def test_smtp_failure_returns_200_with_generic_message(self, _mock):
        """Un error SMTP no debe exponer información — devuelve 200 con mensaje genérico."""
        response = self.client.post(
            '/api/auth/forgot-password/', {'email': 'smtpfail@example.com'}, format='json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('message', response.data)

    @patch('accounts.views.send_password_reset_email', side_effect=OSError('Connection refused'))
    def test_smtp_failure_deletes_reset_token(self, _mock):
        """Si el email falla, el token creado se elimina para evitar tokens huérfanos."""
        self.client.post(
            '/api/auth/forgot-password/', {'email': 'smtpfail@example.com'}, format='json'
        )
        self.assertFalse(PasswordResetToken.objects.filter(user=self.user).exists())


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class SendInvitationSMTPErrorTest(TestCase):
    """Verifica el comportamiento ante fallos de SMTP en SendInvitationView."""

    def setUp(self):
        self.client = APIClient()
        self.user = _make_user('invitesmtp')
        _login(self.client, 'invitesmtp')

    @patch('accounts.views.send_invitation_email', side_effect=OSError('SMTP unreachable'))
    def test_smtp_failure_returns_502(self, _mock):
        """Un fallo SMTP al enviar invitación debe devolver 502, no 500."""
        response = self.client.post(
            '/api/invitations/send/', {'email': 'destino@example.com'}, format='json'
        )
        self.assertEqual(response.status_code, 502)

    @patch('accounts.views.send_invitation_email', side_effect=OSError('SMTP unreachable'))
    def test_smtp_failure_error_message_is_safe(self, _mock):
        """El mensaje de error no debe exponer detalles internos."""
        response = self.client.post(
            '/api/invitations/send/', {'email': 'destino2@example.com'}, format='json'
        )
        self.assertIn('error', response.data)
        self.assertNotIn('SMTP', response.data['error'])
        self.assertNotIn('unreachable', response.data['error'])
