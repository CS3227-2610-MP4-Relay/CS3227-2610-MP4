"""Seed the fixed deployment-wide gateway locks."""

from datetime import timedelta

from django.db import migrations
from django.utils import timezone


def seed(apps, schema_editor):
    """Create the two deployment slots and the reserved metrics row."""
    CallSlot = apps.get_model("ai", "CallSlot")
    Usage = apps.get_model("ai", "Usage")
    expired = timezone.now() - timedelta(seconds=1)
    for key in ("0", "1"):
        CallSlot.objects.get_or_create(
            scope="deployment", key=key, defaults={"expires_at": expired}
        )
    Usage.objects.get_or_create(
        scope="deployment-calls",
        key="all",
        defaults={"window_start": expired, "count": 0},
    )


def unseed(apps, schema_editor):
    """Remove only the fixed rows this migration created."""
    CallSlot = apps.get_model("ai", "CallSlot")
    Usage = apps.get_model("ai", "Usage")
    CallSlot.objects.filter(scope="deployment", key__in=("0", "1")).delete()
    Usage.objects.filter(scope="deployment-calls", key="all").delete()


class Migration(migrations.Migration):
    """Add the deployment-wide rows used by the gateway locks."""

    dependencies = [("ai", "0001_initial")]

    operations = [migrations.RunPython(seed, unseed)]
