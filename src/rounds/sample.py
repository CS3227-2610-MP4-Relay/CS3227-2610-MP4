"""The sample draft round written into each new demo workspace (RND-7).

These constants are the one home of its fixed synthetic text: ASCII only and
within the RND-2 field limits. Each case names the criteria it links to by
their position in `CRITERIA`.
"""

from django.db import transaction

from . import services
from .models import Round

TITLE = "Sample round"

CRITERIA = (
    (
        "A signed-in user can add a task with a title, and it appears at the "
        "top of their task list."
    ),
    (
        "A task title of 1 to 80 characters is saved; an empty or 81-character "
        'title gets "Enter 1 to 80 characters." and no task is added.'
    ),
    "A user cannot see or change another user's tasks.",
)

CASES = (
    (
        {
            "title": "Add a task",
            "steps": "1. Sign in to the example to-do app as user A.\n"
            '2. Enter "Water the plants" as a task title.\n'
            "3. Choose Add.",
            "expected_result": '"Water the plants" appears at the top of '
            "user A's task list.",
        },
        (0,),
    ),
    (
        {
            "title": "Longest task title",
            "steps": "1. Sign in as user A.\n"
            "2. Enter a task title of exactly 80 characters.\n"
            "3. Choose Add.",
            "expected_result": "The task is added with its full 80-character "
            "title at the top of the list.",
        },
        (0, 1),
    ),
    (
        {
            "title": "Empty and too-long task titles",
            "steps": "1. Sign in as user A.\n"
            "2. Choose Add with an empty title.\n"
            "3. Enter a title of 81 characters and choose Add.",
            "expected_result": 'Each attempt shows "Enter 1 to 80 characters." '
            "and no task is added.",
        },
        (1,),
    ),
    (
        {
            "title": "Another user's task",
            "steps": "1. Sign in as user A, add a task and copy its address.\n"
            "2. Sign out and sign in as user B.\n"
            "3. Open the copied address.",
            "expected_result": "User B gets a not-found page, and user A's task "
            "is unchanged.",
        },
        (2,),
    ),
)


def create_sample_round(workspace):
    """Write the sample round into `workspace`, which demo creation has just made.

    It uses the shared round services, so the round cap, the criterion and case
    caps and same-round links apply. The new round row is locked first, as
    those services require; it is not yet committed, so nothing waits on it.
    """
    with transaction.atomic():
        created = services.create_round(workspace, TITLE)
        round_ = Round.objects.select_for_update().get(pk=created.pk)
        criteria = [services.add_criterion(round_, text) for text in CRITERIA]
        for fields, positions in CASES:
            linked = [criteria[position].pk for position in positions]
            services.add_case(round_, dict(fields), linked)
    return round_
