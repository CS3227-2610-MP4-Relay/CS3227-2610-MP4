"""Public presentation for the application foundation."""

from django.db import DatabaseError, InterfaceError, connection
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_safe

from accounts.views import HOMES


@csrf_exempt
@never_cache
@require_safe
def readiness(request):
    """Check runtime database connectivity without accessing application records."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except (DatabaseError, InterfaceError):
        status, body = 503, "unavailable\n"
    else:
        status, body = 200, "ready\n"
    return HttpResponse(
        "" if request.method == "HEAD" else body,
        status=status,
        content_type="text/plain; charset=utf-8",
        headers={"Content-Length": str(len(body))},
    )


@csrf_exempt
@require_safe
def home(request):
    """Render the start page, or send a signed-in user to their role home.

    Reject every method that could write. The page's CSRF token still renders
    for the demo button, which POSTs to the CSRF-protected `/demo/`.
    """
    if request.user.is_authenticated:
        return redirect(HOMES[request.user.role])
    return render(request, "home.html")
