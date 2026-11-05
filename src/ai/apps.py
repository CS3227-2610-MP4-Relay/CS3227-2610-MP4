"""Django application configuration for the LLM gateway and AI features."""

from django.apps import AppConfig


class AiConfig(AppConfig):
    """Own the gateway's records, the AI feature pages and operator commands."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "ai"
