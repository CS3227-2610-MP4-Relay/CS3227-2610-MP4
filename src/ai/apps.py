"""Django application configuration for the LLM gateway and its AI features."""

from django.apps import AppConfig


class AiConfig(AppConfig):
    """Own the gateway, its operational records and the AI features using it."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "ai"
