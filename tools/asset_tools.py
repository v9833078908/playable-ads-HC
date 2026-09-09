import base64
import io
import re
from PIL import Image


def inline_all_assets(html: str, assets: dict[str, str]) -> str:
    """Inline all assets into HTML (assets should already be data URLs)"""
    # Assets dict should already contain data:image URLs
    # This function is for any additional inlining if needed
    return html


def compress_images(html: str, quality: int = 70) -> str:
    """Compress base64 images in HTML to reduce size"""

    def compress_match(match):
        data_url = match.group(0)

        if "base64," not in data_url:
            return data_url

        try:
            header, b64_data = data_url.split("base64,", 1)

            # Decode image
            img_bytes = base64.b64decode(b64_data)
            img = Image.open(io.BytesIO(img_bytes))

            # Convert to RGB if needed (for JPEG compression)
            if img.mode in ("RGBA", "P"):
                # Keep as PNG for transparency
                buffer = io.BytesIO()
                img.save(buffer, format="PNG", optimize=True)
                new_b64 = base64.b64encode(buffer.getvalue()).decode()
                return f"data:image/png;base64,{new_b64}"
            else:
                # Convert to JPEG
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=quality, optimize=True)
                new_b64 = base64.b64encode(buffer.getvalue()).decode()
                return f"data:image/jpeg;base64,{new_b64}"

        except Exception:
            return data_url

    # Find and replace all data URLs
    pattern = r"data:image/[^;]+;base64,[A-Za-z0-9+/=]+"
    return re.sub(pattern, compress_match, html)


def get_html_size_kb(html: str) -> float:
    """Get HTML size in KB"""
    return len(html.encode("utf-8")) / 1024
