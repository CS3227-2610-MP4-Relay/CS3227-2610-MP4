"""Routes for sign-in, sign-out, the role home pages and demo creation."""

from django.urls import path

from rounds import tester

from . import views

app_name = "accounts"
urlpatterns = [
    path("sign-in/", views.sign_in, name="sign-in"),
    path("sign-out/", views.sign_out, name="sign-out"),
    path("coordinator/", views.coordinator_home, name="coordinator"),
    path("tester/", views.tester_home, name="tester"),
    path("tester/rounds/<int:round_id>/", tester.detail, name="tester-round"),
    path("demo/", views.create_demo, name="demo"),
]
