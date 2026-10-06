from django.conf import settings
from django.http import FileResponse, Http404
from django.urls import path, re_path

from corpus.api import api


def spa(request):
    """Serve the Vue app shell for client-side routes (assets are served by WhiteNoise)."""
    index = settings.FRONTEND_DIST / 'index.html'
    if not index.exists():
        raise Http404('frontend not built')
    return FileResponse(open(index, 'rb'), content_type='text/html')


urlpatterns = [
    path('api/', api.urls),
    re_path(r'^(?!api/|static/).*$', spa),
]
