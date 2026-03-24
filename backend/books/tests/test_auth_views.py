"""
Tests para vistas de autenticación e invitaciones.
"""
import re
from datetime import timedelta
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import (
    Invitation,
    PasswordResetToken,
    build_password_reset_token_hash,
)


class AuthViewsTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='Testpass123'
        )
        self.user.profile.nickname = 'testuser'
        self.user.profile.save()

    def test_login_success(self):
        response = self.client.post('/api/auth/login/', {
            'nickname': 'testuser',
            'password': 'Testpass123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('user', response.data)
        self.assertIn(settings.JWT_ACCESS_COOKIE_NAME, response.cookies)
        self.assertIn(settings.JWT_REFRESH_COOKIE_NAME, response.cookies)

    def test_login_wrong_password(self):
        response = self.client.post('/api/auth/login/', {
            'nickname': 'testuser',
            'password': 'wrongpassword'
        })
        self.assertIn(response.status_code, [400, 401])

    def test_login_nonexistent_user(self):
        response = self.client.post('/api/auth/login/', {
            'nickname': 'nobody',
            'password': 'Testpass123'
        })
        self.assertIn(response.status_code, [400, 401])

    def test_me_unauthenticated(self):
        response = self.client.get('/api/me/')
        self.assertEqual(response.status_code, 401)

    def test_me_authenticated(self):
        response = self.client.post('/api/auth/login/', {
            'nickname': 'testuser',
            'password': 'Testpass123'
        })
        self.assertEqual(response.status_code, 200)
        me = self.client.get('/api/me/')
        self.assertEqual(me.status_code, 200)

    def test_update_credentials(self):
        self.user.profile.must_change_credentials = True
        self.user.profile.save(update_fields=['must_change_credentials'])

        response = self.client.post('/api/auth/login/', {
            'nickname': 'testuser',
            'password': 'Testpass123'
        })
        self.assertEqual(response.status_code, 200)

        response = self.client.post('/api/me/credentials/update/', {
            'nickname': 'testuser_new',
            'password': 'Newpass123',
            'password_confirm': 'Newpass123'
        })
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.profile.nickname, 'testuser_new')
        self.assertFalse(self.user.profile.must_change_credentials)

        self.client.credentials()
        relogin = self.client.post('/api/auth/login/', {
            'nickname': 'testuser_new',
            'password': 'Newpass123'
        })
        self.assertEqual(relogin.status_code, 200)

    def test_update_privacy_hermit_mode_toggle(self):
        response = self.client.post('/api/auth/login/', {
            'nickname': 'testuser',
            'password': 'Testpass123'
        })
        self.assertEqual(response.status_code, 200)

        enable = self.client.patch('/api/me/privacy/', {
            'is_hermit_mode': True,
            'is_discoverable': True,
            'comment_allowance_depth': 2
        }, format='json')
        self.assertEqual(enable.status_code, 200)
        self.user.profile.refresh_from_db()
        self.assertTrue(self.user.profile.is_hermit_mode)
        self.assertTrue(enable.data['is_hermit_mode'])

        disable = self.client.patch('/api/me/privacy/', {
            'is_hermit_mode': False,
            'is_discoverable': True,
            'comment_allowance_depth': 2
        }, format='json')
        self.assertEqual(disable.status_code, 200)
        self.user.profile.refresh_from_db()
        self.assertFalse(self.user.profile.is_hermit_mode)
        self.assertFalse(disable.data['is_hermit_mode'])

    def test_update_privacy_discoverable_toggle(self):
        response = self.client.post('/api/auth/login/', {
            'nickname': 'testuser',
            'password': 'Testpass123'
        })
        self.assertEqual(response.status_code, 200)

        disable = self.client.patch('/api/me/privacy/', {
            'is_hermit_mode': False,
            'is_discoverable': False,
            'comment_allowance_depth': 2
        }, format='json')
        self.assertEqual(disable.status_code, 200)
        self.user.profile.refresh_from_db()
        self.assertFalse(self.user.profile.is_discoverable)
        self.assertFalse(disable.data['is_discoverable'])

        enable = self.client.patch('/api/me/privacy/', {
            'is_hermit_mode': False,
            'is_discoverable': True,
            'comment_allowance_depth': 2
        }, format='json')
        self.assertEqual(enable.status_code, 200)
        self.user.profile.refresh_from_db()
        self.assertTrue(self.user.profile.is_discoverable)
        self.assertTrue(enable.data['is_discoverable'])

    def test_network_tree_respects_depth_and_node_limits(self):
        response = self.client.post('/api/auth/login/', {
            'nickname': 'testuser',
            'password': 'Testpass123'
        })
        self.assertEqual(response.status_code, 200)

        # Cadena lineal: testuser -> net_1 -> ... -> net_14
        parent = self.user
        for idx in range(1, 15):
            child = User.objects.create_user(
                username=f'net_{idx}',
                password='Testpass123'
            )
            child.profile.nickname = f'net_{idx}'
            child.profile.invited_by = parent
            child.profile.save(update_fields=['nickname', 'invited_by'])
            parent = child
        # Ramificación directa desde raíz para disparar límite por nodos
        for idx in range(1, 13):
            branch = User.objects.create_user(
                username=f'root_branch_{idx}',
                password='Testpass123'
            )
            branch.profile.nickname = f'root_branch_{idx}'
            branch.profile.invited_by = self.user
            branch.profile.save(update_fields=['nickname', 'invited_by'])

        depth_limited = self.client.get('/api/me/network-tree/?max_depth=2')
        self.assertEqual(depth_limited.status_code, 200)
        self.assertEqual(depth_limited.data['meta']['max_depth'], 2)
        self.assertFalse(depth_limited.data['meta']['truncated'])
        self.assertTrue(
            all((node.get('depth') or 0) <= 2 for node in depth_limited.data['nodes'].values())
        )

        node_limited = self.client.get('/api/me/network-tree/?max_nodes=10')
        self.assertEqual(node_limited.status_code, 200)
        self.assertEqual(node_limited.data['meta']['max_nodes'], 10)
        self.assertTrue(node_limited.data['meta']['truncated'])
        self.assertEqual(len(node_limited.data['nodes']), 10)


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class InvitationViewsTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='inviter',
            password='Testpass123'
        )
        self.user.profile.nickname = 'inviter'
        self.user.profile.save()

        # Authenticate (cookie-based session)
        response = self.client.post('/api/auth/login/', {
            'nickname': 'inviter',
            'password': 'Testpass123'
        })
        self.assertEqual(response.status_code, 200)

    def test_send_invitation(self):
        email = 'new_invited@example.com'
        response = self.client.post('/api/invitations/send/', {'email': email}, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['email'], email)
        self.assertNotIn('invited_user', response.data)
        self.assertEqual(User.objects.filter(email=email).count(), 0)

        invitation = Invitation.objects.get(email=email)
        self.assertFalse(invitation.is_used)
        self.assertTrue(invitation.is_token_valid)
        self.assertIsNotNone(invitation.token_hash)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('/accept-invite?token=', mail.outbox[0].body)
        self.assertNotIn('credenciales temporales', mail.outbox[0].body.lower())

    def test_accept_invitation_creates_user_without_auto_login(self):
        email = 'accepted_invite@example.com'
        response = self.client.post('/api/invitations/send/', {'email': email}, format='json')
        self.assertEqual(response.status_code, 201)

        token_match = re.search(r'accept-invite\?token=([^\s]+)', mail.outbox[0].body)
        self.assertIsNotNone(token_match)
        raw_token = token_match.group(1)

        anonymous_client = APIClient()
        accept_response = anonymous_client.post(
            '/api/accounts/accept-invite/',
            {
                'token': raw_token,
                'username': 'accepted_user',
                'password': 'Securepass99',
            },
            format='json',
        )

        self.assertEqual(accept_response.status_code, 201)
        created_user = User.objects.get(username='accepted_user')
        self.assertEqual(created_user.email, email)
        self.assertEqual(created_user.profile.nickname, 'accepted_user')
        self.assertEqual(created_user.profile.invited_by, self.user)
        self.assertEqual(created_user.profile.invitation_used.email, email)
        self.assertFalse(created_user.profile.must_change_credentials)

        invitation = Invitation.objects.get(email=email)
        invitation.refresh_from_db()
        self.assertTrue(invitation.is_used)
        self.assertEqual(invitation.created_user, created_user)

        # La unificación eliminó InvitationToken: el used_at ahora está en Invitation.
        invitation.refresh_from_db()
        self.assertIsNotNone(invitation.used_at)
        self.assertEqual(anonymous_client.get('/api/me/').status_code, 401)

    def test_invitation_stats(self):
        self.client.post('/api/invitations/send/', {'email': 'stats_user@example.com'}, format='json')
        response = self.client.get('/api/invitations/stats/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('total_sent', response.data)
        self.assertIn('sent_invitations', response.data)
        self.assertEqual(response.data['total_sent'], 1)

    def test_reset_temp_password_endpoint_disabled(self):
        response = self.client.post('/api/invitations/999/reset-temp-password/', {})
        self.assertEqual(response.status_code, 410)

    def test_reset_temp_password_still_disabled_for_other_user(self):
        outsider = User.objects.create_user(username='outsider', password='Testpass123')
        outsider.profile.nickname = 'outsider'
        outsider.profile.save(update_fields=['nickname'])

        self.client.force_authenticate(user=outsider)

        response = self.client.post('/api/invitations/999/reset-temp-password/', {})
        self.assertEqual(response.status_code, 410)

    def test_validate_invitation_invalid_uuid(self):
        """Token que no existe → 404."""
        self.client.cookies.clear()
        response = self.client.get('/api/invitations/validate/00000000-0000-0000-0000-000000000000/')
        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.data['valid'])


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class CSRFSecurityRegressionTest(TestCase):
    """Regresiones de seguridad: garantiza que CSRF cookie-auth siga activo."""

    def setUp(self):
        self.client = APIClient(enforce_csrf_checks=True)
        self.user = User.objects.create_user(username='csrf_user', password='Testpass123')
        self.user.profile.nickname = 'csrf_user'
        self.user.profile.save(update_fields=['nickname'])
        self.user.email = 'csrf_user@example.com'
        self.user.save(update_fields=['email'])
        self.user.profile.verified_email = 'csrf_user@example.com'
        self.user.profile.save(update_fields=['verified_email'])

        login = self.client.post('/api/auth/login/', {
            'nickname': 'csrf_user',
            'password': 'Testpass123',
        })
        self.assertEqual(login.status_code, 200)
        self.assertIn(settings.CSRF_COOKIE_NAME, login.cookies)
        self.csrf_token = login.cookies[settings.CSRF_COOKIE_NAME].value

    def test_post_with_jwt_cookie_without_csrf_header_is_rejected(self):
        # Si alguien desactiva CSRF por error, este test debe fallar de inmediato.
        response = self.client.post('/api/invitations/send/', {'email': 'csrf_no_header@example.com'}, format='json')
        self.assertEqual(response.status_code, 403)

    def test_post_with_matching_csrf_header_is_allowed(self):
        # Si alguien desactiva CSRF por error, este test debe fallar de inmediato.
        response = self.client.post(
            '/api/invitations/send/',
            {'email': 'csrf_ok@example.com'},
            format='json',
            HTTP_X_CSRFTOKEN=self.csrf_token,
        )
        self.assertEqual(response.status_code, 201)

    def test_forgot_password_requires_email(self):
        response = self.client.post('/api/auth/forgot-password/', {}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_forgot_password_unknown_email_reports_success(self):
        response = self.client.post(
            '/api/auth/forgot-password/',
            {'email': 'doesnotexist@example.com'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('message', response.data)
        self.assertEqual(PasswordResetToken.objects.count(), 0)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_forgot_password_existing_user_creates_reset_token(self):
        original_hash = self.user.password
        response = self.client.post(
            '/api/auth/forgot-password/',
            {'email': 'csrf_user@example.com'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)

        self.user.refresh_from_db()
        self.assertEqual(self.user.password, original_hash)
        self.assertFalse(self.user.profile.must_change_credentials)
        self.assertEqual(PasswordResetToken.objects.filter(user=self.user, used_at__isnull=True).count(), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('/reset-password?token=', mail.outbox[0].body)

    def test_forgot_password_send_failure_keeps_account_unchanged(self):
        original_hash = self.user.password

        with patch('accounts.views.send_password_reset_email', side_effect=OSError('smtp down')):
            response = self.client.post(
                '/api/auth/forgot-password/',
                {'email': 'csrf_user@example.com'},
                format='json',
            )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.password, original_hash)
        self.assertFalse(self.user.profile.must_change_credentials)
        self.assertEqual(PasswordResetToken.objects.filter(user=self.user).count(), 0)

    def test_reset_password_with_valid_token_updates_password(self):
        reset_token = PasswordResetToken.objects.create(
            user=self.user,
            token_hash=build_password_reset_token_hash('valid-token'),
            expires_at=timezone.now() + timedelta(hours=1),
        )

        response = self.client.post(
            '/api/auth/reset-password/',
            {
                'token': 'valid-token',
                'password': 'NuevaClave123',
                'password_confirm': 'NuevaClave123',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        reset_token.refresh_from_db()
        self.assertTrue(self.user.check_password('NuevaClave123'))
        self.assertIsNotNone(reset_token.used_at)

    def test_reset_password_rejects_expired_token(self):
        PasswordResetToken.objects.create(
            user=self.user,
            token_hash=build_password_reset_token_hash('expired-token'),
            expires_at=timezone.now() - timedelta(minutes=1),
        )

        response = self.client.post(
            '/api/auth/reset-password/',
            {
                'token': 'expired-token',
                'password': 'NuevaClave123',
                'password_confirm': 'NuevaClave123',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400)

    def test_logout_without_csrf_header_is_rejected(self):
        response = self.client.post('/api/auth/logout/', {}, format='json')
        self.assertEqual(response.status_code, 403)

        me = self.client.get('/api/me/')
        self.assertEqual(me.status_code, 200)

    def test_logout_with_matching_csrf_header_invalidates_session(self):
        response = self.client.post(
            '/api/auth/logout/',
            {},
            format='json',
            HTTP_X_CSRFTOKEN=self.csrf_token,
        )
        self.assertEqual(response.status_code, 200)

        me = self.client.get('/api/me/')
        self.assertEqual(me.status_code, 401)


class HealthViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch('exogram.views.redis_client.from_url')
    def test_health_ok(self, _mock_redis):
        response = self.client.get('/api/health/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get('status'), 'ok')
        self.assertEqual(data.get('db'), 'ok')

    @patch('exogram.views.redis_client.from_url')
    @patch('exogram.views.connection.cursor', side_effect=RuntimeError('db down'))
    def test_health_reports_db_error(self, _cursor, _mock_redis):
        response = self.client.get('/api/health/')
        self.assertEqual(response.status_code, 503)
        data = response.json()
        self.assertEqual(data.get('status'), 'error')
        self.assertEqual(data.get('db'), 'error')
