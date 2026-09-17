import os
from pathlib import Path
from dotenv import load_dotenv
from django.apps import AppConfig
from django.conf import settings

load_dotenv(dotenv_path=Path(__file__).resolve().parent / "tokens.env")

class jdashConfig(AppConfig):
    name = 'jdash'

    def ready(self):
        import jdash.audit.registry  # noqa

    default_auto_field = 'django.db.models.BigAutoField'
