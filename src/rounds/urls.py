"""Routes for the coordinator's round pages."""

from django.urls import path

from . import views

app_name = "rounds"
urlpatterns = [
    path("new/", views.new_round, name="new"),
    path("<int:round_id>/", views.round_page, name="detail"),
    path("<int:round_id>/edit/", views.edit_round, name="edit"),
]
