"""Test rounds owned by a workspace (RND)."""

from django.conf import settings
from django.db import models
from django.urls import reverse

from accounts.models import Workspace


class Round(models.Model):
    """A workspace's test round, which moves Draft -> Open -> Closed."""

    class State(models.TextChoices):
        """The round states, in their only order."""

        DRAFT = "draft", "Draft"
        OPEN = "open", "Open"
        CLOSED = "closed", "Closed"

    workspace = models.ForeignKey(
        Workspace, on_delete=models.PROTECT, related_name="rounds"
    )
    title = models.CharField(max_length=120)
    state = models.CharField(max_length=8, choices=State.choices, default=State.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(state__in=["draft", "open", "closed"]),
                name="rounds_round_state_valid",
            )
        ]

    def __str__(self):
        """Return the round title."""
        return self.title

    def get_absolute_url(self):
        """Return the coordinator's round page."""
        return reverse("rounds:detail", args=[self.pk])


class Criterion(models.Model):
    """An acceptance criterion of a round (RND-2)."""

    round = models.ForeignKey(Round, on_delete=models.PROTECT, related_name="criteria")
    text = models.CharField(max_length=500)

    class Meta:
        # Creation order: a round's writes are serialised by its row lock.
        ordering = ["id"]

    def __str__(self):
        """Return the criterion text."""
        return self.text


class Case(models.Model):
    """A test case of a round, linked to one or more of its criteria (RND-2)."""

    round = models.ForeignKey(Round, on_delete=models.PROTECT, related_name="cases")
    title = models.CharField(max_length=120)
    steps = models.CharField(max_length=2000)
    expected_result = models.CharField(max_length=1000)
    criteria = models.ManyToManyField(
        Criterion, through="CaseCriterion", related_name="cases"
    )

    class Meta:
        ordering = ["id"]

    def __str__(self):
        """Return the case title."""
        return self.title


class CaseCriterion(models.Model):
    """A case's link to a criterion of the same round; never cascades."""

    case = models.ForeignKey(Case, on_delete=models.PROTECT, related_name="links")
    criterion = models.ForeignKey(
        Criterion, on_delete=models.PROTECT, related_name="links"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["case", "criterion"], name="rounds_casecriterion_unique"
            )
        ]


class Build(models.Model):
    """A named build of the software under test, covering some of a round's cases.

    Publishing creates a round's first build (RND-3). Its default string shows
    no user text, so a logged record never carries a label.
    """

    round = models.ForeignKey(Round, on_delete=models.PROTECT, related_name="builds")
    label = models.CharField(max_length=100)
    # The label without format characters, then NFC, which can triple length.
    key = models.CharField(max_length=300)
    created_at = models.DateTimeField(auto_now_add=True)
    cases = models.ManyToManyField(Case, through="BuildCase", related_name="builds")

    class Meta:
        # Creation order, serialised by the round lock: a case's current build
        # is the last build covering it.
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["round", "key"], name="rounds_build_key_unique"
            )
        ]


class BuildCase(models.Model):
    """A build's coverage of one case of the same round; never cascades."""

    build = models.ForeignKey(Build, on_delete=models.PROTECT, related_name="links")
    case = models.ForeignKey(Case, on_delete=models.PROTECT, related_name="build_links")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["build", "case"], name="rounds_buildcase_unique"
            )
        ]


class Result(models.Model):
    """One tester's draft or immutable submission for a case/build (RES-2)."""

    class Outcome(models.TextChoices):
        """The two tester-selected outcomes."""

        PASS = "pass", "Pass"
        FAIL = "fail", "Fail"

    tester = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="results"
    )
    case = models.ForeignKey(Case, on_delete=models.PROTECT, related_name="results")
    build = models.ForeignKey(Build, on_delete=models.PROTECT, related_name="results")
    outcome = models.CharField(max_length=4, choices=Outcome.choices)
    observation = models.CharField(max_length=2000, blank=True, default="")
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tester", "case", "build"], name="rounds_result_tuple_unique"
            ),
            models.CheckConstraint(
                condition=models.Q(outcome__in=["pass", "fail"]),
                name="rounds_result_outcome_valid",
            ),
        ]
