"""
Tests para modelos de la app Books.
"""
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from accounts.models import Invitation
from books.models import Author, Book, Highlight


class AuthorModelTest(TestCase):
    def test_create_author(self):
        author = Author.objects.create(name='Carl Sagan')
        self.assertEqual(str(author), 'Carl Sagan')
        self.assertEqual(author.openlibrary_id, '')

    def test_author_with_openlibrary_id(self):
        author = Author.objects.create(
            name='Carl Sagan',
            openlibrary_id='OL123456A'
        )
        self.assertEqual(author.openlibrary_id, 'OL123456A')


class BookModelTest(TestCase):
    def test_create_book(self):
        book = Book.objects.create(title='Cosmos')
        self.assertEqual(str(book), 'Cosmos')

    def test_book_with_authors(self):
        author = Author.objects.create(name='Carl Sagan')
        book = Book.objects.create(title='Cosmos', isbn='9780345539434')
        book.authors.add(author)
        self.assertIn(author, book.authors.all())

    def test_book_metadata(self):
        book = Book.objects.create(
            title='Cosmos',
            isbn='9780345539434',
            publish_year=1980,
            genre='Science'
        )
        self.assertEqual(book.publish_year, 1980)


class ProfileModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='Testpass123'
        )

    def test_profile_auto_created(self):
        """Profile debería crearse automáticamente via signal."""
        self.assertTrue(hasattr(self.user, 'profile'))

    def test_profile_defaults(self):
        profile = self.user.profile
        self.assertEqual(profile.nickname, f'user_{self.user.id}')
        self.assertFalse(profile.is_hermit_mode)

    def test_hermit_mode(self):
        profile = self.user.profile
        profile.is_hermit_mode = True
        profile.save()
        self.assertTrue(profile.is_hermit_mode)

    def test_available_invitations(self):
        profile = self.user.profile
        self.assertEqual(profile.invitations_remaining, settings.MAX_INVITATIONS_PER_USER)

    def test_available_invitations_decreases_with_direct_invited_users(self):
        Invitation.objects.create(
            invited_by=self.user,
            email='child_user@example.com'
        )

        profile = self.user.profile
        self.assertEqual(
            profile.invitations_remaining,
            settings.MAX_INVITATIONS_PER_USER - 1
        )


class InvitationModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='inviter',
            password='Testpass123'
        )
        self.user.profile.nickname = 'inviter'
        self.user.profile.save()

    def test_create_invitation(self):
        inv = Invitation.objects.create(
            invited_by=self.user,
            email='test@example.com'
        )
        self.assertFalse(inv.is_used)
        self.assertIsNotNone(inv.token)

    def test_invitation_expiry(self):
        inv = Invitation.objects.create(
            invited_by=self.user,
            email='test@example.com'
        )
        self.assertFalse(inv.is_expired)

    def test_expired_invitation(self):
        inv = Invitation.objects.create(
            invited_by=self.user,
            email='test@example.com'
        )
        inv.expires_at = timezone.now() - timedelta(seconds=1)
        inv.save(update_fields=['expires_at'])
        self.assertTrue(inv.is_expired)


class HighlightModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='reader',
            password='Testpass123'
        )
        self.author = Author.objects.create(name='Sagan')
        self.book = Book.objects.create(title='Cosmos')
        self.book.authors.add(self.author)

    def test_create_highlight(self):
        h = Highlight.objects.create(
            user=self.user.profile,
            book=self.book,
            content='The cosmos is all that is.',
            location='Loc 42-45'
        )
        self.assertIn('The cosmos', str(h))
        self.assertEqual(h.visibility, 'private')

    def test_highlight_visibility(self):
        h = Highlight.objects.create(
            user=self.user.profile,
            book=self.book,
            content='Test highlight',
            visibility='public'
        )
        self.assertEqual(h.visibility, 'public')
