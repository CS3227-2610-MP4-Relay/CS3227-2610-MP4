"""Test rounds owned by a workspace (RND)."""

from django.db import models

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
