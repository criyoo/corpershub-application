from django.db import migrations
from django.utils import timezone


def sync_verified_biodata_attempts(apps, schema_editor):
    CorperProfile = apps.get_model("corpers", "CorperProfile")
    VerificationAttempt = apps.get_model("verification", "VerificationAttempt")
    now = timezone.now()

    for corper_id in (
        CorperProfile.objects.filter(biodata_verification_status="verified")
        .values_list("id", flat=True)
        .iterator()
    ):
        latest_biodata_attempt = (
            VerificationAttempt.objects.filter(corper_id=corper_id, verification_type="biodata")
            .exclude(status__in=["approved", "failed"])
            .order_by("-created_at")
            .first()
        )
        if latest_biodata_attempt is None:
            continue

        VerificationAttempt.objects.filter(pk=latest_biodata_attempt.pk).update(
            status="approved",
            updated_at=now,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("verification", "0003_split_dikriptverificationcache"),
    ]

    operations = [
        migrations.RunPython(sync_verified_biodata_attempts, migrations.RunPython.noop),
    ]
