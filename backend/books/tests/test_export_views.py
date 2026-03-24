"""
Tests para exportaciones Markdown.
"""
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from books.models import Author, Book, Highlight


class BookMarkdownExportViewTest(TestCase):
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

        self.author = Author.objects.create(name='Jorge Luis Borges')
        self.book = Book.objects.create(title='Ficciones', genre='Ficción')
        self.book.authors.add(self.author)

        Highlight.objects.create(
            user=self.user.profile,
            book=self.book,
            content='No nos une el amor sino el espanto.',
            location='p. 15',
            visibility='private',
            note='Anotación personal',
            created_at=timezone.now()
        )
        Highlight.objects.create(
            user=self.user.profile,
            book=self.book,
            content='El tiempo es la sustancia de que estoy hecho.',
            location='p. 24',
            visibility='private',
            created_at=timezone.now()
        )

    def test_export_book_markdown_success(self):
        response = self.client.get(f'/api/me/export/books/{self.book.id}/markdown/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/markdown', response['Content-Type'])
        self.assertIn('.md', response['Content-Disposition'])

        content = response.content.decode('utf-8')
        self.assertTrue(content.startswith('---\n'))
        self.assertIn('title: "Ficciones"', content)
        self.assertIn('author: "Jorge Luis Borges"', content)
        self.assertIn('highlights: 2', content)
        self.assertIn('## Highlights', content)
        self.assertIn('No nos une el amor sino el espanto.', content)
        self.assertIn('Nota: Anotación personal', content)

    def test_export_book_markdown_not_found(self):
        response = self.client.get('/api/me/export/books/999999/markdown/')
        self.assertEqual(response.status_code, 404)
