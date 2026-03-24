"""
URL configuration for exogram project.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from .views import health_view

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),  # Dynamic admin URL from settings
    path('api/health/', health_view, name='health'),

    # API endpoints
    path('api/', include('accounts.urls')),
    path('api/', include('books.urls')),
    path('api/social/', include('social.urls')),
    path('api/affinity/', include('affinity.urls')),
    path('api/discovery/', include('discovery.urls')),
    path('api/articles/', include('articles.urls')),
    path('api/threads/', include('threads.urls')),
]

# Servir media files en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
