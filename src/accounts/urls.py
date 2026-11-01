"""Routes for sign-in, sign-out, the role homes and demo creation.

Also the tester's round, results, result entry and result feedback pages.
"""

from django.urls import path

from ai.feedback_views import feedback_page
from rounds import tester

from . import views

app_name = "accounts"
urlpatterns = [
    path("sign-in/", views.sign_in, name="sign-in"),
    path("sign-out/", views.sign_out, name="sign-out"),
    path("coordinator/", views.coordinator_home, name="coordinator"),
    path("tester/", tester.home, name="tester"),
    path("tester/rounds/<int:round_id>/", tester.detail, name="tester-round"),
    path(
        "tester/rounds/<int:round_id>/results/",
        tester.history,
        name="tester-results",
    ),
    path(
        "tester/rounds/<int:round_id>/cases/<int:case_id>/builds/<int:build_id>/result/",
        tester.result_entry,
        name="tester-result",
    ),
    path(
        "tester/rounds/<int:round_id>/cases/<int:case_id>/builds/<int:build_id>/result/feedback/",
        feedback_page,
        name="tester-feedback",
    ),
    path("demo/", views.create_demo, name="demo"),
]
