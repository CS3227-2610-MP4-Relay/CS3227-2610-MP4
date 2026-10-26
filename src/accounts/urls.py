"""Routes for sign-in, sign-out and the role home pages."""

from django.urls import path

from . import views

app_name = "accounts"
urlpatterns = [
    path("sign-in/", views.sign_in, name="sign-in"),
    path("sign-out/", views.sign_out, name="sign-out"),
    path("coordinator/", views.coordinator_home, name="coordinator"),
    path("tester/", views.tester_home, name="tester"),
]
