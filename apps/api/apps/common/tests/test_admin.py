from django.contrib import admin
from django.test import RequestFactory, TestCase

from apps.accounts.models import User
from apps.common.admin import CourseCategoryInline, UniversityCourseInline
from apps.common.models import CourseCategory, CourseField, UniversityCourse


class CourseCatalogAdminTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            email="admin@example.com",
            password="StrongPass123!",
        )
        self.request = RequestFactory().get("/")
        self.request.user = self.superuser

        self.course_field, _ = CourseField.objects.get_or_create(
            name="University Courses",
            defaults={"sort_order": 1},
        )
        self.category, _ = CourseCategory.objects.get_or_create(
            field=self.course_field,
            name="Engineering & Technology",
            defaults={"sort_order": 2},
        )
        self.course, _ = UniversityCourse.objects.get_or_create(
            category=self.category,
            name="Computer Engineering",
            defaults={"sort_order": 3},
        )

    def test_course_catalog_models_are_registered(self):
        self.assertIn(CourseField, admin.site._registry)
        self.assertIn(CourseCategory, admin.site._registry)
        self.assertIn(UniversityCourse, admin.site._registry)

    def test_course_field_admin_exposes_category_inline(self):
        admin_instance = admin.site._registry[CourseField]

        self.assertIn(CourseCategoryInline, admin_instance.inlines)

    def test_course_category_admin_exposes_course_inline(self):
        admin_instance = admin.site._registry[CourseCategory]

        self.assertIn(UniversityCourseInline, admin_instance.inlines)

    def test_course_admin_resolves_parent_field_name(self):
        admin_instance = admin.site._registry[UniversityCourse]

        self.assertEqual(admin_instance.field_name(self.course), "University Courses")
