"""Sign-in, sign-out, the role home pages (ACC-1) and demo creation (ACC-2)."""

import logging
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters, sensitive_variables
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from . import demo
from .forms import SignInForm
from .models import User

logger = logging.getLogger(__name__)

SESSION_LIFETIME = timedelta(hours=8)
HOMES = {
    User.Role.COORDINATOR: "accounts:coordinator",
    User.Role.TESTER: "accounts:tester",
}


@sensitive_post_parameters("password")
@never_cache
@require_http_methods(["GET", "POST"])
def sign_in(request):
    """Show the sign-in form; on valid credentials start a fresh session."""
    if request.method == "GET":
        return render(request, "accounts/sign_in.html")
    form = SignInForm(request.POST)
    user = form.is_valid() and authenticate(request, **form.cleaned_data)
    if not user:
        context = {"error": "Username or password is incorrect."}
        return render(request, "accounts/sign_in.html", context)
    # login() keeps the identifier when the same user signs in again (ACC-1.7).
    request.session.cycle_key()
    login(request, user)
    request.session.set_expiry(timezone.now() + SESSION_LIFETIME)
    return redirect(HOMES[user.role])


@require_POST
def sign_out(request):
    """End the session on the server and return to the sign-in page."""
    logout(request)
    messages.info(request, "You have signed out.")
    return redirect("accounts:sign-in")


def _role_home(role, title):
    """Build a GET-only home page for one role."""

    @never_cache
    @require_GET
    def home(request):
        if not request.user.is_authenticated:
            return redirect("accounts:sign-in")
        if request.user.role != role:
            raise PermissionDenied
        return render(request, "accounts/home.html", {"title": title})

    return home


coordinator_home = _role_home(User.Role.COORDINATOR, "Coordinator home")
tester_home = _role_home(User.Role.TESTER, "Tester home")


@require_POST
@sensitive_variables("passwords", "credentials", "page")
def create_demo(request):
    """Create a demo workspace and show its passwords once, uncached (ACC-2)."""
    if request.user.is_authenticated:
        return redirect(HOMES[request.user.role])
    passwords = demo.generate_passwords()
    try:
        # ACC-3 locks its limit counts first, inside this same transaction.
        with transaction.atomic():
            workspace, credentials = demo.create_demo_workspace(passwords)
            page = render_to_string(
                "accounts/demo.html",
                {"workspace": workspace, "credentials": credentials},
            )
    except Exception:
        # The traceback names no password; the rendered page is never logged.
        logger.exception("Demo workspace creation failed.")
        return render(request, "503.html", status=503)
    response = HttpResponse(page)
    response["Cache-Control"] = "no-store"
    return response


def csrf_failure(request, reason=""):
    """Refuse a request that failed CSRF or Origin checks with the 403 page."""
    return render(request, "403.html", status=403)
