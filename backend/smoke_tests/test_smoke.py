"""
Smoke tests de Exogram (flujos críticos happy-path).

Qué son:
- Verificaciones de integración rápidas para confirmar que el sistema está vivo
  y funcional extremo a extremo.

Qué no son:
- No reemplazan tests unitarios ni de regresión fina; no buscan cobertura total.

Cuándo correrlos:
- Antes y después de cada deploy a producción (o entorno staging equivalente).

Cómo correrlos de forma aislada:
- `pytest -m smoke backend/smoke_tests/test_smoke.py`
"""
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from affinity.models import UserCluster
from books.models import Book, Highlight
from social.models import UserFollow

try:
    import pytest
    pytestmark = [pytest.mark.smoke]
except Exception:  # pragma: no cover - permite correr con manage.py test sin pytest instalado
    pytestmark = []


def _vector_384(value=0.001):
    return [value] * 384


class SmokeSuiteTest(TestCase):
    """
    Suite smoke de flujos críticos.
    """

    def setUp(self):
        self.client = APIClient(enforce_csrf_checks=True)

    def _create_user(self, username, nickname, password='Testpass123'):
        user = User.objects.create_user(username=username, password=password, email=f'{username}@example.com')
        user.profile.nickname = nickname
        user.profile.verified_email = user.email
        user.profile.save(update_fields=['nickname', 'verified_email'])
        return user

    def _login(self, nickname, password='Testpass123'):
        response = self.client.post(
            '/api/auth/login/',
            {'nickname': nickname, 'password': password},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(settings.JWT_ACCESS_COOKIE_NAME, response.cookies)
        self.assertIn(settings.CSRF_COOKIE_NAME, response.cookies)
        csrf_token = response.cookies[settings.CSRF_COOKIE_NAME].value
        self.client.credentials(HTTP_X_CSRFTOKEN=csrf_token)
        return response

    def test_00_sentry_empty_dsn_does_not_break_startup(self):
        # Errores de inicialización de Sentry suelen romper deploys en silencio.
        # Este test valida que con DSN vacío el bootstrap de Django sigue sano.
        dsn = getattr(settings, 'SENTRY_DSN', '')
        self.assertIn(dsn, ('', '# optional'))
        try:
            call_command('check', verbosity=0)
        except Exception as exc:  # pragma: no cover
            self.fail(f'Django startup/check failed with empty SENTRY_DSN: {exc}')

    def test_01_authentication_cookie_flow(self):
        # Valida todo el stack de auth por cookie: emisión JWT HttpOnly y
        # autenticación posterior vía clase custom basada en cookie.
        user = self._create_user('smoke_auth', 'smoke_auth')
        self._login('smoke_auth')

        me = self.client.get('/api/me/')
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.data['nickname'], user.profile.nickname)
        # El payload actual no expone user_id; validamos identidad autenticada end-to-end.
        self.assertEqual(me.wsgi_request.user.id, user.id)

    @patch('books.highlight_views.batch_generate_embeddings.delay')
    def test_02_highlight_import_enqueues_embedding_task(self, mock_delay):
        # No valida output ONNX; solo que el pipeline async de embeddings fue disparado.
        user = self._create_user('smoke_import', 'smoke_import')
        self._login('smoke_import')

        payload = {
            'highlights': [
                {
                    'title': 'Smoke Book',
                    'author': 'Smoke Author',
                    'content': 'Este es un highlight de humo para validar el pipeline async.',
                    'location': 'Loc 12',
                    'created_at': timezone.now().isoformat(),
                }
            ]
        }
        response = self.client.post('/api/highlights/import/', payload, format='json')
        self.assertEqual(response.status_code, 201)

        created = Highlight.objects.filter(user=user.profile).order_by('-id').first()
        self.assertIsNotNone(created)
        mock_delay.assert_called_once()
        queued_ids = mock_delay.call_args.args[0]
        self.assertIn(created.id, queued_ids)

    def test_03_discovery_feed_returns_valid_200_response(self):
        # El caso not_ready (sin centroide) debe responder 200 + lista vacía,
        # nunca error 500.
        user = self._create_user('smoke_discovery', 'smoke_discovery')
        self._login('smoke_discovery')

        book = Book.objects.create(title='Discovery Seed Book')
        Highlight.objects.create(
            user=user.profile,
            book=book,
            content='Texto con embedding preseed para smoke test de discovery.',
            location='Loc 1',
            visibility='public',
            embedding=_vector_384(),
        )
        UserCluster.objects.create(
            profile=user.profile,
            centroid=_vector_384(),
            highlights_count=1,
        )

        response = self.client.get('/api/discovery/feed/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('results', response.data)
        self.assertIsInstance(response.data['results'], list)
        if response.data.get('not_ready') is True:
            self.assertEqual(response.data['results'], [])

    def test_04_thread_create_post_and_read_cycle(self):
        # Cubre ciclo completo write-read del chat y la serialización de last_message.
        user_a = self._create_user('smoke_thread_a', 'smoke_thread_a')
        user_b = self._create_user('smoke_thread_b', 'smoke_thread_b')
        user_b.profile.invited_by = user_a
        user_b.profile.save(update_fields=['invited_by'])

        self._login('smoke_thread_a')

        create_thread = self.client.post(
            '/api/threads/',
            {'other_nickname': user_b.profile.nickname, 'context_book_title': 'Smoke Thread Book'},
            format='json',
        )
        self.assertEqual(create_thread.status_code, 201)
        thread_id = create_thread.data['id']

        send_message = self.client.post(
            f'/api/threads/{thread_id}/messages/',
            {'content': 'Mensaje smoke end-to-end'},
            format='json',
        )
        self.assertEqual(send_message.status_code, 201)

        detail = self.client.get(f'/api/threads/{thread_id}/')
        self.assertEqual(detail.status_code, 200)
        self.assertGreaterEqual(len(detail.data['messages']), 1)
        self.assertEqual(detail.data['messages'][-1]['content'], 'Mensaje smoke end-to-end')
        self.assertIsNotNone(detail.data['thread']['last_message'])
        self.assertEqual(detail.data['thread']['last_message']['content'], 'Mensaje smoke end-to-end')

    def test_05_following_endpoint_returns_book_title_regression_guard(self):
        # Guardia de regresión de P0.8: el título debe resolverse por latest.book.title.
        user_a = self._create_user('smoke_follow_a', 'smoke_follow_a')
        user_b = self._create_user('smoke_follow_b', 'smoke_follow_b')

        UserFollow.objects.create(follower=user_a.profile, following=user_b.profile)
        book = Book.objects.create(title='Regression Book Title')
        Highlight.objects.create(
            user=user_b.profile,
            book=book,
            content='Highlight para validar book_title en /api/social/following/.',
            location='Loc 9',
            visibility='public',
        )

        self._login('smoke_follow_a')
        response = self.client.get('/api/social/following/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('results', response.data)

        matching = [item for item in response.data['results'] if item.get('nickname') == user_b.profile.nickname]
        self.assertTrue(matching)
        self.assertEqual(matching[0].get('book_title'), 'Regression Book Title')
