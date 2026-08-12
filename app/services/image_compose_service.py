import os
import time
from PIL import Image, ImageDraw, ImageFont

IMAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "generated_images")
os.makedirs(IMAGE_DIR, exist_ok=True)

_BOLD_FONT_CANDIDATES = [
    "C:/Windows/Fonts/arialbd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
]


def _load_font(size):
    for path in _BOLD_FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _parse_placement(instructions):
    """Cheap keyword parsing of free-text layout instructions - no AI call involved."""
    text = (instructions or "").lower()

    vertical = "bottom"
    if "top" in text:
        vertical = "top"
    elif "center" in text or "middle" in text:
        vertical = "center"

    horizontal = "center"
    if "left" in text and "right" not in text:
        horizontal = "left"
    elif "right" in text and "left" not in text:
        horizontal = "right"

    large_text = any(k in text for k in ("large", "big", "bold"))
    small_text = any(k in text for k in ("small", "subtle", "minimal"))
    use_overlay = not any(k in text for k in ("no overlay", "without overlay", "no background", "no dark"))

    return vertical, horizontal, large_text, small_text, use_overlay


def _wrap_text(draw, text, font, max_width):
    words = text.split()
    lines = []
    current = ""
    for word in words:
        candidate = (current + " " + word).strip()
        if not current or draw.textlength(candidate, font=font) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def compose_hook_on_image(image_path, hook_text, instructions=None):
    """Render the approved hook text directly onto the approved image using Pillow, so
    spelling is exact. Returns the path to the newly saved composed image; the original
    image file is left untouched. Purely local image processing - no AI call involved."""
    if not hook_text:
        raise ValueError("No approved hook text to place on the image.")

    base = Image.open(image_path).convert("RGBA")
    width, height = base.size
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    vertical, horizontal, large_text, small_text, use_overlay = _parse_placement(instructions)

    font_size = width // 14
    if large_text:
        font_size = int(font_size * 1.3)
    elif small_text:
        font_size = int(font_size * 0.75)
    font_size = max(22, min(font_size, width // 8))
    font = _load_font(font_size)

    max_text_width = width * 0.86
    lines = _wrap_text(draw, hook_text.strip(), font, max_text_width)

    line_bbox = draw.textbbox((0, 0), "Ag", font=font)
    line_height = (line_bbox[3] - line_bbox[1]) + int(font_size * 0.4)
    block_height = line_height * len(lines)
    padding = int(font_size * 0.6)

    if vertical == "top":
        block_top = padding
    elif vertical == "center":
        block_top = (height - block_height) // 2
    else:
        block_top = height - block_height - padding * 2

    if use_overlay:
        band_top = max(0, block_top - padding)
        band_bottom = min(height, block_top + block_height + padding)
        draw.rectangle([(0, band_top), (width, band_bottom)], fill=(0, 0, 0, 140))

    y = block_top
    for line in lines:
        line_width = draw.textlength(line, font=font)
        if horizontal == "left":
            x = padding
        elif horizontal == "right":
            x = width - line_width - padding
        else:
            x = (width - line_width) / 2
        draw.text((x, y), line, font=font, fill=(255, 255, 255, 255),
                  stroke_width=max(2, font_size // 16), stroke_fill=(0, 0, 0, 255))
        y += line_height

    composed = Image.alpha_composite(base, overlay).convert("RGB")

    filename = f"final_{int(time.time() * 1000)}.png"
    file_path = os.path.join(IMAGE_DIR, filename)
    composed.save(file_path)

    return file_path
