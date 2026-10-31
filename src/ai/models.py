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


class CallRecord(models.Model):
    """One scope's quota row and nullable metrics for a counted gateway call."""

    scope = models.CharField(max_length=32)
    key = models.CharField(max_length=64)
    created_at = models.DateTimeField()
    prompt_tokens = models.PositiveBigIntegerField(null=True)
    completion_tokens = models.PositiveBigIntegerField(null=True)
    total_tokens = models.PositiveBigIntegerField(null=True)
    elapsed_ms = models.PositiveBigIntegerField(null=True)

    class Meta:
        indexes = [
            models.Index(fields=["scope", "key", "created_at"]),
        ]
