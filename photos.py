import os
import uuid

from PIL import Image


MAX_DIMENSION = 1920  # longest edge
JPEG_QUALITY = 80     # targets roughly 500KB–1MB for most photos


def save_uploaded_photo(file_storage, upload_folder):
    """Compress/resize an uploaded photo and save it. Returns the filename."""
    ext = "jpg"
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(upload_folder, filename)

    img = Image.open(file_storage.stream)

    # Handle EXIF orientation
    try:
        from PIL import ImageOps
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass

    # Convert to RGB (handles RGBA, palette, etc.)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    # Resize if larger than MAX_DIMENSION
    if max(img.size) > MAX_DIMENSION:
        img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)

    img.save(filepath, "JPEG", quality=JPEG_QUALITY, optimize=True)
    return filename


def delete_photo_file(upload_folder, filename):
    """Delete a photo file from disk."""
    filepath = os.path.join(upload_folder, filename)
    if os.path.isfile(filepath):
        os.remove(filepath)
