"""
Tests para el flujo vigente de usuarios:
- Modelo A (Waitlist + invitación por email)
- Endpoints legacy deshabilitados
- Modelo C (trust promotion)
"""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Profile, Waitlist

# ─── Helpers ────────────────────────────────────────────────────────────────


def make_user(username, nickname=None, password='Testpass123'):
    user = User.objects.create_user(username=username, password=password)
    user.profile.nickname = nickname or username
    user.profile.save(update_fields=['nickname'])
    return user


def login(client, user, password='Testpass123'):
    resp = client.post('/api/auth/login/', {'nickname': user.profile.nickname, 'password': password})
    assert resp.status_code == 200, resp.data
    return resp


# ─── Modelo A: Waitlist ──────────────────────────────────────────────────────

class WaitlistModelTest(TestCase):
    def test_create_waitlist_entry(self):
        entry = Waitlist.objects.create(email='user@example.com', message='Hello')
        self.assertFalse(entry.is_activated)
        self.assertIsNone(entry.activated_by)
        self.assertIsNotNone(entry.requested_at)

    def test_activate_entry(self):
        user = make_user('activator')
        entry = Waitlist.objects.create(email='wait@example.com')
        entry.activate(user.profile)
        entry.refresh_from_db()
        self.assertTrue(entry.is_activated)
        self.assertEqual(entry.activated_by, user.profile)
        self.assertIsNotNone(entry.activated_at)


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class WaitlistAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_join_waitlist_public(self):
        resp = self.client.post('/api/waitlist/', {'email': 'new@example.com', 'message': 'hi'})
        self.assertEqual(resp.status_code, 201)
        self.assertIn('anotado', resp.data['message'].lower())
        self.assertTrue(Waitlist.objects.filter(email='new@example.com').exists())

    def test_join_waitlist_idempotent(self):
        self.client.post('/api/waitlist/', {'email': 'dup@example.com'})
        resp = self.client.post('/api/waitlist/', {'email': 'dup@example.com'})
        self.assertIn(resp.status_code, [200, 201])
        self.assertEqual(Waitlist.objects.filter(email='dup@example.com').count(), 1)

    def test_join_waitlist_invalid_email(self):
        resp = self.client.post('/api/waitlist/', {'email': 'not-an-email'})
        self.assertEqual(resp.status_code, 400)

    def test_join_waitlist_missing_email(self):
        resp = self.client.post('/api/waitlist/', {})
        self.assertEqual(resp.status_code, 400)

    def test_waitlist_activate_requires_auth(self):
        entry = Waitlist.objects.create(email='someone@example.com')
        resp = self.client.post(f'/api/waitlist/{entry.id}/activate/', {})
        self.assertIn(resp.status_code, [401, 403])

    def test_waitlist_activate_uses_quota(self):
        inviter = make_user('waitactivator')
        login(self.client, inviter)
        entry = Waitlist.objects.create(email='activate_me@example.com')
        initial_remaining = inviter.profile.invitations_remaining

        resp = self.client.post(f'/api/waitlist/{entry.id}/activate/', {})
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['waitlist_email'], 'activate_me@example.com')
        self.assertIn('invitations_remaining', resp.data)
        entry.refresh_from_db()
        self.assertTrue(entry.is_activated)
        inviter.profile.refresh_from_db()
        self.assertEqual(inviter.profile.invitations_remaining, initial_remaining - 1)

    def test_waitlist_activate_already_done(self):
        inviter = make_user('w_act2')
        login(self.client, inviter)
        entry = Waitlist.objects.create(email='done@example.com')
        self.client.post(f'/api/waitlist/{entry.id}/activate/', {})
        resp = self.client.post(f'/api/waitlist/{entry.id}/activate/', {})
        self.assertEqual(resp.status_code, 404)

    def test_list_waitlist_requires_staff(self):
        make_user('regular')
        login(self.client, make_user('regvisitor'))
        resp = self.client.get('/api/waitlist/')
        self.assertEqual(resp.status_code, 403)


# ─── Endpoints Legacy Deshabilitados ─────────────────────────────────────────

class LegacyInvitationEndpointsTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.inviter = make_user('legacyinviter')
        login(self.client, self.inviter)

    def test_create_invitation_link_disabled(self):
        resp = self.client.post('/api/invitations/link/', {})
        self.assertEqual(resp.status_code, 410)

    def test_register_by_token_disabled(self):
        resp = self.client.post('/api/auth/register-by-token/', {
            'token': '00000000-0000-0000-0000-000000000000',
            'nickname': 'legacyuser',
            'password': 'Securepass99',
            'password_confirm': 'Securepass99',
        })
        self.assertEqual(resp.status_code, 410)

    def test_validate_nonexistent_token(self):
        self.client.cookies.clear()
        resp = self.client.get('/api/invitations/validate/00000000-0000-0000-0000-000000000000/')
        self.assertEqual(resp.status_code, 404)
        self.assertFalse(resp.data['valid'])


# ─── Modelo C: Trust Promotion ───────────────────────────────────────────────

class TrustPromotionTest(TestCase):
    def test_promote_trust_levels_command(self):
        """El management command promueve perfiles con 30+ días en depth=0."""
        from io import StringIO

        from django.core.management import call_command

        # Crear usuario con antigüedad falsa (> 30 días)
        old_user = make_user('olduser')
        Profile.objects.filter(pk=old_user.profile.pk).update(
            created_at=timezone.now() - timedelta(days=31),
            comment_allowance_depth=0,
            trust_promoted_at=None,
        )

        # Crear usuario reciente (no debe promoverse)
        new_user = make_user('newuser')
        Profile.objects.filter(pk=new_user.profile.pk).update(
            comment_allowance_depth=0,
            trust_promoted_at=None,
        )

        out = StringIO()
        call_command('promote_trust_levels', stdout=out)
        self.assertIn('promovidos', out.getvalue().lower())

        old_user.profile.refresh_from_db()
        new_user.profile.refresh_from_db()

        self.assertEqual(old_user.profile.comment_allowance_depth, 1)
        self.assertIsNotNone(old_user.profile.trust_promoted_at)

        self.assertEqual(new_user.profile.comment_allowance_depth, 0)
        self.assertIsNone(new_user.profile.trust_promoted_at)

    def test_promote_trust_levels_dry_run(self):
        from io import StringIO

        from django.core.management import call_command

        old_user = make_user('dryrunuser')
        Profile.objects.filter(pk=old_user.profile.pk).update(
            created_at=timezone.now() - timedelta(days=40),
            comment_allowance_depth=0,
            trust_promoted_at=None,
        )

        out = StringIO()
        call_command('promote_trust_levels', '--dry-run', stdout=out)
        self.assertIn('dry run', out.getvalue().lower())

        old_user.profile.refresh_from_db()
        self.assertEqual(old_user.profile.comment_allowance_depth, 0)  # no debe cambiar

    def test_promote_already_promoted_skipped(self):
        from io import StringIO

        from django.core.management import call_command

        already_promoted = make_user('promoted_already')
        promoted_at = timezone.now() - timedelta(days=5)
        Profile.objects.filter(pk=already_promoted.profile.pk).update(
            created_at=timezone.now() - timedelta(days=35),
            comment_allowance_depth=1,  # ya promovido
            trust_promoted_at=promoted_at,
        )

        out = StringIO()
        call_command('promote_trust_levels', stdout=out)

        already_promoted.profile.refresh_from_db()
        self.assertEqual(already_promoted.profile.comment_allowance_depth, 1)
        self.assertAlmostEqual(
            already_promoted.profile.trust_promoted_at.timestamp(),
            promoted_at.timestamp(),
            delta=1
        )

    def test_celery_task_promotes_users(self):
        """La tarea Celery reproduce la misma lógica que el command."""
        from books.tasks import promote_trust_levels_task

        test_user = make_user('taskuser')
        Profile.objects.filter(pk=test_user.profile.pk).update(
            created_at=timezone.now() - timedelta(days=35),
            comment_allowance_depth=0,
            trust_promoted_at=None,
        )

        result = promote_trust_levels_task()
        self.assertGreaterEqual(result['promoted'], 1)

        test_user.profile.refresh_from_db()
        self.assertEqual(test_user.profile.comment_allowance_depth, 1)
