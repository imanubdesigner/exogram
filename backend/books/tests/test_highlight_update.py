from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from books.models import Author, Book, Highlight


class HighlightUpdateViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='reader',
            password='Testpass123'
        )
        self.user.profile.nickname = 'reader'
        self.user.profile.save()

        author = Author.objects.create(name='Le Guin')
        book = Book.objects.create(title='A Wizard of Earthsea')
        book.authors.add(author)

        self.highlight = Highlight.objects.create(
            user=self.user.profile,
            book=book,
            content='Only in silence the word.',
            location='Loc 10-12',
            visibility='private'
        )

        login = self.client.post('/api/auth/login/', {
            'nickname': 'reader',
            'password': 'Testpass123'
        })
        self.assertEqual(login.status_code, 200)

    def test_patch_is_public_true(self):
        response = self.client.patch(
            f'/api/highlights/{self.highlight.id}/',
            {'is_public': True},
            format='json'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['visibility'], 'public')
        self.assertTrue(response.data['is_public'])

    def test_patch_is_public_false(self):
        self.highlight.visibility = 'public'
        self.highlight.save(update_fields=['visibility'])

        response = self.client.patch(
            f'/api/highlights/{self.highlight.id}/',
            {'is_public': False},
            format='json'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['visibility'], 'private')
        self.assertFalse(response.data['is_public'])

    def test_patch_note_on_private_highlight(self):
        response = self.client.patch(
            f'/api/highlights/{self.highlight.id}/',
            {'note': 'nota privada'},
            format='json'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['visibility'], 'private')
        self.assertEqual(response.data['note'], 'nota privada')

    def test_patch_rejects_visibility_and_is_public_together(self):
        response = self.client.patch(
            f'/api/highlights/{self.highlight.id}/',
            {'visibility': 'public', 'is_public': True},
            format='json'
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('solo uno', response.data['error'])

    def test_patch_rejects_non_boolean_is_public(self):
        response = self.client.patch(
            f'/api/highlights/{self.highlight.id}/',
            {'is_public': 'true'},
            format='json'
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('booleano', response.data['error'])
