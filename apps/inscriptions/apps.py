from django.apps import AppConfig


class InscriptionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.inscriptions'

    def ready(self):
        import apps.inscriptions.signals
