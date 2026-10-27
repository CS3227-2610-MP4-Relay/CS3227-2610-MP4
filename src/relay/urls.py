"""Public application routes."""

from django.urls import include, path

from .pages import home

urlpatterns = [
    path("", home, name="home"),
    path("", include("accounts.urls")),
    path("coordinator/rounds/", include("rounds.urls")),
]
