from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("companies", "0003_companyprofile_approval_status_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="companyprofile",
            name="accommodation_provided",
            field=models.CharField(blank=True, default="", max_length=32),
        ),
        migrations.AlterField(
            model_name="companyprofile",
            name="placement_type",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
    ]
