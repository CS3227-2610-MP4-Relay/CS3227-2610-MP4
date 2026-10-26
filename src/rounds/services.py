"""Round writes shared by the rounds routes and demo creation."""

import unicodedata

from django.db import transaction
from django.utils import timezone

from accounts.models import Workspace

from .models import Build, BuildCase, Case, CaseCriterion, Criterion, Round

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


CRITERION_LIMIT = 20
CASE_LIMIT = 30
NO_LINK = "Link at least one acceptance criterion."
FOREIGN = "Choose criteria from this round."


class Refused(Exception):
    """A criterion or case write the RND-2 rules refuse.

    `str()` is the user-facing message; `field` names the form field it
    belongs next to, or is None for a refused deletion.
    """

    def __init__(self, message, field=None):
        super().__init__(message)
        self.field = field


# Every function below runs inside the caller's transaction, after the caller
# has locked the round row and re-checked that the round is Draft.


def add_criterion(round_, text):
    """Add a criterion to the locked `round_`, below the cap (RND-2.5)."""
    if round_.criteria.count() >= CRITERION_LIMIT:
        message = (
            f"This round has reached its limit of {CRITERION_LIMIT} "
            "acceptance criteria."
        )
        raise Refused(message, "text")
    return Criterion.objects.create(round=round_, text=text)


def save_criterion(criterion, text):
    """Change a criterion's text; its links stay."""
    criterion.text = text
    criterion.save(update_fields=["text"])


def _round_criteria(round_, criterion_ids):
    """Return the chosen criteria, refusing none or any not in `round_`."""
    ids = set(criterion_ids)
    if not ids:
        raise Refused(NO_LINK, "criteria")
    chosen = list(round_.criteria.filter(pk__in=ids))
    if len(chosen) != len(ids):
        raise Refused(FOREIGN, "criteria")
    return chosen


def _link(case, chosen):
    CaseCriterion.objects.bulk_create(
        CaseCriterion(case=case, criterion=criterion) for criterion in chosen
    )


def add_case(round_, fields, criterion_ids):
    """Add a case to the locked `round_`, linked to its chosen criteria."""
    if round_.cases.count() >= CASE_LIMIT:
        message = f"This round has reached its limit of {CASE_LIMIT} test cases."
        raise Refused(message, "title")
    chosen = _round_criteria(round_, criterion_ids)
    case = Case.objects.create(round=round_, **fields)
    _link(case, chosen)
    return case


def save_case(case, fields, criterion_ids):
    """Change a case's fields and replace its links with the chosen criteria."""
    chosen = _round_criteria(case.round, criterion_ids)
    for name, value in fields.items():
        setattr(case, name, value)
    case.save(update_fields=list(fields))
    case.links.all().delete()
    _link(case, chosen)


def delete_case(case):
    """Delete a case's links, then the case; its criteria stay (RND-2.3)."""
    case.links.all().delete()
    case.delete()


def delete_criterion(criterion):
    """Delete a criterion that no case links to (RND-2.6)."""
    if criterion.links.exists():
        raise Refused("This criterion is linked to a test case. Unlink it first.")
    criterion.delete()


NO_CASES = "Add at least one test case before publishing."


def build_key(label):
    """Return the label compared for uniqueness: no format characters, then NFC."""
    kept = "".join(char for char in label if unicodedata.category(char) != "Cf")
    return unicodedata.normalize("NFC", kept)


def publish(round_, label):
    """Open the locked Draft `round_` on its first build, covering every case.

    A round with no cases is refused before anything is written (RND-3.3).
    """
    cases = list(round_.cases.all())
    if not cases:
        raise Refused(NO_CASES, "label")
    build = Build.objects.create(round=round_, label=label, key=build_key(label))
    BuildCase.objects.bulk_create(BuildCase(build=build, case=case) for case in cases)
    round_.state = Round.State.OPEN
    round_.published_at = timezone.now()
    round_.save(update_fields=["state", "published_at"])
    return build


class RoundNotOpen(Exception):
    """A close of a round that is not Open; the view's 409 normally comes first."""

    def __init__(self):
        super().__init__("Only an Open round can be closed.")


def close(round_):
    """Close the locked `round_`, whose Open state the caller has re-checked.

    The update itself requires the Open state, so no caller can close a Draft
    round or move a Closed one's closing time (RND-6); nothing reopens a round.
    """
    now = timezone.now()
    closed = Round.objects.filter(pk=round_.pk, state=Round.State.OPEN).update(
        state=Round.State.CLOSED, closed_at=now
    )
    if not closed:
        raise RoundNotOpen
    round_.state, round_.closed_at = Round.State.CLOSED, now
