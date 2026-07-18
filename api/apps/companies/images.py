from io import BytesIO
from pathlib import Path

from django.core.files.base import ContentFile
from PIL import Image, ImageOps


COMPANY_PROFILE_IMAGE_SIZE = (1600, 1200)
COMPANY_PROFILE_IMAGE_QUALITY = 86


def process_company_profile_image(uploaded_file) -> ContentFile:
    image = Image.open(uploaded_file)
    image = ImageOps.exif_transpose(image)
    image = image.convert("RGB")
    image = ImageOps.fit(
        image,
        COMPANY_PROFILE_IMAGE_SIZE,
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )

    output = BytesIO()
    image.save(
        output,
        format="WEBP",
        quality=COMPANY_PROFILE_IMAGE_QUALITY,
        method=6,
        optimize=True,
    )
    output.seek(0)

    original_name = Path(getattr(uploaded_file, "name", "company-image")).stem or "company-image"
    return ContentFile(output.read(), name=f"{original_name}.webp")
