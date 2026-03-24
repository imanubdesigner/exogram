"""
Generador de tarjetas de citas usando Pillow.

Crea imágenes JPEG estéticamente minimalistas con text wrapping
para compartir highlights en redes sociales.
"""
import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# Colores del design system zen
COLORS = {
    'bg': '#FCFCFC',
    'text': '#111111',
    'text_secondary': '#666666',
    'text_tertiary': '#AAAAAA',
    'accent': '#000000',
    'border': '#EEEEEE',
}

# Dimensiones de la tarjeta
CARD_WIDTH = 1080
CARD_HEIGHT = 1080
PADDING = 100
TEXT_AREA_WIDTH = CARD_WIDTH - (PADDING * 2)

# Límites de caracteres para ajustar tamaño de fuente
SHORT_TEXT = 100
MEDIUM_TEXT = 250
LONG_TEXT = 500


def _get_font(name, size):
    """
    Intenta cargar una fuente del sistema.
    Fallback a la fuente default de Pillow.
    """
    font_paths = [
        # Linux
        f'/usr/share/fonts/truetype/dejavu/DejaVu{name}.ttf',
        f'/usr/share/fonts/truetype/liberation/Liberation{name}-Regular.ttf',
        f'/usr/share/fonts/TTF/DejaVu{name}.ttf',
        # Fallback genérica
        f'/usr/share/fonts/truetype/freefont/Free{name}.ttf',
    ]

    for path in font_paths:
        if Path(path).exists():
            return ImageFont.truetype(path, size)

    # Último recurso: fuente default
    try:
        return ImageFont.truetype("DejaVuSerif.ttf", size)
    except (IOError, OSError):
        return ImageFont.load_default()


def _calculate_font_size(text_length):
    """Calcula el tamaño de fuente según la longitud del texto."""
    if text_length <= SHORT_TEXT:
        return 48
    elif text_length <= MEDIUM_TEXT:
        return 36
    elif text_length <= LONG_TEXT:
        return 28
    else:
        return 24


def _wrap_text(text, font, max_width, draw):
    """
    Text wrapping preciso usando medición de píxeles.
    """
    words = text.split()
    lines = []
    current_line = []

    for word in words:
        test_line = ' '.join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        text_width = bbox[2] - bbox[0]

        if text_width <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]

    if current_line:
        lines.append(' '.join(current_line))

    return lines


def generate_quote_card(
    content: str,
    book_title: str,
    author_name: str,
    location: str = ''
) -> bytes:
    """
    Genera una tarjeta de cita como imagen JPEG.

    Args:
        content: Texto del highlight
        book_title: Título del libro
        author_name: Nombre del autor
        location: Ubicación (ej: "Loc 450-455")

    Returns:
        Bytes de la imagen JPEG
    """
    # Crear imagen
    img = Image.new('RGB', (CARD_WIDTH, CARD_HEIGHT), COLORS['bg'])
    draw = ImageDraw.Draw(img)

    # Fuentes
    font_size = _calculate_font_size(len(content))
    font_quote = _get_font('Serif', font_size)
    font_meta = _get_font('Sans', 20)
    font_brand = _get_font('Sans', 16)

    # --- Línea decorativa superior ---
    line_y = PADDING - 30
    draw.line(
        [(PADDING, line_y), (CARD_WIDTH - PADDING, line_y)],
        fill=COLORS['border'],
        width=1
    )

    # --- Comillas de apertura ---
    font_quotes_char = _get_font('Serif', 72)
    draw.text(
        (PADDING, PADDING - 20),
        '"',
        fill=COLORS['text_tertiary'],
        font=font_quotes_char
    )

    # --- Texto de la cita ---
    quote_y = PADDING + 60
    lines = _wrap_text(content, font_quote, TEXT_AREA_WIDTH, draw)

    # Control de overflow: limitar líneas
    max_lines = (CARD_HEIGHT - 400) // (font_size + 12)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip() + '…'

    for line in lines:
        draw.text(
            (PADDING, quote_y),
            line,
            fill=COLORS['text'],
            font=font_quote
        )
        quote_y += font_size + 12

    # --- Comillas de cierre ---
    draw.text(
        (CARD_WIDTH - PADDING - 40, quote_y - 10),
        '"',
        fill=COLORS['text_tertiary'],
        font=font_quotes_char
    )

    # --- Metadata del libro (abajo) ---
    meta_y = CARD_HEIGHT - PADDING - 120

    # Línea separadora
    draw.line(
        [(PADDING, meta_y - 20), (CARD_WIDTH - PADDING, meta_y - 20)],
        fill=COLORS['border'],
        width=1
    )

    # Título del libro
    draw.text(
        (PADDING, meta_y),
        book_title[:80],
        fill=COLORS['text'],
        font=font_meta
    )

    # Autor
    draw.text(
        (PADDING, meta_y + 30),
        author_name[:60],
        fill=COLORS['text_secondary'],
        font=font_meta
    )

    # Ubicación
    if location:
        draw.text(
            (PADDING, meta_y + 60),
            location,
            fill=COLORS['text_tertiary'],
            font=font_meta
        )

    # --- Branding sutil ---
    draw.text(
        (CARD_WIDTH - PADDING - 80, CARD_HEIGHT - PADDING + 10),
        'exogram',
        fill=COLORS['text_tertiary'],
        font=font_brand
    )

    # Guardar como JPEG
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=92, optimize=True)
    buffer.seek(0)

    return buffer.getvalue()
