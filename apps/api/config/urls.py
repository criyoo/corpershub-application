from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from apps.common.home_backgrounds import home_background_image, home_background_manifest
from apps.common.views import health_check

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health_check, name="health-check-legacy"),
    path("healthz/", health_check, name="health-check"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/swagger/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/docs/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("api/home-backgrounds/", home_background_manifest, name="home-background-manifest"),
    path("api/home-backgrounds/<str:name>", home_background_image, name="home-background-image"),
    path("api/common/", include("apps.common.urls")),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/companies/", include("apps.companies.urls")),
    path("api/corpers/", include("apps.corpers.urls")),
    path("api/search/", include("apps.search.urls")),
    path("api/interests/", include("apps.interests.urls")),
    path("api/chat/", include("apps.chat.urls")),
    path("api/payments/", include("apps.payments.urls")),
    path("api/subscriptions/", include("apps.subscriptions.urls")),
    path("api/notifications/", include("apps.notifications.urls")),
    path("api/verification/", include("apps.verification.urls")),
    path("api/adminpanel/", include("apps.adminpanel.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
