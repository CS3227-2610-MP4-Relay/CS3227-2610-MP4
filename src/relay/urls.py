"""Public application routes."""

from django.urls import path

from .pages import home

urlpatterns = [path("", home, name="home")]
