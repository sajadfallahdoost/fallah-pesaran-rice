from django.conf import settings
from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError

ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP", "AVIF"}


def validate_image_upload(file) -> None:
    """Size and real-content checks for uploaded images (extension alone is not trusted)."""
    if file.size and file.size > settings.MAX_IMAGE_UPLOAD_BYTES:
        raise ValidationError("حجم تصویر نباید بیشتر از ۸ مگابایت باشد.")
    position = file.tell() if hasattr(file, "tell") else None
    try:
        with Image.open(file) as image:
            image_format = image.format
            image.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValidationError("فایل انتخاب‌شده تصویر معتبر نیست.") from exc
    finally:
        if position is not None:
            file.seek(position)
    if image_format not in ALLOWED_IMAGE_FORMATS:
        raise ValidationError("فقط تصویرهای JPEG، PNG، WebP یا AVIF پذیرفته می‌شوند.")
