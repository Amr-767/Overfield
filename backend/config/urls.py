"""Root URL configuration for AgroSpace Quest."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include(("apps.core.urls", "core"), namespace="api-v1")),
]
