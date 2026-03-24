"""
Tests para la app Threads (mini-foro privado).

Cubre: Thread, ThreadMessage, vistas (list, create, detail, send message).
"""
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from threads.models import Thread, ThreadMessage

# ─── Helpers ────────────────────────────────────────────────────────────────


def make_user(username, nickname=None, password='Testpass123'):
    u = User.objects.create_user(username=username, password=password)
    u.profile.nickname = nickname or username
    u.profile.save(update_fields=['nickname'])
    return u


def login(client, user, password='Testpass123'):
    resp = client.post('/api/auth/login/', {'nickname': user.profile.nickname, 'password': password})
    assert resp.status_code == 200, resp.data
    return resp


def network_connect(user_a, user_b):
    """
    Conecta dos usuarios en la misma red de invitaciones
    para que puedan enviarse threads.
    user_a invitó a user_b.
    """
    user_b.profile.invited_by = user_a
    user_b.profile.comment_allowance_depth = 2
    user_b.profile.save(update_fields=['invited_by', 'comment_allowance_depth'])
    user_a.profile.comment_allowance_depth = 2
    user_a.profile.save(update_fields=['comment_allowance_depth'])


# ─── Model Tests ─────────────────────────────────────────────────────────────

class ThreadModelTest(TestCase):
    def setUp(self):
        self.u1 = make_user('alice')
        self.u2 = make_user('bob')

    def test_create_thread(self):
        thread = Thread.objects.create(context_book_title='Cosmos')
        thread.participants.add(self.u1.profile, self.u2.profile)
        self.assertEqual(thread.participants.count(), 2)
        self.assertEqual(thread.context_book_title, 'Cosmos')

    def test_get_other_participant(self):
        thread = Thread.objects.create()
        thread.participants.add(self.u1.profile, self.u2.profile)
        other = thread.get_other_participant(self.u1.profile)
        self.assertEqual(other, self.u2.profile)

    def test_thread_message_created(self):
        thread = Thread.objects.create()
        thread.participants.add(self.u1.profile, self.u2.profile)
        msg = ThreadMessage.objects.create(
            thread=thread,
            author=self.u1.profile,
            content='Hola, leíste Cosmos?'
        )
        self.assertEqual(msg.thread, thread)
        self.assertIn('Hola', str(msg))


# ─── API View Tests ───────────────────────────────────────────────────────────

class ThreadListCreateTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.alice = make_user('alice_t')
        self.bob = make_user('bob_t')
        network_connect(self.alice, self.bob)
        login(self.client, self.alice)

    def test_create_thread_with_network_user(self):
        resp = self.client.post('/api/threads/', {
            'other_nickname': 'bob_t',
            'context_book_title': 'Cosmos',
        }, format='json')
        self.assertIn(resp.status_code, [200, 201])
        self.assertEqual(resp.data['other_nickname'], 'bob_t')

    def test_create_thread_idempotent(self):
        """Si ya existe un hilo entre ambos, retorna el existente."""
        resp1 = self.client.post('/api/threads/', {'other_nickname': 'bob_t'}, format='json')
        resp2 = self.client.post('/api/threads/', {'other_nickname': 'bob_t'}, format='json')
        self.assertEqual(resp1.data['id'], resp2.data['id'])

    def test_create_thread_self_rejected(self):
        resp = self.client.post('/api/threads/', {'other_nickname': 'alice_t'}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_create_thread_unknown_user(self):
        resp = self.client.post('/api/threads/', {'other_nickname': 'nobody_xyz'}, format='json')
        self.assertEqual(resp.status_code, 404)

    def test_list_my_threads(self):
        self.client.post('/api/threads/', {'other_nickname': 'bob_t'}, format='json')
        resp = self.client.get('/api/threads/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['count'], 1)

    def test_thread_requires_auth(self):
        self.client.credentials()
        self.client.cookies.clear()
        resp = self.client.get('/api/threads/')
        self.assertIn(resp.status_code, [401, 403])

    def test_hermit_mode_blocks_thread_creation(self):
        """Si bob activa mode ermitaño, alice no puede iniciar un hilo."""
        self.bob.profile.is_hermit_mode = True
        self.bob.profile.save(update_fields=['is_hermit_mode'])
        resp = self.client.post('/api/threads/', {'other_nickname': 'bob_t'}, format='json')
        self.assertEqual(resp.status_code, 403)

    def test_no_network_connection_blocks_thread(self):
        """Sin conexión en la red, no se puede crear un hilo."""
        make_user('outsider_t')
        # No hay relación de invitación
        resp = self.client.post('/api/threads/', {'other_nickname': 'outsider_t'}, format='json')
        self.assertEqual(resp.status_code, 403)


class ThreadDetailAndMessagesTest(TestCase):
    def setUp(self):
        self.client_a = APIClient()
        self.client_b = APIClient()
        self.alice = make_user('alice_m')
        self.bob = make_user('bob_m')
        network_connect(self.alice, self.bob)

        login(self.client_a, self.alice)
        login(self.client_b, self.bob)

        # Crear hilo
        resp = self.client_a.post('/api/threads/', {'other_nickname': 'bob_m'}, format='json')
        self.thread_id = resp.data['id']

    def test_view_thread_detail(self):
        resp = self.client_a.get(f'/api/threads/{self.thread_id}/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('messages', resp.data)

    def test_send_message(self):
        resp = self.client_a.post(f'/api/threads/{self.thread_id}/messages/', {
            'content': 'Hola Bob, leíste Cosmos?'
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['author'], 'alice_m')
        self.assertIn('Cosmos', resp.data['content'])

    def test_both_participants_can_message(self):
        self.client_a.post(f'/api/threads/{self.thread_id}/messages/', {'content': 'Hola'}, format='json')
        resp = self.client_b.post(f'/api/threads/{self.thread_id}/messages/', {'content': 'Chau'}, format='json')
        self.assertEqual(resp.status_code, 201)

    def test_outsider_cannot_view_thread(self):
        outsider = make_user('outsider_m')
        client_o = APIClient()
        login(client_o, outsider)
        resp = client_o.get(f'/api/threads/{self.thread_id}/')
        self.assertEqual(resp.status_code, 403)

    def test_outsider_cannot_message(self):
        outsider = make_user('outsider_m2')
        client_o = APIClient()
        login(client_o, outsider)
        resp = client_o.post(f'/api/threads/{self.thread_id}/messages/', {'content': 'hack'}, format='json')
        self.assertEqual(resp.status_code, 403)

    def test_empty_message_rejected(self):
        resp = self.client_a.post(f'/api/threads/{self.thread_id}/messages/', {'content': ''}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_last_message_at_updated(self):
        self.client_a.post(f'/api/threads/{self.thread_id}/messages/', {'content': 'hello'}, format='json')
        thread = Thread.objects.get(id=self.thread_id)
        self.assertIsNotNone(thread.last_message_at)

    def test_message_over_2000_chars_rejected(self):
        """Mensajes que superan el límite de 2000 chars deben retornar 400."""
        long_content = 'x' * 2001
        resp = self.client_a.post(f'/api/threads/{self.thread_id}/messages/', {
            'content': long_content
        }, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('2000', resp.data.get('error', ''))

    def test_message_exactly_2000_chars_accepted(self):
        """Mensajes de exactamente 2000 chars son válidos."""
        content = 'a' * 2000
        resp = self.client_a.post(f'/api/threads/{self.thread_id}/messages/', {
            'content': content
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(len(resp.data['content']), 2000)
