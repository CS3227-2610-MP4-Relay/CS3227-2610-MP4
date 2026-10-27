"""Application configuration for accounts."""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Register the accounts app and its models."""

    name = "accounts"
    default_auto_field = "django.db.models.BigAutoField"
