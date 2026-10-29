"""Operational records for the shared LLM gateway; no prompts or replies."""

from django.db import models


class CallSlot(models.Model):
    """A live or expired reservation of a per-user or deployment call slot."""

    scope = models.CharField(max_length=32)
    key = models.CharField(max_length=64)
    expires_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["scope", "key"], name="ai_callslot_scope_key"
            )
        ]


class Usage(models.Model):
    """A rolling count of gateway calls for one quota scope and key."""

    scope = models.CharField(max_length=32)
    key = models.CharField(max_length=64)
    window_start = models.DateTimeField()
    count = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["scope", "key"], name="ai_usage_scope_key")
        ]
