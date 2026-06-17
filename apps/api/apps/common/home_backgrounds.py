from __future__ import annotations

import mimetypes
import re
from pathlib import Path
from urllib.parse import quote

from django.conf import settings
from django.http import Http404, HttpResponse, JsonResponse
from django.views.decorators.http import require_GET

IMAGE_FILE_PATTERN = re.compile(r"^[a-zA-Z0-9._-]+\.(?:jpe?g|png|webp|avif)$", re.IGNORECASE)
IMAGE_NAME_ORDER: dict[str, int] = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
}


def _get_image_directory() -> Path:
    return Path(settings.BASE_DIR) / "uploads" / "images"


def _iter_home_background_paths() -> list[Path]:
    image_directory = _get_image_directory()
    if not image_directory.exists():
        return []

    return sorted(
        (
            path
            for path in image_directory.iterdir()
            if path.is_file() and IMAGE_FILE_PATTERN.fullmatch(path.name)
        ),
        key=lambda path: (
            IMAGE_NAME_ORDER.get(path.stem.lower(), float("inf")),
            path.name.lower(),
        ),
    )


def _get_home_background_path(name: str) -> Path:
    if not IMAGE_FILE_PATTERN.fullmatch(name):
        raise Http404("Unsupported image.")

    image_path = _get_image_directory() / Path(name).name
    if not image_path.is_file():
        raise Http404("Image not found.")

    return image_path


@require_GET
def home_background_manifest(request):
    return JsonResponse(
        {
            "images": [
                {
                    "name": image_path.name,
                    "url": request.build_absolute_uri(
                        f"/api/home-backgrounds/{quote(image_path.name)}"
                    ),
                }
                for image_path in _iter_home_background_paths()
            ]
        }
    )


@require_GET
def home_background_image(_request, name: str):
    image_path = _get_home_background_path(name)
    content_type = mimetypes.guess_type(image_path.name)[0] or "application/octet-stream"
    response = HttpResponse(image_path.read_bytes(), content_type=content_type)
    response["Cache-Control"] = "public, max-age=3600, stale-while-revalidate=86400"
    return response
