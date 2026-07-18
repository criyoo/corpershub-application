import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("companies", "0001_initial"),
        ("corpers", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Interest",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("message", models.CharField(blank=True, max_length=255)),
                (
                    "status",
                    models.CharField(
                        choices=[("expressed", "Expressed"), ("contacted", "Contacted"), ("archived", "Archived")],
                        default="expressed",
                        max_length=20,
                    ),
                ),
                ("corper_expressed_at", models.DateTimeField(blank=True, null=True)),
                ("company_expressed_at", models.DateTimeField(blank=True, null=True)),
                ("viewed_by_company_at", models.DateTimeField(blank=True, null=True)),
                ("viewed_by_corper_at", models.DateTimeField(blank=True, null=True)),
                (
                    "company",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="interested_corpers",
                        to="companies.companyprofile",
                    ),
                ),
                (
                    "corper",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="interests",
                        to="corpers.corperprofile",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="interest",
            constraint=models.UniqueConstraint(fields=("corper", "company"), name="unique_interest_pair"),
        ),
    ]
