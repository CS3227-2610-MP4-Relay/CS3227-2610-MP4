"""Public presentation for the application foundation."""

from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_safe


@csrf_exempt
@require_safe
def home(request):
    """Render the stateless public page; reject every method that could write."""
    return render(request, "home.html")
