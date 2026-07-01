from django.db import migrations, models


def rename_success_statuses(apps, schema_editor):
    PaymentTransaction = apps.get_model("payments", "PaymentTransaction")
    FlutterwavePaymentRecord = apps.get_model("payments", "FlutterwavePaymentRecord")

    PaymentTransaction.objects.filter(status="success").update(status="successful")
    FlutterwavePaymentRecord.objects.filter(status="success").update(status="successful")


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(rename_success_statuses, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="paymenttransaction",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("processing", "Processing"),
                    ("successful", "Successful"),
                    ("failed", "Failed"),
                    ("cancelled", "Cancelled"),
                    ("expired", "Expired"),
                    ("abandoned", "Abandoned"),
                ],
                default="pending",
                max_length=20,
            ),
        ),
    ]
