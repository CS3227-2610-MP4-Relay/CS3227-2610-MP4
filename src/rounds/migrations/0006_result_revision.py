"""Give existing and new results a saved revision for stale-form checks."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("rounds", "0005_result")]

    operations = [
        migrations.AddField(
            model_name="result",
            name="revision",
            field=models.PositiveBigIntegerField(default=1, db_default=1),
        ),
    ]
