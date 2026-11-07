"""Public application routes."""

from django.urls import include, path

from .pages import home, readiness

urlpatterns = [
    path("health/ready/", readiness, name="readiness"),
    path("", home, name="home"),
    path("", include("accounts.urls")),
    path("coordinator/rounds/", include("rounds.urls")),
    path("coordinator/rounds/", include("ai.urls")),
]
