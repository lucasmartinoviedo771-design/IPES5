from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from apps.api.routers.v1 import api
from django.conf import settings
from django.conf.urls.static import static
from apps.preinscriptions.admin_api import export_preinscripciones_csv

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", api.urls),
    path("", include("apps.dashboard.urls")),
    path("", include("apps.preinscriptions.urls")),
    path("healthz/", lambda r: HttpResponse("ok")),
    path('gestion/preinscripciones/export.csv', export_preinscripciones_csv, name='pre_csv'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
