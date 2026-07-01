from django.test import SimpleTestCase

from apps.verification.models import VerificationAttempt
from apps.verification.serializers import VerificationSubmissionSerializer


class VerificationSubmissionSerializerTests(SimpleTestCase):
    def test_biodata_mobile_number_accepts_local_format(self):
        serializer = VerificationSubmissionSerializer(
            data={
                "verification_type": VerificationAttempt.VerificationType.BIODATA,
                "first_name": "Christian",
                "middle_name": "Odezi",
                "surname": "Aluya",
                "date_of_birth": "1977-02-06",
                "gender": "male",
                "mobile_number": "08099446062",
                "state_of_origin": "Delta",
                "country_of_birth": "Nigeria",
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["mobile_number"], "08099446062")

    def test_biodata_mobile_number_requires_zero_when_not_using_plus_234(self):
        serializer = VerificationSubmissionSerializer(
            data={
                "verification_type": VerificationAttempt.VerificationType.BIODATA,
                "first_name": "Christian",
                "middle_name": "Odezi",
                "surname": "Aluya",
                "date_of_birth": "1977-02-06",
                "gender": "male",
                "mobile_number": "8099446062",
                "state_of_origin": "Delta",
                "country_of_birth": "Nigeria",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            serializer.errors["mobile_number"][0],
            "Enter a valid Nigerian mobile number starting with 0 or +234.",
        )

    def test_biodata_requires_middle_name_state_and_country(self):
        serializer = VerificationSubmissionSerializer(
            data={
                "verification_type": VerificationAttempt.VerificationType.BIODATA,
                "first_name": "Christian",
                "surname": "Aluya",
                "date_of_birth": "1977-02-06",
                "gender": "male",
                "mobile_number": "08099446062",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors["middle_name"][0], "This value is required.")
        self.assertEqual(serializer.errors["state_of_origin"][0], "This value is required.")
        self.assertEqual(serializer.errors["country_of_birth"][0], "This value is required.")
