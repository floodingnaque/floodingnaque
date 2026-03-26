"""Photo service - image validation, EXIF stripping, compression, and upload.

Supports Supabase Storage in production and local file storage in
development (simulation mode when ``SUPABASE_URL`` is unset).

Compression pipeline (applied automatically on every upload):
    1. EXIF metadata stripped (privacy)
    2. Resized to fit within ``MAX_DIMENSION`` (default 1920 px)
    3. Re-encoded as JPEG at ``JPEG_QUALITY`` (default 75)

A typical 4 MB phone photo (4032x3024) shrinks to ~150–250 KB.
"""

import io
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple

logger = logging.getLogger(__name__)

# ── Upload constraints ──────────────────────────────────────────────────
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB (pre-compression upload limit)

# ── Compression settings ────────────────────────────────────────────────
MAX_DIMENSION: int = int(os.getenv("PHOTO_MAX_DIMENSION", "1280"))
"""Longest edge in pixels - images larger than this are down-scaled
proportionally.  1280 px is sufficient for flood evidence."""

JPEG_QUALITY: int = int(os.getenv("PHOTO_JPEG_QUALITY", "60"))
"""JPEG encoder quality (1–95).  60 keeps flood evidence clearly
visible while minimising database/storage footprint."""

# ── Accepted magic bytes ────────────────────────────────────────────────
_MAGIC_BYTES = {
    "jpeg": b"\xff\xd8\xff",
    "png": b"\x89PNG",
    "webp_riff": b"RIFF",
}
_WEBP_MARKER = b"WEBP"


def validate_image(file_storage) -> Tuple[bool, str]:  # type: ignore[no-untyped-def]
    """Validate an uploaded image by checking magic bytes and size.

    Args:
        file_storage: A Werkzeug ``FileStorage`` object (or any object
            with ``.read()`` and ``.seek()``).

    Returns:
        (valid, error_message) - ``error_message`` is empty on success.
    """
    try:
        # Read header bytes without consuming the entire stream
        header = file_storage.read(12)
        file_storage.seek(0)

        if not header:
            return False, "Empty file"

        is_jpeg = header[:3] == _MAGIC_BYTES["jpeg"]
        is_png = header[:4] == _MAGIC_BYTES["png"]
        is_webp = header[:4] == _MAGIC_BYTES["webp_riff"] and header[8:12] == _WEBP_MARKER

        if not (is_jpeg or is_png or is_webp):
            return False, "Unsupported image format - only JPEG, PNG, and WebP are accepted"

        # Check size
        file_storage.seek(0, os.SEEK_END)
        size = file_storage.tell()
        file_storage.seek(0)

        if size > MAX_IMAGE_SIZE:
            return False, f"Image exceeds maximum size of {MAX_IMAGE_SIZE // (1024 * 1024)} MB"

        return True, ""

    except Exception as exc:
        logger.warning("Image validation error: %s", exc)
        return False, f"Validation error: {exc}"


def compress_image(
    image_bytes: bytes,
    *,
    max_dimension: int | None = None,
    jpeg_quality: int | None = None,
) -> bytes:
    """Strip EXIF metadata, resize, and re-encode an image as compressed JPEG.

    This is the single entry-point that replaces the old ``strip_exif``
    function.  It performs three operations in order:

    1. **EXIF removal** - copies pixel data to a fresh ``Image`` so no
       metadata (GPS, camera serial, timestamps) survives.
    2. **Down-scale** - if either dimension exceeds *max_dimension* the
       image is proportionally resized using Lanczos resampling.
    3. **JPEG re-encode** - saved at *jpeg_quality* (default 75).

    Args:
        image_bytes: Raw image bytes (JPEG, PNG, or WebP).
        max_dimension: Override for ``MAX_DIMENSION`` module default.
        jpeg_quality: Override for ``JPEG_QUALITY`` module default.

    Returns:
        Compressed JPEG bytes with no metadata.
    """
    _max_dim = max_dimension if max_dimension is not None else MAX_DIMENSION
    _quality = jpeg_quality if jpeg_quality is not None else JPEG_QUALITY

    try:
        from PIL import Image

        src = Image.open(io.BytesIO(image_bytes))
        original_size = len(image_bytes)

        # ── 1. Strip EXIF - copy pixel data into a clean image ──────────
        clean = Image.new(src.mode, src.size)
        clean.putdata(list(src.getdata()))

        # Convert to RGB if necessary (RGBA PNGs, palettised, etc.)
        if clean.mode in ("RGBA", "P", "LA"):
            clean = clean.convert("RGB")

        # ── 2. Down-scale to fit within max_dimension ───────────────────
        w, h = clean.size
        if max(w, h) > _max_dim:
            ratio = _max_dim / max(w, h)
            new_w = int(w * ratio)
            new_h = int(h * ratio)
            resample = getattr(Image, "LANCZOS", getattr(Image, "ANTIALIAS", 1))
            clean = clean.resize((new_w, new_h), resample)
            logger.info(
                "Image resized from %dx%d to %dx%d (max_dimension=%d)",
                w,
                h,
                new_w,
                new_h,
                _max_dim,
            )

        # ── 3. Re-encode as JPEG ───────────────────────────────────────
        buf = io.BytesIO()
        clean.save(buf, format="JPEG", quality=_quality, optimize=True)
        compressed = buf.getvalue()

        ratio_pct = (1 - len(compressed) / original_size) * 100 if original_size else 0
        logger.info(
            "Image compressed: %d KB → %d KB (%.0f%% reduction, quality=%d)",
            original_size // 1024,
            len(compressed) // 1024,
            ratio_pct,
            _quality,
        )
        return compressed

    except ImportError:
        logger.warning("Pillow not installed - returning image without compression")
        return image_bytes
    except Exception as exc:
        logger.warning("Image compression failed: %s - returning original bytes", exc)
        return image_bytes


# Backward-compatible alias so callers using the old name still work.
strip_exif = compress_image


def upload_photo(image_bytes: bytes, report_id: int) -> str:
    """Upload a report photo to Supabase Storage or local filesystem.

    Simulation mode: when ``SUPABASE_URL`` is unset, saves to
    ``backend/static/uploads/reports/<date>/<report_id>.jpg`` and
    returns a local URL path.

    Args:
        image_bytes: EXIF-stripped JPEG bytes.
        report_id: Associated CommunityReport ID.

    Returns:
        Public URL or local path to the uploaded image.
    """
    date_prefix = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY", "")
    bucket = os.getenv("SUPABASE_STORAGE_BUCKET", "report-photos")

    # ── Supabase Storage mode ────────────────────────────────────────────
    if supabase_url and supabase_key:
        try:
            from supabase import create_client

            client = create_client(supabase_url, supabase_key)
            file_path_in_bucket = f"{date_prefix}/{report_id}.jpg"

            client.storage.from_(bucket).upload(
                file_path_in_bucket,
                image_bytes,
                file_options={"content-type": "image/jpeg", "upsert": "true"},
            )

            public_url = client.storage.from_(bucket).get_public_url(file_path_in_bucket)
            logger.info("Photo uploaded to Supabase: %s", public_url)
            return public_url

        except Exception as exc:
            logger.warning("Supabase upload failed (%s) - falling back to local storage", exc)

    # ── Simulation / local mode ──────────────────────────────────────────
    base_dir = Path(__file__).resolve().parent.parent.parent  # backend/
    upload_dir = base_dir / "static" / "uploads" / "reports" / date_prefix
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_path = upload_dir / f"{report_id}.jpg"
    file_path.write_bytes(image_bytes)

    local_url = f"/static/uploads/reports/{date_prefix}/{report_id}.jpg"
    logger.info("Photo saved locally: %s", local_url)
    return local_url
