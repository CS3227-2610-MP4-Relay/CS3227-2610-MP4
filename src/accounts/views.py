"""Sign-in, sign-out, the coordinator home (ACC-1) and demo creation (ACC-2).

Both apply the ACC-3 abuse limits; the tester home is `rounds.tester.home`.
"""

import logging
from datetime import timedelta

from django import db
from django.conf import settings
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

from rounds.models import Round

from . import demo, limits
from .forms import SignInForm
from .models import User
from .workspaces import workspace_records

logger = logging.getLogger(__name__)

HOMES = {
    User.Role.COORDINATOR: "accounts:coordinator",
    User.Role.TESTER: "accounts:tester",
}
FAILED = "Username or password is incorrect."
SIGN_IN_LIMITED = "Too many sign-in attempts. Try again later."


@sensitive_post_parameters("password")
@never_cache
@require_http_methods(["GET", "POST"])
def sign_in(request):
    """Show the sign-in form; on valid credentials start a fresh session."""
    if request.method == "GET":
        return render(request, "accounts/sign_in.html")
    try:
        user, error = _check_sign_in(request)
    except db.Error:
        logger.exception("Sign-in failed in storage.")
        return render(request, "503.html", status=503)
    if error:
        status = 429 if error == SIGN_IN_LIMITED else 200
        context = {"error": error}
        return render(request, "accounts/sign_in.html", context, status=status)
    # login() keeps the identifier when the same user signs in again (ACC-1.7).
    request.session.cycle_key()
    login(request, user)
    lifetime = timedelta(seconds=settings.SESSION_COOKIE_AGE)
    request.session.set_expiry(timezone.now() + lifetime)
    return redirect(HOMES[user.role])


def _check_sign_in(request):
    """Check the address's count, authenticate, then count a failure (ACC-3).

    An unlocked read refuses early; the password is checked outside any lock,
    then the count is locked, checked again and a failure recorded. Returns the
    user, or None and the message to show. The session starts only after this
    transaction commits, so a failure in it signs no one in.
    """
    key = limits.client_key(request)
    if limits.reached(limits.peek(limits.SIGN_IN, key), limits.SIGN_IN):
        return None, SIGN_IN_LIMITED
    form = SignInForm(request.POST)
    user = form.is_valid() and authenticate(request, **form.cleaned_data)
    with transaction.atomic():
        limits.start()
        counter = limits.lock(limits.SIGN_IN, key)
        if limits.reached(counter, limits.SIGN_IN):
            return None, SIGN_IN_LIMITED
        if user:
            return user, None
        limits.record(counter, limits.SIGN_IN)
    return None, FAILED


@require_POST
def sign_out(request):
    """End the session on the server and return to the sign-in page.

    Only a signed-in user gets the message, so a signed-out visitor's sign-out
    stores no session row to carry it.
    """
    signed_in = request.user.is_authenticated
    logout(request)
    if signed_in:
        messages.info(request, "You have signed out.")
    return redirect("accounts:sign-in")


@never_cache
@require_GET
def coordinator_home(request):
    """Show the coordinator's home page with their workspace's rounds."""
    if not request.user.is_authenticated:
        return redirect("accounts:sign-in")
    if request.user.role != User.Role.COORDINATOR:
        raise PermissionDenied
    context = {
        "title": "Coordinator home",
        "rounds": workspace_records(request.user, Round),
    }
    return render(request, "rounds/coordinator_home.html", context)


def _demo_counts(read, key):
    """Read or lock the address's creation count, then the overall count."""
    return [
        (limits.DEMO, read(limits.DEMO, key)),
        (limits.DEMO_TOTAL, read(limits.DEMO_TOTAL, limits.TOTAL_KEY)),
    ]


def _any_reached(counts):
    return any(limits.reached(counter, limit) for limit, counter in counts)


@require_POST
# No names: hide create_demo's variables and those of undecorated frames below it.
@sensitive_variables()
def create_demo(request):
    """Create a demo workspace and show its passwords once, uncached (ACC-2).

    Both creation limits (ACC-3) are checked unlocked before any password is
    hashed, then again under their locks inside the creation transaction.
    """
    if request.user.is_authenticated:
        return redirect(HOMES[request.user.role])
    key = limits.client_key(request)
    page = None
    try:
        if not _any_reached(_demo_counts(limits.peek, key)):
            passwords = demo.generate_passwords()
            with transaction.atomic():
                limits.start()
                counts = _demo_counts(limits.lock, key)
                if not _any_reached(counts):
                    workspace, credentials = demo.create_demo_workspace(passwords)
                    page = render_to_string(
                        "accounts/demo.html",
                        {"workspace": workspace, "credentials": credentials},
                    )
                    for limit, counter in counts:
                        limits.record(counter, limit)
    except Exception:
        # The traceback names no password; the rendered page is never logged.
        logger.exception("Demo workspace creation failed.")
        return render(request, "503.html", status=503)
    if page is None:
        # Refused by a limit: a normal response, never routed through the 503.
        return render(request, "429.html", status=429)
    response = HttpResponse(page)
    response["Cache-Control"] = "no-store"
    return response


def csrf_failure(request, reason=""):
    """Refuse a request that failed CSRF or Origin checks with the 403 page."""
    return render(request, "403.html", status=403)
