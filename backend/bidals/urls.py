from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

from bidals.views import health_check

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health_check, name="health-check"),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/", include("apps.auctions.urls")),
    path("api/", include("apps.audit.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
