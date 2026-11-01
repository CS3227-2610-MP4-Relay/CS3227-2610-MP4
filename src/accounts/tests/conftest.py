"""Shared helpers for the accounts tests."""

from django.conf import settings as django_settings
from django.test import Client


def csrf_client(path):
    """A CSRF-enforcing client that loaded `path`, and its CSRF token."""
    client = Client(enforce_csrf_checks=True)
    client.get(path)
    return client, client.cookies[django_settings.CSRF_COOKIE_NAME].value
