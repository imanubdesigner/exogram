"""
Tests para activación de sincronización Goodreads.
"""
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from affinity.models import ReadingSession
from books.models import Author, Book


class GoodreadsActivationViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='reader',
            password='Testpass123'
        )
        self.user.profile.nickname = 'reader'
        self.user.profile.save()

        login = self.client.post('/api/auth/login/', {
            'nickname': 'reader',
            'password': 'Testpass123'
        })
        self.assertEqual(login.status_code, 200)

    @patch('books.goodreads_tasks.sync_goodreads_reading.delay')
    def test_activate_goodreads_with_payload_username(self, mock_delay):
        mock_delay.return_value = SimpleNamespace(id='task-123')

        response = self.client.post('/api/me/goodreads/activate/', {
            'goodreads_username': '1234567-maria'
        }, format='json')

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data['status'], 'queued')
        self.assertEqual(response.data['task_id'], 'task-123')
        self.assertEqual(
            response.data['goodreads_feed_url'],
            'https://www.goodreads.com/review/list_rss/1234567?shelf=read'
        )
        mock_delay.assert_called_once_with(self.user.id)

    @patch('books.goodreads_tasks.sync_goodreads_reading.delay')
    def test_activate_goodreads_with_saved_username(self, mock_delay):
        mock_delay.return_value = SimpleNamespace(id='task-456')
        profile = self.user.profile
        profile.goodreads_username = '7654321-lector'
        profile.save(update_fields=['goodreads_username', 'updated_at'])

        response = self.client.post('/api/me/goodreads/activate/', {}, format='json')

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data['task_id'], 'task-456')
        self.assertEqual(
            response.data['goodreads_feed_url'],
            'https://www.goodreads.com/review/list_rss/7654321?shelf=read'
        )
        mock_delay.assert_called_once_with(self.user.id)

    @patch('books.goodreads_tasks.sync_goodreads_reading.delay')
    def test_activate_goodreads_accepts_username_without_numeric_id(self, mock_delay):
        mock_delay.return_value = SimpleNamespace(id='task-789')

        response = self.client.post('/api/me/goodreads/activate/', {
            'goodreads_username': 'usuario-sin-id'
        }, format='json')

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data['status'], 'queued')
        self.assertEqual(response.data['task_id'], 'task-789')
        self.assertEqual(response.data['goodreads_feed_url'], '')
        mock_delay.assert_called_once_with(self.user.id)

    def test_activate_goodreads_rejects_empty_username(self):
        response = self.client.post('/api/me/goodreads/activate/', {
            'goodreads_username': '   '
        }, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('Debes configurar tu usuario de Goodreads', response.data['error'])

    def test_get_goodreads_reading_returns_sessions(self):
        author = Author.objects.create(name='Ursula K. Le Guin')
        book = Book.objects.create(title='A Wizard of Earthsea')
        book.authors.add(author)
        ReadingSession.objects.create(
            profile=self.user.profile,
            book=book,
            status='reading',
            progress=0.42
        )

        response = self.client.get('/api/me/goodreads/reading/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['book_title'], 'A Wizard of Earthsea')
        self.assertEqual(response.data['results'][0]['progress_percent'], 42)
