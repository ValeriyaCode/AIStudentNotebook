from io import BytesIO
from uuid import uuid4
from PIL import Image, ImageOps, UnidentifiedImageError
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError


def prepare_avatar(upload):
    if upload.size > 5 * 1024 * 1024:
        raise ValidationError('Оберіть фото розміром до 5 МБ.')
    try:
        with Image.open(upload) as source:
            if source.width * source.height > 20000000:
                raise ValidationError('Фото завелике. Максимум — 20 мегапікселів.')
            image = ImageOps.exif_transpose(source).convert('RGB')
            image = ImageOps.fit(image, (400, 400))
            output = BytesIO()
            image.save(output, format='JPEG', quality=88)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, ValueError):
        raise ValidationError('Не вдалося прочитати фото. Оберіть JPG, PNG або WebP.')
    return ContentFile(output.getvalue(), name=f'{uuid4().hex}.jpg')
