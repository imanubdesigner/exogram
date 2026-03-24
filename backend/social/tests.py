"""
Tests para la app Social (comentarios + moderación).
"""
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from books.models import Book, Highlight
from social.models import Comment, UserFollow
from social.moderation import analyze_toxicity, moderate_comment


class ModerationTest(TestCase):
    """Tests para el engine de moderación local."""

    def test_clean_text_low_score(self):
        score, reason = analyze_toxicity('Gran reflexión sobre la ciencia')
        self.assertLess(score, 0.3)

    def test_toxic_text_high_score(self):
        score, reason = analyze_toxicity('idiota estúpido imbécil')
        self.assertGreater(score, 0.3)

    def test_spam_urls(self):
        text = 'Visitá http://spam.com http://more.com http://even.more.com'
        score, reason = analyze_toxicity(text)
        self.assertGreater(score, 0.2)

    def test_caps_abuse(self):
        score, reason = analyze_toxicity('ESTO ES UN MENSAJE MUY AGRESIVO Y EN MAYÚSCULAS TOTALES')
        self.assertGreater(score, 0.1)

    def test_empty_text(self):
        score, reason = analyze_toxicity('')
        self.assertEqual(score, 0.0)

    def test_moderate_approved(self):
        status, score, reason = moderate_comment('Hermosa frase, me resonó mucho')
        self.assertEqual(status, 'approved')

    def test_moderate_rejected(self):
        status, score, reason = moderate_comment('idiota estúpido pelotudo imbécil boludo')
        self.assertEqual(status, 'rejected')


class CommentModelTest(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user('commenter', password='pass123')
        self.user1.profile.nickname = 'commenter'
        self.user1.profile.save()

        self.user2 = User.objects.create_user('author', password='pass123')
        self.user2.profile.nickname = 'author'
        self.user2.profile.save()

        self.book = Book.objects.create(title='Test Book')
        self.highlight = Highlight.objects.create(
            user=self.user2.profile,
            book=self.book,
            content='Test highlight content',
            visibility='public'
        )

    def test_create_comment(self):
        comment = Comment.objects.create(
            author=self.user1.profile,
            highlight=self.highlight,
            content='Great insight!'
        )
        self.assertEqual(comment.status, 'pending')

    def test_approve_comment(self):
        comment = Comment.objects.create(
            author=self.user1.profile,
            highlight=self.highlight,
            content='Great insight!'
        )
        comment.approve()
        self.assertEqual(comment.status, 'approved')
        self.assertIsNotNone(comment.moderated_at)

    def test_reject_comment(self):
        comment = Comment.objects.create(
            author=self.user1.profile,
            highlight=self.highlight,
            content='Bad comment'
        )
        comment.reject('Manual rejection')
        self.assertEqual(comment.status, 'rejected')
        self.assertEqual(comment.moderation_reason, 'Manual rejection')


class FollowingUsersViewRegressionTest(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.follower_user = User.objects.create_user('follower', password='pass123')
        self.follower_user.profile.nickname = 'follower'
        self.follower_user.profile.save(update_fields=['nickname'])

        self.followed_user = User.objects.create_user('followed', password='pass123')
        self.followed_user.profile.nickname = 'followed'
        self.followed_user.profile.save(update_fields=['nickname'])

        UserFollow.objects.create(
            follower=self.follower_user.profile,
            following=self.followed_user.profile,
        )

        book = Book.objects.create(title='The Name of the Rose')
        Highlight.objects.create(
            user=self.followed_user.profile,
            book=book,
            content='Stat rosa pristina nomine.',
            visibility='public',
            location='Loc 12',
        )

    def test_following_includes_non_empty_book_title(self):
        # Este test cubre la regresión where se usaba latest.book_title en vez de
        # latest.book.title y terminaba rompiendo el payload del endpoint.
        self.client.force_authenticate(user=self.follower_user)
        response = self.client.get('/api/social/following/')

        self.assertEqual(response.status_code, 200)
        self.assertIn('results', response.data)
        self.assertGreaterEqual(len(response.data['results']), 1)

        for item in response.data['results']:
            self.assertIn('book_title', item)
            self.assertIsNotNone(item['book_title'])
            self.assertNotEqual(item['book_title'].strip(), '')
