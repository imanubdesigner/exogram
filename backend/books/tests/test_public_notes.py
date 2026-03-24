from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from books.models import Note


class PublicNotesViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='reader_public_notes',
            password='Testpass123'
        )
        self.user.profile.nickname = 'reader_public_notes'
        self.user.profile.save(update_fields=['nickname'])

        Note.objects.create(
            user=self.user.profile,
            content='Nota privada',
            visibility='private'
        )
        self.public_note = Note.objects.create(
            user=self.user.profile,
            content='Nota pública visible',
            visibility='public'
        )

    def test_public_notes_endpoint_returns_only_public_notes(self):
        response = self.client.get('/api/users/reader_public_notes/notes/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], str(self.public_note.id))
        self.assertEqual(response.data[0]['visibility'], 'public')

    def test_public_notes_endpoint_returns_404_when_profile_is_hermit(self):
        self.user.profile.is_hermit_mode = True
        self.user.profile.save(update_fields=['is_hermit_mode'])

        response = self.client.get('/api/users/reader_public_notes/notes/')

        self.assertEqual(response.status_code, 404)
