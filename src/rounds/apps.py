"""Application configuration for rounds."""

from django.apps import AppConfig


class RoundsConfig(AppConfig):
    """Register the rounds app and its models."""

    name = "rounds"
    default_auto_field = "django.db.models.BigAutoField"
