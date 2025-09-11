from ninja import NinjaAPI

api = NinjaAPI(version="1.0.0")

# Aca se pueden agregar los routers de las otras apps
# from apps.users.routers import router as users_router
# api.add_router("/users", users_router)

