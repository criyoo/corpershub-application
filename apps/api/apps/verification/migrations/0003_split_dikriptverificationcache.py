import uuid

from django.db import migrations, models


def copy_dikript_cache_records(apps, schema_editor):
    DikriptVerificationCache = apps.get_model("verification", "DikriptVerificationCache")
    NINDikriptVerificationCache = apps.get_model("verification", "NINDikriptVerificationCache")
    CACDikriptVerificationCache = apps.get_model("verification", "CACDikriptVerificationCache")

    nin_records = []
    cac_records = []

    for record in DikriptVerificationCache.objects.all().iterator():
        target = {
            "id": record.id,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
            "lookup_hash": record.lookup_hash,
            "payload": record.payload,
            "fetched_at": record.fetched_at,
        }
        if record.verification_type == "nin":
            nin_records.append(NINDikriptVerificationCache(**target))
        elif record.verification_type == "cac":
            cac_records.append(CACDikriptVerificationCache(**target))

    if nin_records:
        NINDikriptVerificationCache.objects.bulk_create(nin_records, ignore_conflicts=True)
    if cac_records:
        CACDikriptVerificationCache.objects.bulk_create(cac_records, ignore_conflicts=True)


class Migration(migrations.Migration):
    dependencies = [
        ("verification", "0002_dikriptverificationcache"),
    ]

    operations = [
        migrations.CreateModel(
            name="NINDikriptVerificationCache",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("lookup_hash", models.CharField(db_index=True, max_length=64)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("fetched_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "verification_nin_dikriptverificationcache",
                "ordering": ["-updated_at"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("lookup_hash",),
                        name="verification_unique_nin_dikript_lookup_cache",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="CACDikriptVerificationCache",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("lookup_hash", models.CharField(db_index=True, max_length=64)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("fetched_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "verification_cac_dikriptverificationcache",
                "ordering": ["-updated_at"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("lookup_hash",),
                        name="verification_unique_cac_dikript_lookup_cache",
                    )
                ],
            },
        ),
        migrations.RunPython(copy_dikript_cache_records, migrations.RunPython.noop),
        migrations.DeleteModel(
            name="DikriptVerificationCache",
        ),
    ]
