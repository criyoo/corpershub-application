from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("companies", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="companyprofile",
            name="company_registration_date",
            field=models.DateField(blank=True, null=True),
        ),
    ]
