"""Bounded account writes for the coordinator's ACC-4 action."""

from django.views.decorators.debug import sensitive_variables

from . import demo
from .models import User
from .workspaces import workspace_records

TESTER_LIMIT = 10


def tester_count(user):
    """Count only Beta Testers in the authorized coordinator's workspace."""
    return workspace_records(user, User).filter(role=User.Role.TESTER).count()


def tester_records(user):
    """Select only testers in the caller's workspace for ACC-5."""
    return workspace_records(user, User).filter(role=User.Role.TESTER)


@sensitive_variables()
def create_tester(user, password, hashed):
    """Write one tester while the caller holds its workspace lock below the cap.

    Username uniqueness is global; the bounded suffix draw follows demo
    creation, leaving a third collision to fail on the unique constraint.
    The view's transaction also encloses rendering the returned credential.
    """
    for _ in range(demo.SUFFIX_DRAWS):
        username = f"tester-{demo.draw_suffix()}"
        if not User.objects.filter(username=username).exists():
            break
    User.objects.create(
        username=username,
        role=User.Role.TESTER,
        workspace_id=user.workspace_id,
        password=hashed,
    )
    return demo.Credential(User.Role.TESTER.label, username, password)
