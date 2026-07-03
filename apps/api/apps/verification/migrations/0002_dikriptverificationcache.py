import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("verification", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="DikriptVerificationCache",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("verification_type", models.CharField(choices=[("nin", "NIN"), ("cac", "CAC")], max_length=12)),
                ("lookup_hash", models.CharField(db_index=True, max_length=64)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("fetched_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["-updated_at"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("verification_type", "lookup_hash"),
                        name="verification_unique_dikript_lookup_cache",
                    )
                ],
            },
        ),
    ]
