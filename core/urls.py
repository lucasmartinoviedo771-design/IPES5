from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.api.routers.api_router")),
    path("", include("apps.dashboard.urls")),
    path("healthz/", lambda r: HttpResponse("ok")),
]
