import os
from unittest.mock import patch

from django.test import SimpleTestCase

from config.settings.base import build_storages, env_optional


class StorageSettingsTests(SimpleTestCase):
    def test_env_optional_converts_blank_to_none(self):
        with patch.dict(os.environ, {"TEST_OPTIONAL_ENV": "   "}):
            self.assertIsNone(env_optional("TEST_OPTIONAL_ENV"))

    def test_env_optional_returns_stripped_value(self):
        with patch.dict(os.environ, {"TEST_OPTIONAL_ENV": " https://s3.amazonaws.com "}):
            self.assertEqual(env_optional("TEST_OPTIONAL_ENV"), "https://s3.amazonaws.com")

    def test_uses_local_media_storage_without_bucket(self):
        storages = build_storages("")

        self.assertEqual(
            storages["default"]["BACKEND"],
            "django.core.files.storage.FileSystemStorage",
        )
        self.assertEqual(
            storages["staticfiles"]["BACKEND"],
            "whitenoise.storage.CompressedManifestStaticFilesStorage",
        )

    def test_uses_s3_media_storage_with_bucket(self):
        storages = build_storages("corpershub-dev-media")

        self.assertEqual(
            storages["default"]["BACKEND"],
            "apps.common.storage.PublicMediaStorage",
        )
