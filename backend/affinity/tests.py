"""
Tests para la app Affinity (clustering + afinidad).
"""
from django.contrib.auth.models import User
from django.test import TestCase

from affinity.clustering import compute_user_centroid, update_user_cluster
from affinity.models import ReadingSession, UserCluster
from books.models import Book


class UserClusterModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('reader', password='pass123')
        self.user.profile.nickname = 'reader'
        self.user.profile.save()

    def test_create_cluster(self):
        cluster = UserCluster.objects.create(
            profile=self.user.profile,
            highlights_count=5
        )
        self.assertIn('reader', str(cluster))


class ReadingSessionModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('reader', password='pass123')
        self.user.profile.nickname = 'reader'
        self.user.profile.save()
        self.book = Book.objects.create(title='Test Book')

    def test_create_session(self):
        session = ReadingSession.objects.create(
            profile=self.user.profile,
            book=self.book,
            status='reading',
            progress=0.5
        )
        self.assertEqual(session.status, 'reading')
        self.assertEqual(session.progress, 0.5)

    def test_unique_together(self):
        ReadingSession.objects.create(
            profile=self.user.profile,
            book=self.book
        )
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            ReadingSession.objects.create(
                profile=self.user.profile,
                book=self.book
            )


class ClusteringTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('reader', password='pass123')
        self.user.profile.nickname = 'reader'
        self.user.profile.save()

    def test_centroid_no_highlights(self):
        """Sin highlights, el centroide debería ser None."""
        centroid = compute_user_centroid(self.user.profile)
        self.assertIsNone(centroid)

    def test_update_cluster_no_data(self):
        """Sin highlights, update_user_cluster debería retornar None."""
        result = update_user_cluster(self.user.profile)
        self.assertIsNone(result)
