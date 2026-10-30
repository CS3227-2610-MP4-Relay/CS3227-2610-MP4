"""Shared environment-independent Django configuration."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.messages",
    "accounts",
    "rounds",
    "ai",
]
MIDDLEWARE = [
    # First, so responses other middleware makes refuse framing too.
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]
ROOT_URLCONF = "relay.urls"
WSGI_APPLICATION = "relay.wsgi.application"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]
LANGUAGE_CODE = "en"
TIME_ZONE = "UTC"
USE_TZ = True

AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "accounts:sign-in"
CSRF_FAILURE_VIEW = "accounts.views.csrf_failure"
# Database sessions; sign-in also sets an absolute expiry 8 hours ahead (ACC-1.6).
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_AGE = 8 * 60 * 60
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
# Messages stay in the server-side session until shown, never in a cookie.
MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"
CSRF_COOKIE_SAMESITE = "Lax"
# Secure everywhere except local development, which turns it off.
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Code-level provider switch, never read from the environment. Runtime setup,
# confirmed evidence and pending validation: workflow/specs/ai/llm-gateway.md.
SOC_LLM_LIVE = True
