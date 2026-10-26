"""Shared environment-independent Django configuration."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
INSTALLED_APPS = []
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
]
ROOT_URLCONF = "relay.urls"
WSGI_APPLICATION = "relay.wsgi.application"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": []},
    }
]
LANGUAGE_CODE = "en"
TIME_ZONE = "UTC"
USE_TZ = True
