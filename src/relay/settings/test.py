"""Fixed settings for tests against an isolated throwaway PostgreSQL server."""

from .base import *

SECRET_KEY = "relay-test-only-not-a-production-secret"
DEBUG = False
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "relay_test",
        "USER": "relay_test",
        "PASSWORD": "relay_test",
        "HOST": "127.0.0.1",
        "OPTIONS": {"hostaddr": "127.0.0.1"},
        "PORT": "55432",
        "TEST": {"NAME": "test_relay_test"},
    }
}
# A fast hasher keeps the suite quick; shared and local settings keep Django's default.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
