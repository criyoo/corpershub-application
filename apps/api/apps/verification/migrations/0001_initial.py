import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('corpers', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='VerificationAttempt',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('verification_type', models.CharField(choices=[('biodata', 'Biodata'), ('nin', 'NIN'), ('callup', 'NYSC Call-up'), ('state_code', 'NYSC State Code'), ('profile', 'Profile')], max_length=20)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('failed', 'Failed'), ('rejected', 'Rejected')], default='pending', max_length=20)),
                ('submitted_value_masked', models.CharField(blank=True, max_length=255)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('review_note', models.TextField(blank=True)),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='verification_reviews', to=settings.AUTH_USER_MODEL)),
                ('corper', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='verification_attempts', to='corpers.corperprofile')),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [models.Index(fields=['verification_type', 'status'], name='verificatio_verific_196cc0_idx')],
            },
        ),
        migrations.CreateModel(
            name="CorperVerification",
            fields=[],
            options={
                "verbose_name": "Verification",
                "verbose_name_plural": "Verifications",
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("corpers.corperprofile",),
        ),
    ]
