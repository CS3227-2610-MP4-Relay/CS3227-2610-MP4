"""Round writes shared by the rounds routes and demo creation."""

from django.db import transaction

from accounts.models import Workspace

from .models import Round

ROUND_LIMIT = 20


class RoundLimitReached(Exception):
    """The workspace already has its maximum number of rounds (RND-1.4)."""

    def __init__(self):
        super().__init__(
            f"This workspace has reached its limit of {ROUND_LIMIT} rounds."
        )


def create_round(workspace, title):
    """Create a Draft round in `workspace`, below the per-workspace cap.

    `workspace` is only ever the signed-in user's workspace or the one demo
    creation has just made, never a value from request data. The workspace
    row lock makes concurrent creations count one at a time (RND-1.5).
    """
    with transaction.atomic():
        Workspace.objects.select_for_update().filter(pk=workspace.pk).get()
        if Round.objects.filter(workspace=workspace).count() >= ROUND_LIMIT:
            raise RoundLimitReached
        return Round.objects.create(workspace=workspace, title=title)
