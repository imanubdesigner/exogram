from rest_framework import generics

from .models import Article
from .serializers import ArticleSerializer


class ArticleListView(generics.ListAPIView):
    """
    Lista artículos éticos, opcionalmente filtrados por placement.

    GET /api/articles/?placement=onboarding
    """
    serializer_class = ArticleSerializer

    def get_queryset(self):
        qs = Article.objects.filter(is_published=True)
        placement = self.request.query_params.get('placement')
        if placement:
            qs = qs.filter(placement=placement)
        return qs


class ArticleDetailView(generics.RetrieveAPIView):
    """
    Detalle de un artículo por slug.

    GET /api/articles/<slug>/
    """
    serializer_class = ArticleSerializer
    lookup_field = 'slug'
    queryset = Article.objects.filter(is_published=True)
