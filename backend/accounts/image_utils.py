"""
Utilidades de procesamiento de imágenes para avatares.
"""
import io

from django.core.files.uploadedfile import InMemoryUploadedFile
from PIL import Image

# Formatos permitidos y su MIME type
_FORMAT_MIME = {
    'JPEG': 'image/jpeg',
    'PNG': 'image/png',
    'WEBP': 'image/webp',
}

# Extensiones por formato
_FORMAT_EXT = {
    'JPEG': 'jpg',
    'PNG': 'png',
    'WEBP': 'webp',
}


def sanitize_avatar(uploaded_file) -> InMemoryUploadedFile:
    """
    Re-codifica el avatar con Pillow para eliminar EXIF, metadatos y
    cualquier contenido polígamo embebido.

    Devuelve un InMemoryUploadedFile listo para asignarse al campo avatar.
    El formato original (JPEG/PNG/WEBP) se preserva.
    """
    uploaded_file.seek(0)
    img = Image.open(uploaded_file)
    img_format = img.format  # 'JPEG', 'PNG', 'WEBP'

    if img_format not in _FORMAT_MIME:
        # validate_avatar ya rechaza formatos inválidos; esto es un fallback.
        img_format = 'JPEG'

    # JPEG no soporta transparencia: convertir a RGB para eliminar canal alpha.
    if img_format == 'JPEG' and img.mode in ('RGBA', 'P', 'LA'):
        img = img.convert('RGB')

    output = io.BytesIO()
    save_kwargs = {'format': img_format}
    if img_format == 'JPEG':
        save_kwargs['optimize'] = True
        save_kwargs['quality'] = 85

    # save() sin parámetro 'exif' omite los metadatos EXIF del original.
    img.save(output, **save_kwargs)
    output.seek(0)
    size = output.getbuffer().nbytes

    ext = _FORMAT_EXT[img_format]
    mime = _FORMAT_MIME[img_format]

    return InMemoryUploadedFile(
        output,
        field_name='avatar',
        name=f'avatar.{ext}',
        content_type=mime,
        size=size,
        charset=None,
    )
