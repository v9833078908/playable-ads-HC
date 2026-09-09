"""Image segmentation service using rembg + PIL"""

import base64
import io
import logging
from PIL import Image
from rembg import remove

from models.assets import ExtractedComponent

logger = logging.getLogger('Segmentation')


async def segment_objects(
    image_bytes: bytes,
    objects_info: list[dict],
    source_index: int = 0
) -> list[ExtractedComponent]:
    """
    Extract objects from image based on analysis results.

    Args:
        image_bytes: Source image bytes
        objects_info: List of objects from GPT-4o/Gemini analysis
            Each dict: {description, role, bbox (optional), should_extract}
        source_index: Index of the source image

    Returns:
        List of ExtractedComponent with transparent backgrounds
    """
    components = []
    img = Image.open(io.BytesIO(image_bytes))

    # Convert to RGBA if needed
    if img.mode != 'RGBA':
        img = img.convert('RGBA')

    for i, obj in enumerate(objects_info):
        if not obj.get("should_extract", True):
            continue

        role = obj.get("role", "decoration")
        description = obj.get("description", "")
        bbox = obj.get("bbox")

        try:
            if bbox and len(bbox) == 4:
                # Crop to bounding box
                x, y, w, h = bbox
                # Ensure valid bounds
                x = max(0, min(x, img.width - 1))
                y = max(0, min(y, img.height - 1))
                w = min(w, img.width - x)
                h = min(h, img.height - y)

                if w > 10 and h > 10:  # Skip tiny regions
                    cropped = img.crop((x, y, x + w, y + h))
                else:
                    logger.warning(f"Skipping tiny bbox: {bbox}")
                    continue
            else:
                # Use full image
                cropped = img

            # Remove background using rembg
            cropped_bytes = io.BytesIO()
            cropped.save(cropped_bytes, format="PNG")
            no_bg_bytes = remove(cropped_bytes.getvalue())

            # Encode to base64
            b64 = base64.b64encode(no_bg_bytes).decode()

            comp_id = f"{role}_{i}"
            components.append(ExtractedComponent(
                id=comp_id,
                base64=b64,
                role=role,
                description=description,
                source_image_index=source_index,
                bbox=bbox,
            ))
            logger.info(f"Extracted component: {comp_id} ({description[:30]}...)")

        except Exception as e:
            logger.error(f"Failed to extract object {i}: {e}")
            continue

    return components


def extract_background_color(image_bytes: bytes) -> str:
    """
    Determine dominant background color from corner pixels.

    Args:
        image_bytes: Image bytes

    Returns:
        Hex color string like "#D4B8A0"
    """
    img = Image.open(io.BytesIO(image_bytes))

    # Convert to RGB if needed
    if img.mode != 'RGB':
        img = img.convert('RGB')

    # Sample corners (usually background)
    width, height = img.size
    corners = [
        img.getpixel((0, 0)),
        img.getpixel((width - 1, 0)),
        img.getpixel((0, height - 1)),
        img.getpixel((width - 1, height - 1)),
    ]

    # Also sample edge midpoints for better accuracy
    midpoints = [
        img.getpixel((width // 2, 0)),
        img.getpixel((width // 2, height - 1)),
        img.getpixel((0, height // 2)),
        img.getpixel((width - 1, height // 2)),
    ]

    all_samples = corners + midpoints

    # Average the colors
    avg_r = sum(c[0] for c in all_samples) // len(all_samples)
    avg_g = sum(c[1] for c in all_samples) // len(all_samples)
    avg_b = sum(c[2] for c in all_samples) // len(all_samples)

    return f"#{avg_r:02x}{avg_g:02x}{avg_b:02x}"


def remove_background_from_image(image_bytes: bytes) -> bytes:
    """
    Remove background from entire image using rembg.

    Args:
        image_bytes: Source image bytes

    Returns:
        PNG bytes with transparent background
    """
    return remove(image_bytes)


def is_similar_color(color1: str, color2: str, threshold: int = 50) -> bool:
    """Check if two hex colors are similar within threshold."""
    def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    r1, g1, b1 = hex_to_rgb(color1)
    r2, g2, b2 = hex_to_rgb(color2)

    return abs(r1 - r2) < threshold and abs(g1 - g2) < threshold and abs(b1 - b2) < threshold
