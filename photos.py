"""Saving uploaded bathroom photos.

Used only by the /add form, which only exists while developing. Every photo
that reaches public/static/photos/ goes through save_upload(), so there is one
place where "what a committed photo looks like" is decided.

Pillow docs: https://pillow.readthedocs.io/en/stable/reference/Image.html
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from PIL import Image, ImageOps

import data

# Big enough to stay sharp on a laptop, small enough that a popup with several
# photos is not a slow download. Phone photos arrive around 8000px wide.
MAX_EDGE = 1600
JPEG_QUALITY = 82

ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".tif", ".tiff"}


class PhotoError(Exception):
    """An uploaded file could not be saved as a photo."""


def slugify(text: str) -> str:
    """'Wheeler Hall, 4th floor' -> 'wheeler-hall-4th-floor'."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    hyphenated = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")
    return re.sub(r"-{2,}", "-", hyphenated)


def unique_filename(stem: str) -> str:
    """A '<stem>.jpg' that is not already taken, adding -2, -3 ... if needed."""
    candidate = f"{stem}.jpg"
    counter = 2
    while (data.PHOTO_DIR / candidate).exists():
        candidate = f"{stem}-{counter}.jpg"
        counter += 1
    return candidate


def save_upload(uploaded, stem: str) -> str:
    """Resize, strip metadata, and save one uploaded photo. Returns its filename.

    The metadata stripping is the part that matters. Phones embed EXIF in every
    photo -- GPS coordinates of where it was taken, the exact timestamp, the
    device. This repository is public, so a photo saved straight off a phone
    would publish where you were and when. Building a new image from the pixel
    bytes alone leaves all of that behind, because only the pixels are copied.
    """
    suffix = Path(uploaded.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise PhotoError(
            f"{uploaded.filename!r} is not an image this can read "
            f"({', '.join(sorted(ALLOWED_SUFFIXES))})"
        )

    try:
        image = Image.open(uploaded.stream)
    except OSError as exc:
        raise PhotoError(f"{uploaded.filename!r} could not be opened: {exc}") from None

    with image:
        # Phones record orientation in EXIF rather than rotating the pixels.
        # Apply it before the metadata is dropped, or the photo silently
        # displays sideways.
        image = ImageOps.exif_transpose(image)

        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")

        image.thumbnail((MAX_EDGE, MAX_EDGE), Image.LANCZOS)

        # Only the pixels are carried over -- no EXIF, no GPS, no timestamp.
        clean = Image.frombytes(image.mode, image.size, image.tobytes())

        data.PHOTO_DIR.mkdir(parents=True, exist_ok=True)
        filename = unique_filename(stem)
        clean.save(data.PHOTO_DIR / filename, "JPEG",
                   quality=JPEG_QUALITY, optimize=True)

    return filename
