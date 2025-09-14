from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from apps.api.routers.v1 import api
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", api.urls),
    path("", include("apps.dashboard.urls")),
    path("healthz/", lambda r: HttpResponse("ok")),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
