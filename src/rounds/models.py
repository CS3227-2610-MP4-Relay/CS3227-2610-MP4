"""Test rounds owned by a workspace (RND)."""

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
