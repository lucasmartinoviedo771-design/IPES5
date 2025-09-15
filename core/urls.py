from django.contrib import admin
from django.urls import path, include, re_path
from django.http import HttpResponse
from django.views.generic import RedirectView
from apps.api.routers.v1 import api
from django.conf import settings
from django.conf.urls.static import static
from apps.preinscriptions.admin_api import export_preinscripciones_csv
from apps.dashboard import views as dash_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("api/v1/", api.urls),
    path("dashboard/", include("apps.dashboard.urls", namespace="dashboard")),
    path("", include("apps.preinscriptions.urls")),
    path("healthz/", lambda r: HttpResponse("ok")),
    path('gestion/preinscripciones/export.csv', export_preinscripciones_csv, name='pre_csv'),
    re_path(r"^ui/dashboard/?$", RedirectView.as_view(url="/dashboard/autorizar/", permanent=False)),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)