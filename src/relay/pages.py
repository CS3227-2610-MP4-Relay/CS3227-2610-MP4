"""Public presentation for the application foundation."""

from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_safe

from accounts.views import HOMES


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
