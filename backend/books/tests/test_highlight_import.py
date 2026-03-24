"""
Tests de integración para upload e import de highlights.

Cubre:
- HighlightUploadView: parseo del archivo Kindle, detección de duplicados
- HighlightImportView: creación en DB, deduplicación, respuesta
"""
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from books.models import Book, Highlight

# ─── Fixture ────────────────────────────────────────────────────────────────

_CLIPPINGS_SINGLE = """\
El libro de prueba (Autor Prueba)
- Your Highlight on page 12 | location 100-101 | Added on Monday, January 1, 2024 12:00:00 AM

Contenido del highlight de prueba.
==========
"""

_CLIPPINGS_TWO = """\
El libro de prueba (Autor Prueba)
- Your Highlight on page 12 | location 100-101 | Added on Monday, January 1, 2024 12:00:00 AM

Primer highlight del libro.
==========
El libro de prueba (Autor Prueba)
- Your Highlight on page 15 | location 150-151 | Added on Tuesday, January 2, 2024 10:00:00 AM

Segundo highlight del libro.
==========
"""


def _make_user(username, password='Testpass123'):
    user = User.objects.create_user(username=username, password=password)
    user.profile.nickname = username
    user.profile.save(update_fields=['nickname'])
    return user


def _login(client, nickname, password='Testpass123'):
    return client.post('/api/auth/login/', {'nickname': nickname, 'password': password})


def _clippings_file(content=_CLIPPINGS_SINGLE, filename='My Clippings.txt'):
    return SimpleUploadedFile(
        filename,
        content.encode('utf-8'),
        content_type='text/plain',
    )


# ─── HighlightUploadView ─────────────────────────────────────────────────────

class HighlightUploadViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = _make_user('uploader')
        _login(self.client, 'uploader')

    def test_upload_valid_clippings_returns_preview(self):
        response = self.client.post(
            '/api/highlights/upload/',
            {'file': _clippings_file(_CLIPPINGS_SINGLE)},
            format='multipart',
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('total_parsed', response.data)
        self.assertGreater(response.data['total_parsed'], 0)
        self.assertIn('books_found', response.data)
        self.assertIn('new_count', response.data)
        # Nada guardado en DB en esta etapa
        self.assertEqual(Highlight.objects.count(), 0)

    def test_upload_two_highlights_preview(self):
        response = self.client.post(
            '/api/highlights/upload/',
            {'file': _clippings_file(_CLIPPINGS_TWO)},
            format='multipart',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['total_parsed'], 2)
        self.assertEqual(response.data['books_found'], 1)

    def test_upload_marks_existing_as_not_new(self):
        # Crear highlight preexistente del mismo contenido
        book = Book.objects.create(title='El libro de prueba')
        Highlight.objects.create(
            user=self.user.profile,
            book=book,
            content='Contenido del highlight de prueba.',
        )
        response = self.client.post(
            '/api/highlights/upload/',
            {'file': _clippings_file(_CLIPPINGS_SINGLE)},
            format='multipart',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['new_count'], 0)
        self.assertEqual(response.data['existing_count'], 1)
        for h in response.data['highlights']:
            self.assertFalse(h['is_new'])

    def test_upload_missing_file_returns_400(self):
        response = self.client.post('/api/highlights/upload/', {}, format='multipart')
        self.assertEqual(response.status_code, 400)

    def test_upload_oversized_file_returns_400(self):
        big = SimpleUploadedFile(
            'big.txt',
            b'A' * (6 * 1024 * 1024),
            content_type='text/plain',
        )
        response = self.client.post('/api/highlights/upload/', {'file': big}, format='multipart')
        self.assertEqual(response.status_code, 400)
        self.assertIn('grande', response.data.get('error', '').lower())

    def test_upload_binary_file_returns_400(self):
        binary = SimpleUploadedFile(
            'binary.txt',
            bytes(range(256)),
            content_type='text/plain',
        )
        response = self.client.post('/api/highlights/upload/', {'file': binary}, format='multipart')
        self.assertEqual(response.status_code, 400)

    def test_upload_empty_clippings_returns_400(self):
        empty = SimpleUploadedFile('empty.txt', b'', content_type='text/plain')
        response = self.client.post('/api/highlights/upload/', {'file': empty}, format='multipart')
        self.assertEqual(response.status_code, 400)

    def test_upload_unauthenticated_returns_401(self):
        anon = APIClient()
        response = anon.post(
            '/api/highlights/upload/',
            {'file': _clippings_file()},
            format='multipart',
        )
        self.assertEqual(response.status_code, 401)


# ─── HighlightImportView ─────────────────────────────────────────────────────

class HighlightImportViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = _make_user('importer')
        _login(self.client, 'importer')

    def _import_payload(self, content='Texto del highlight.', title='Libro Test', author='Autor Test'):
        return {
            'highlights': [
                {
                    'title': title,
                    'author': author,
                    'content': content,
                    'location': 'Loc 100',
                    'created_at': '2024-01-01T12:00:00Z',
                    'visibility': 'private',
                }
            ]
        }

    @patch('books.highlight_views.batch_generate_embeddings')
    def test_import_creates_highlight(self, mock_task):
        mock_task.delay.return_value = None
        payload = self._import_payload()
        response = self.client.post('/api/highlights/import/', payload, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertGreater(response.data['imported'], 0)
        self.assertTrue(Highlight.objects.filter(user=self.user.profile).exists())

    @patch('books.highlight_views.batch_generate_embeddings')
    def test_import_highlight_is_private(self, mock_task):
        mock_task.delay.return_value = None
        response = self.client.post('/api/highlights/import/', self._import_payload(), format='json')
        self.assertEqual(response.status_code, 201)
        h = Highlight.objects.filter(user=self.user.profile).first()
        self.assertEqual(h.visibility, 'private')

    @patch('books.highlight_views.batch_generate_embeddings')
    def test_import_skips_duplicates(self, mock_task):
        mock_task.delay.return_value = None
        payload = self._import_payload(content='Contenido único del test.')
        # Primera importación
        self.client.post('/api/highlights/import/', payload, format='json')
        # Segunda con mismo contenido
        response = self.client.post('/api/highlights/import/', payload, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertGreater(response.data['skipped_duplicates'], 0)
        self.assertEqual(Highlight.objects.filter(user=self.user.profile).count(), 1)

    def test_import_empty_list_returns_400(self):
        response = self.client.post('/api/highlights/import/', {'highlights': []}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_import_unauthenticated_returns_401(self):
        anon = APIClient()
        response = anon.post(
            '/api/highlights/import/',
            self._import_payload(),
            format='json',
        )
        self.assertEqual(response.status_code, 401)

    @patch('books.highlight_views.batch_generate_embeddings')
    def test_import_enqueues_embedding_task_when_highlights_created(self, mock_task):
        mock_task.delay.return_value = None
        self.client.post('/api/highlights/import/', self._import_payload(), format='json')
        mock_task.delay.assert_called_once()
