"""A separately invoked pytest case checking real runner settings selection."""

from django.conf import settings


def test_runner_uses_fixed_settings():
    """Check selection after pytest-django initializes the actual runner."""
    assert settings.SETTINGS_MODULE == "relay.settings.test"
    assert settings.DEBUG is False
    assert settings.DATABASES["default"]["NAME"] == "relay_test"
