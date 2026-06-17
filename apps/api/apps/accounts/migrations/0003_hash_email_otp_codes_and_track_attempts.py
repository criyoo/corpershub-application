from django.contrib.auth.hashers import identify_hasher, make_password
from django.db import migrations, models


def hash_existing_email_otp_codes(apps, schema_editor):
    EmailOTP = apps.get_model("accounts", "EmailOTP")
    for otp in EmailOTP.objects.all().iterator():
        code_hash = (otp.code_hash or "").strip()
        if not code_hash:
            continue
        try:
            identify_hasher(code_hash)
            continue
        except ValueError:
            pass
        otp.code_hash = make_password(code_hash.upper())
        otp.save(update_fields=["code_hash"])


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_alter_emailotp_purpose"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="emailotp",
            name="accounts_em_email_814cb4_idx",
        ),
        migrations.RemoveIndex(
            model_name="emailotp",
            name="accounts_em_code_b660c8_idx",
        ),
        migrations.RenameField(
            model_name="emailotp",
            old_name="code",
            new_name="code_hash",
        ),
        migrations.AlterField(
            model_name="emailotp",
            name="code_hash",
            field=models.CharField(max_length=255),
        ),
        migrations.AddField(
            model_name="emailotp",
            name="attempt_count",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.RunPython(hash_existing_email_otp_codes, migrations.RunPython.noop),
        migrations.AddIndex(
            model_name="emailotp",
            index=models.Index(
                fields=["email", "purpose", "consumed_at", "-created_at"],
                name="accounts_emailotp_active_idx",
            ),
        ),
    ]
