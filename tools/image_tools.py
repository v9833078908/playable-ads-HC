"""Image analysis and segmentation tools"""

import base64
import logging
import json
import asyncio
import io
from PIL import Image

from models import AssetMapping, ExtractedAsset, ExtractedComponent, BackgroundInfo
from services.gemini_client import gemini_client
from services.openai_client import openai_client
from services.segmentation import segment_objects, extract_background_color

logger = logging.getLogger('ImageTools')

GEMINI_TIMEOUT = 15  # seconds


async def analyze_and_extract(images_bytes: list[bytes]) -> AssetMapping:
    """
    Full pipeline: analyze images → segment objects → extract components.

    This is the new main function that extracts components from images
    instead of classifying whole images into categories.
    """
    logger.info(f"analyze_and_extract: {len(images_bytes)} images")

    all_components: list[ExtractedComponent] = []
    background_info: BackgroundInfo | None = None
    style = "cartoon"

    # Analyze all images for segmentation
    analyses = await _analyze_images_for_segmentation(images_bytes)

    for i, (img_bytes, analysis) in enumerate(zip(images_bytes, analyses)):
        logger.info(f"Processing image {i}: {analysis}")

        # Extract background info from first valid result
        if not background_info and analysis.get("background"):
            bg = analysis["background"]
            bg_type = bg.get("type", "solid_color")

            if bg_type == "solid_color":
                # Use detected color or extract from image
                primary_color = bg.get("primary_color")
                if not primary_color:
                    primary_color = extract_background_color(img_bytes)

                background_info = BackgroundInfo(
                    type="solid_color",
                    primary_color=primary_color,
                )
            else:
                # Complex background - store the image
                background_info = BackgroundInfo(
                    type="image",
                    primary_color=bg.get("primary_color"),
                    base64=base64.b64encode(img_bytes).decode(),
                )

        # Extract style
        if analysis.get("style"):
            style = analysis["style"]

        # Segment objects from this image
        objects_to_extract = [
            obj for obj in analysis.get("objects", [])
            if obj.get("should_extract", True)
        ]

        if objects_to_extract:
            components = await segment_objects(img_bytes, objects_to_extract, source_index=i)
            all_components.extend(components)
        else:
            # No objects identified - try to extract the whole image as foreground
            logger.info(f"No objects identified in image {i}, extracting whole image")
            try:
                from services.segmentation import remove_background_from_image
                no_bg = remove_background_from_image(img_bytes)
                all_components.append(ExtractedComponent(
                    id=f"object_{i}",
                    base64=base64.b64encode(no_bg).decode(),
                    role="main_gameplay_object",
                    description="extracted object",
                    source_image_index=i,
                ))
            except Exception as e:
                logger.error(f"Failed to extract whole image {i}: {e}")

    # Fallback: if no background detected, extract from first image
    if not background_info and images_bytes:
        primary_color = extract_background_color(images_bytes[0])
        background_info = BackgroundInfo(
            type="solid_color",
            primary_color=primary_color,
        )

    return AssetMapping(
        components=all_components,
        background=background_info,
        style=style,
    )


async def _analyze_images_for_segmentation(images_bytes: list[bytes]) -> list[dict]:
    """Analyze images with GPT-4o for segmentation (Gemini disabled)."""

    results = None

    # Gemini disabled - too slow/unreliable, always times out
    # Skip directly to GPT-4o to save 15 seconds
    # try:
    #     logger.info(f"Trying Gemini for segmentation analysis (timeout={GEMINI_TIMEOUT}s)...")
    #     results = await asyncio.wait_for(
    #         gemini_client.analyze_batch_for_segmentation(images_bytes),
    #         timeout=GEMINI_TIMEOUT
    #     )
    #     logger.info(f"Gemini success: {len(results)} results")
    # except asyncio.TimeoutError:
    #     logger.warning(f"Gemini timeout after {GEMINI_TIMEOUT}s, switching to GPT-4o...")
    # except Exception as e:
    #     logger.warning(f"Gemini failed: {e}, switching to GPT-4o...")

    # Use GPT-4o directly
    if results is None:
        try:
            logger.info("Calling GPT-4o Vision for segmentation analysis...")
            results = await _analyze_with_gpt4o_segmentation(images_bytes)
            logger.info(f"GPT-4o success: {len(results)} results")
        except Exception as e:
            logger.error(f"GPT-4o also failed: {e}, using fallback")
            # Return minimal fallback
            results = [
                {
                    "index": i,
                    "background": {"type": "solid_color", "primary_color": None},
                    "objects": [{"description": "main object", "role": "main_gameplay_object", "should_extract": True}],
                    "style": "cartoon"
                }
                for i in range(len(images_bytes))
            ]

    return results


async def _analyze_with_gpt4o_segmentation(images_bytes: list[bytes]) -> list[dict]:
    """Analyze images with GPT-4o for segmentation."""

    content = [
        {
            "type": "text",
            "text": """Analyze these game images for object segmentation. For EACH image (by index 0,1,2...), identify:

1. Background: type (solid_color/gradient/texture), primary_color (#HEX)
2. Objects to extract with their bounding boxes

Return JSON:
{
    "images": [
        {
            "index": 0,
            "background": {"type": "solid_color", "primary_color": "#D4B8A0", "description": "beige background"},
            "objects": [
                {"description": "dirty teeth", "role": "main_gameplay_object", "bbox": [x, y, w, h], "should_extract": true},
                {"description": "water flosser", "role": "interactive_tool", "bbox": [x, y, w, h], "should_extract": true}
            ],
            "style": "cartoon"
        }
    ]
}

ROLES: main_gameplay_object (main interaction target), interactive_tool (player tools), decoration (visual), ui_element (buttons/text), icon
Always estimate bbox as [x, y, width, height] in pixels."""
        }
    ]

    for i, img_bytes in enumerate(images_bytes):
        # Get image dimensions
        img = Image.open(io.BytesIO(img_bytes))
        content[0]["text"] += f"\n\nImage {i} dimensions: {img.width}x{img.height} pixels"

        b64 = base64.b64encode(img_bytes).decode()
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64}"}
        })

    response = await openai_client.chat.completions.create(
        model="gpt-5.2",
        messages=[{"role": "user", "content": content}],
        response_format={"type": "json_object"}
    )

    result_text = response.choices[0].message.content or "{}"
    data = json.loads(result_text)
    return data.get("images", [])


# Legacy functions for backward compatibility

async def analyze_images_with_gemini(images_bytes: list[bytes]) -> AssetMapping:
    """
    Legacy function: classify images into categories.
    Now redirects to the new analyze_and_extract pipeline.
    """
    return await analyze_and_extract(images_bytes)


async def _analyze_with_gpt4o(images_bytes: list[bytes]) -> list[dict]:
    """Legacy fallback: analyze images with GPT-4o Vision (category-based)"""
    content = [
        {
            "type": "text",
            "text": """Analyze these game assets. For EACH image (by index 0,1,2...), classify:

Categories: background, character, icon, ui_screen
Roles: battle_bg, setup_bg, victory_bg, player_unit, enemy_unit, draggable_item, reward_icon

Return JSON: {"assets": [{"index": 0, "category": "character", "role": "player_unit"}, ...]}"""
        }
    ]

    for i, img_bytes in enumerate(images_bytes):
        b64 = base64.b64encode(img_bytes).decode()
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64}"}
        })

    response = await openai_client.chat.completions.create(
        model="gpt-5.2",
        messages=[{"role": "user", "content": content}],
        response_format={"type": "json_object"}
    )

    result_text = response.choices[0].message.content or "{}"
    data = json.loads(result_text)
    return data.get("assets", data.get("images", []))


async def analyze_single_image(image_bytes: bytes) -> ExtractedAsset:
    """Analyze a single image (legacy)"""
    result = await gemini_client.analyze_image(image_bytes)
    b64 = base64.b64encode(image_bytes).decode()

    return ExtractedAsset(
        index=0,
        base64=b64,
        category=result.get("category", "character"),
        style=result.get("style", "cartoon"),
        colors=result.get("colors", []),
        suggested_role=result.get("role", "unknown"),
    )
