from django.test import TestCase

from apps.common.models import CourseCategory, CourseField, UniversityCourse


class CourseCatalogAPITests(TestCase):
    def setUp(self):
        self.course_field, _ = CourseField.objects.get_or_create(
            name="Testing University Courses",
            defaults={"sort_order": 1},
        )
        management, _ = CourseCategory.objects.get_or_create(
            field=self.course_field,
            name="Management Sciences & Business",
            defaults={"sort_order": 2},
        )
        sciences, _ = CourseCategory.objects.get_or_create(
            field=self.course_field,
            name="Natural & Applied Sciences",
            defaults={"sort_order": 1},
        )
        UniversityCourse.objects.get_or_create(
            category=management,
            name="Accounting",
            defaults={"sort_order": 2},
        )
        UniversityCourse.objects.get_or_create(
            category=management,
            name="Business Administration",
            defaults={"sort_order": 1},
        )
        UniversityCourse.objects.get_or_create(
            category=sciences,
            name="Computer Science",
            defaults={"sort_order": 1},
        )

    def test_course_catalog_endpoint_returns_grouped_fields_categories_and_courses(self):
        response = self.client.get("/api/common/course-catalog/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        field_payload = next(field for field in payload["fields"] if field["id"] == str(self.course_field.id))

        self.assertEqual(
            field_payload,
            {
                "id": str(self.course_field.id),
                "name": "Testing University Courses",
                "categories": [
                    {
                        "id": str(
                            CourseCategory.objects.get(
                                field=self.course_field,
                                name="Natural & Applied Sciences",
                            ).id
                        ),
                        "name": "Natural & Applied Sciences",
                        "courses": [
                            {
                                "id": str(
                                    UniversityCourse.objects.get(
                                        category__field=self.course_field,
                                        name="Computer Science",
                                    ).id
                                ),
                                "name": "Computer Science",
                            }
                        ],
                    },
                    {
                        "id": str(
                            CourseCategory.objects.get(
                                field=self.course_field,
                                name="Management Sciences & Business",
                            ).id
                        ),
                        "name": "Management Sciences & Business",
                        "courses": [
                            {
                                "id": str(
                                    UniversityCourse.objects.get(
                                        category__field=self.course_field,
                                        name="Business Administration",
                                    ).id
                                ),
                                "name": "Business Administration",
                            },
                            {
                                "id": str(
                                    UniversityCourse.objects.get(
                                        category__field=self.course_field,
                                        name="Accounting",
                                    ).id
                                ),
                                "name": "Accounting",
                            },
                        ],
                    },
                ],
            },
        )
