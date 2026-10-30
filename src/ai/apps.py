"""Django application configuration for the shared LLM gateway."""

from django.apps import AppConfig


class AiConfig(AppConfig):
    """Own the gateway's operational records."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "ai"
