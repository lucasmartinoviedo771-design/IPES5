# apps/api/routers/v1.py
from ninja import NinjaAPI
from ninja.security import APIKeyHeader
from apps.users.models import UserProfile
from apps.academics.routers import router as academics_router
from apps.users.routers import router as users_router
from apps.inscriptions.routers import router as inscriptions_router
from apps.inscriptions.routers_padron import router as padron_router
from apps.preinscriptions.routers import router as preinscripciones_router

class ApiKeyAuth(APIKeyHeader):
    param_name = "X-API-Key"
    def authenticate(self, request, key):
        try:
            return UserProfile.objects.get(api_key=key)
        except UserProfile.DoesNotExist:
            return None

api = NinjaAPI(title="IPES5 API", version="1.0.0", auth=ApiKeyAuth())

api.add_router("/academics", academics_router)
api.add_router("/estudiantes", users_router)
api.add_router("/inscripciones", inscriptions_router)
api.add_router("/padron", padron_router)
api.add_router("/preinscripciones", preinscripciones_router)

@api.get("/healthz", auth=None)
def healthz(request):
    from django.utils import timezone
    return {"status": "ok", "ts": timezone.now().isoformat()}