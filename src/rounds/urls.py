"""Routes for the coordinator's round pages."""

from django.urls import path

from . import views

CRITERIA, CASES = {"kind": "criteria"}, {"kind": "cases"}
CRITERION = "<int:round_id>/criteria/<int:criterion_id>"
CASE = "<int:round_id>/cases/<int:case_id>"

app_name = "rounds"
urlpatterns = [
    path("new/", views.new_round, name="new"),
    path("<int:round_id>/", views.round_page, name="detail"),
    path("<int:round_id>/edit/", views.edit_round, name="edit"),
    path("<int:round_id>/criteria/new/", views.record_form, CRITERIA, "criterion-new"),
    path(f"{CRITERION}/edit/", views.record_form, CRITERIA, "criterion-edit"),
    path(f"{CRITERION}/delete/", views.delete_record, CRITERIA, "criterion-delete"),
    path("<int:round_id>/cases/new/", views.record_form, CASES, "case-new"),
    path(f"{CASE}/edit/", views.record_form, CASES, "case-edit"),
    path(f"{CASE}/delete/", views.delete_record, CASES, "case-delete"),
    path("<int:round_id>/publish/", views.publish_round, name="publish"),
    path("<int:round_id>/retest/", views.retest_round, name="retest"),
    path("<int:round_id>/close/", views.close_round, name="close"),
]
