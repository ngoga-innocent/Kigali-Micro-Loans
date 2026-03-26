
from django.contrib import admin
from django.urls import path,include
from django.conf.urls.static import static
from django.conf import settings
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions
urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/clients/", include("clients.urls")),
    path("api/loans/", include("loans.urls")),
    path("api/users/", include("users.urls"))
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
schema_view = get_schema_view(
    openapi.Info(
        title="Kigali Microloans API",
        default_version='v1',
        description="Loan Management System API",
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns += [
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0)),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0)),
]
