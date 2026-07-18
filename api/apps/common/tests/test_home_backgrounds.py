from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase


class HomeBackgroundAPITests(SimpleTestCase):
    def test_manifest_lists_images_in_expected_order(self):
        with TemporaryDirectory() as temp_dir:
            image_dir = Path(temp_dir) / "uploads" / "images"
            image_dir.mkdir(parents=True)
            for name in ("three.jpg", "one.jpg", "two.jpeg"):
                (image_dir / name).write_bytes(b"image-bytes")

            with self.settings(BASE_DIR=Path(temp_dir)):
                response = self.client.get("/api/home-backgrounds/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["images"],
            [
                {
                    "name": "one.jpg",
                    "url": "http://testserver/api/home-backgrounds/one.jpg",
                },
                {
                    "name": "two.jpeg",
                    "url": "http://testserver/api/home-backgrounds/two.jpeg",
                },
                {
                    "name": "three.jpg",
                    "url": "http://testserver/api/home-backgrounds/three.jpg",
                },
            ],
        )

    def test_image_route_rejects_invalid_names(self):
        response = self.client.get("/api/home-backgrounds/passwd.txt")

        self.assertEqual(response.status_code, 404)
