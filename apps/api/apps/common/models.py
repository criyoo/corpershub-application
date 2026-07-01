import uuid

from django.conf import settings
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UUIDPrimaryKeyModel(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class CourseField(UUIDPrimaryKeyModel):
    name = models.CharField(max_length=255, unique=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "name")
        verbose_name = "Course field"
        verbose_name_plural = "Course fields"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.name = self.name.strip()
        super().save(*args, **kwargs)


class CourseCategory(UUIDPrimaryKeyModel):
    field = models.ForeignKey(CourseField, on_delete=models.CASCADE, related_name="categories")
    name = models.CharField(max_length=255)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "name")
        unique_together = ("field", "name")
        verbose_name = "Course category"
        verbose_name_plural = "Course categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.name = self.name.strip()
        super().save(*args, **kwargs)


class UniversityCourse(UUIDPrimaryKeyModel):
    category = models.ForeignKey(CourseCategory, on_delete=models.CASCADE, related_name="courses")
    name = models.CharField(max_length=255)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "name")
        unique_together = ("category", "name")
        verbose_name = "University course"
        verbose_name_plural = "University courses"
        indexes = [
            models.Index(fields=("name",)),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.name = self.name.strip()
        super().save(*args, **kwargs)


class SeededUser(UUIDPrimaryKeyModel):
    class SeedType(models.TextChoices):
        COMPANY = "company", "Company"
        CORPER = "corper", "Corper"

    seed_type = models.CharField(max_length=20, choices=SeedType.choices)
    seed_key = models.CharField(max_length=120)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="seed_record",
    )

    class Meta:
        ordering = ("seed_type", "seed_key")
        unique_together = ("seed_type", "seed_key")
        indexes = [
            models.Index(fields=("seed_type", "seed_key"), name="common_seeded_user_idx"),
        ]

    def __str__(self):
        return f"{self.seed_type}:{self.seed_key}"
