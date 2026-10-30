"""The Test Coordinator's drafting routes."""

from django.urls import path

from . import views

app_name = "ai"
urlpatterns = [
    path(
        "<int:round_id>/cases/draft/",
        views.draft_page,
        name="draft",
    ),
    path(
        "<int:round_id>/cases/draft/use/",
        views.use_draft,
        name="use-draft",
    ),
]
