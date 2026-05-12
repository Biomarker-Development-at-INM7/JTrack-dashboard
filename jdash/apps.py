from django.apps import AppConfig


class jdashConfig(AppConfig):
    name = 'jdash'

    def ready(self):
        import jdash.audit.registry  # noqa

    default_auto_field = 'django.db.models.BigAutoField'
