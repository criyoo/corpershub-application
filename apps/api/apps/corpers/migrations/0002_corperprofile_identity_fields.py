from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("corpers", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="corperprofile",
            name="country_of_birth",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.AddField(
            model_name="corperprofile",
            name="first_name",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.AddField(
            model_name="corperprofile",
            name="middle_name",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.AddField(
            model_name="corperprofile",
            name="state_of_origin",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.AddField(
            model_name="corperprofile",
            name="surname",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
    ]
