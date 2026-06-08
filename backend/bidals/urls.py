from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

from bidals.views import health_check, readiness_check

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health_check, name="root-health-check"),
    path("health/ready/", readiness_check, name="root-readiness-check"),
    path("api/health/", health_check, name="health-check"),
    path("api/health/ready/", readiness_check, name="api-readiness-check"),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/", include("apps.leads.urls")),
    path("api/", include("apps.auctions.urls")),
    path("api/", include("apps.raffles.urls")),
    path("api/", include("apps.audit.urls")),
]

if settings.SERVE_LOCAL_MEDIA and not settings.USE_S3:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
