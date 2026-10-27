"""Sign-in, sign-out and the role home pages (ACC-1)."""

from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .forms import SignInForm
from .models import User

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


def csrf_failure(request, reason=""):
    """Refuse a request that failed CSRF or Origin checks with the 403 page."""
    return render(request, "403.html", status=403)
