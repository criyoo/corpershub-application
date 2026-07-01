import json
from pathlib import Path

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


DEFAULT_COURSE_FIELD_NAME = "University Courses"
COURSE_SEED_FILENAME = "Nigerian_Universities_Accredited_Courses.json"


def seed_course_catalog(apps, _schema_editor):
    course_field_model = apps.get_model("common", "CourseField")
    course_category_model = apps.get_model("common", "CourseCategory")
    university_course_model = apps.get_model("common", "UniversityCourse")

    seed_path = Path(__file__).resolve().parents[3] / "uploads" / "courses" / COURSE_SEED_FILENAME
    if not seed_path.exists():
        return

    payload = json.loads(seed_path.read_text())
    grouped_courses = payload.get("fields", {})
    if not isinstance(grouped_courses, dict) or not grouped_courses:
        return

    course_field, _ = course_field_model.objects.get_or_create(
        name=DEFAULT_COURSE_FIELD_NAME,
        defaults={"sort_order": 0},
    )

    for category_index, (category_name, courses) in enumerate(grouped_courses.items()):
        if not category_name or not isinstance(courses, list):
            continue

        category, _ = course_category_model.objects.get_or_create(
            field=course_field,
            name=category_name.strip(),
            defaults={"sort_order": category_index},
        )

        for course_index, course_name in enumerate(courses):
            normalized_course_name = str(course_name).strip()
            if not normalized_course_name:
                continue

            university_course_model.objects.get_or_create(
                category=category,
                name=normalized_course_name,
                defaults={"sort_order": course_index},
            )


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CourseField",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255, unique=True)),
                ("sort_order", models.PositiveIntegerField(default=0)),
            ],
            options={
                "verbose_name": "Course field",
                "verbose_name_plural": "Course fields",
                "ordering": ("sort_order", "name"),
            },
        ),
        migrations.CreateModel(
            name="CourseCategory",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                (
                    "field",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="categories", to="common.coursefield"),
                ),
            ],
            options={
                "verbose_name": "Course category",
                "verbose_name_plural": "Course categories",
                "ordering": ("sort_order", "name"),
                "unique_together": {("field", "name")},
            },
        ),
        migrations.CreateModel(
            name="UniversityCourse",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                (
                    "category",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="courses", to="common.coursecategory"),
                ),
            ],
            options={
                "verbose_name": "University course",
                "verbose_name_plural": "University courses",
                "ordering": ("sort_order", "name"),
                "unique_together": {("category", "name")},
            },
        ),
        migrations.AddIndex(
            model_name="universitycourse",
            index=models.Index(fields=["name"], name="common_univ_name_b8273b_idx"),
        ),
        migrations.CreateModel(
            name="SeededUser",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("seed_type", models.CharField(choices=[("company", "Company"), ("corper", "Corper")], max_length=20)),
                ("seed_key", models.CharField(max_length=120)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="seed_record",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("seed_type", "seed_key"),
                "unique_together": {("seed_type", "seed_key")},
            },
        ),
        migrations.AddIndex(
            model_name="seededuser",
            index=models.Index(fields=["seed_type", "seed_key"], name="common_seeded_user_idx"),
        ),
        migrations.RunPython(seed_course_catalog, migrations.RunPython.noop),
    ]
