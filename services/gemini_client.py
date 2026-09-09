from google import genai
from google.genai import types
import json
import os
import logging
from typing import Any

logger = logging.getLogger('GeminiClient')

# Configure on import
api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
logger.info(f"Gemini API key configured: {bool(api_key)}")

# Create client
client = genai.Client(api_key=api_key) if api_key else None


# New prompt for segmentation-aware analysis
ANALYZE_FOR_SEGMENTATION_PROMPT = """Analyze this game image and identify ALL objects for segmentation.

Return JSON:
{
    "background": {
        "type": "solid_color|gradient|texture",
        "primary_color": "#HEX",
        "description": "description of background"
    },
    "objects": [
        {
            "description": "what this object is",
            "role": "main_gameplay_object|interactive_tool|decoration|ui_element|icon",
            "bbox": [x, y, width, height],
            "should_extract": true
        }
    ],
    "style": "cartoon|pixel|realistic",
    "is_screenshot": true
}

RULES:
- bbox = [x, y, width, height] in pixels. Estimate coordinates based on image dimensions.
- should_extract = true for gameplay objects, false for UI elements
- role: main_gameplay_object (the main thing to interact with), interactive_tool (tools player uses), decoration (visual elements), ui_element (buttons, text), icon (small icons)
- ALWAYS identify background color even in complex scenes - look at edges/corners
- If image has teeth/mouth, identify them as main_gameplay_object
- If image has cleaning tools (toothbrush, flosser, etc), identify as interactive_tool

Return ONLY valid JSON, no markdown."""


class GeminiVision:
    """Gemini Vision client for image analysis"""

    def __init__(self):
        self.model_name = "gemini-2.5-flash"
        self.client = client  # Use global client

    async def analyze_image(self, image_bytes: bytes) -> dict:
        """Analyze single image for basic classification (legacy)"""
        import PIL.Image
        import io

        image = PIL.Image.open(io.BytesIO(image_bytes))

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=[
                """Analyze this game asset image. Return JSON:
{
    "category": "background|character|icon|ui_screen",
    "style": "cartoon|pixel|realistic",
    "colors": ["#hex1", "#hex2"],
    "role": "suggested_role like battle_bg, player_unit, etc"
}""",
                types.Part.from_image(image=image)
            ]
        )
        return self._parse_json(response.text)

    async def analyze_for_segmentation(self, image_bytes: bytes, image_dimensions: tuple[int, int] | None = None) -> dict:
        """
        Analyze image to identify objects for segmentation.

        Args:
            image_bytes: Image bytes
            image_dimensions: Optional (width, height) to help with bbox estimation

        Returns:
            Dict with background info and objects list with bboxes
        """
        import PIL.Image
        import io

        image = PIL.Image.open(io.BytesIO(image_bytes))

        prompt = ANALYZE_FOR_SEGMENTATION_PROMPT
        if image_dimensions:
            prompt += f"\n\nImage dimensions: {image_dimensions[0]}x{image_dimensions[1]} pixels"

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=[prompt, types.Part.from_image(image=image)]
        )
        return self._parse_json(response.text)

    async def analyze_batch(self, images: list[bytes]) -> list[dict]:
        """Analyze multiple images at once (legacy batch analysis)"""
        import PIL.Image
        import io

        logger.info(f"analyze_batch: {len(images)} images")

        prompt = """Analyze these game assets. For EACH image (by index 0,1,2...), return JSON array:
[
    {"index": 0, "category": "background", "style": "cartoon", "colors": ["#1a1a2e"], "role": "battle_bg"},
    {"index": 1, "category": "character", "style": "cartoon", "colors": ["#ff6b6b"], "role": "player_unit"}
]

Categories: background, character, icon, ui_screen
Roles: battle_bg, setup_bg, victory_bg, player_unit, enemy_unit, draggable_item, reward_icon, ui_element

Return ONLY valid JSON array."""

        contents = [prompt]
        for img_bytes in images:
            image = PIL.Image.open(io.BytesIO(img_bytes))
            contents.append(types.Part.from_image(image=image))

        logger.info("Sending to Gemini API...")
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=contents
        )
        logger.info(f"Gemini response received: {len(response.text)} chars")
        return self._parse_json(response.text)

    async def analyze_batch_for_segmentation(self, images: list[bytes]) -> list[dict]:
        """
        Analyze multiple images for segmentation.

        Returns list of analysis results, one per image.
        """
        import PIL.Image
        import io

        logger.info(f"analyze_batch_for_segmentation: {len(images)} images")

        prompt = """Analyze these game images for object segmentation. For EACH image (by index 0,1,2...), identify:
- Background type and color
- All objects that should be extracted

Return JSON array where each element has this structure:
[
    {
        "index": 0,
        "background": {"type": "solid_color", "primary_color": "#D4B8A0", "description": "beige background"},
        "objects": [
            {"description": "dirty teeth", "role": "main_gameplay_object", "bbox": [100, 200, 400, 300], "should_extract": true},
            {"description": "water flosser", "role": "interactive_tool", "bbox": [350, 500, 100, 200], "should_extract": true}
        ],
        "style": "cartoon",
        "is_screenshot": true
    }
]

ROLES: main_gameplay_object, interactive_tool, decoration, ui_element, icon
- main_gameplay_object = the main thing to interact with (teeth, face, etc)
- interactive_tool = tools/items the player uses (toothbrush, flosser, etc)
- decoration = visual elements (nose, eyes if not main)
- ui_element = buttons, text - usually should_extract: false
- icon = small icons

ALWAYS estimate bbox as [x, y, width, height] in pixels.
Return ONLY valid JSON array."""

        contents = [prompt]
        for img_bytes in images:
            image = PIL.Image.open(io.BytesIO(img_bytes))
            contents.append(types.Part.from_image(image=image))

        logger.info("Sending to Gemini API for segmentation analysis...")
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=contents
        )
        logger.info(f"Gemini response received: {len(response.text)} chars")
        return self._parse_json(response.text)

    async def extract_from_pdf_page(self, page_image: bytes) -> dict:
        """Extract game elements from PDF screenshot"""
        import PIL.Image
        import io

        image = PIL.Image.open(io.BytesIO(page_image))

        prompt = """Analyze this playable ad specification page and extract ALL scenes.

CRITICAL INSTRUCTIONS:
- Find ALL numbered scenes (Сцена 1, Сцена 1.1, Сцена 2, Сцена 2.1, Сцена 3, Сцена 3.1, Сцена 4, etc.)
- DO NOT limit to 3 scenes - extract as many as you can see
- Each scene or sub-scene should be a separate entry
- Look for tutorial phases (Ремонт/Repair, Оружие/Weapons, Слияние/Merge) and their battle phases
- Extract exact CTA text (usually in English: "REPAIR YOUR SHIP", "SETUP WEAPONS", "MERGE WEAPONS")
- Include the victory/store transition scene

Extract and return JSON:
{
    "title": "game title from document",
    "scenes": [
        {"id": "repair", "description": "detailed description of what happens", "ui_text": "REPAIR YOUR SHIP", "type": "tutorial"},
        {"id": "repair_battle", "description": "...", "type": "battle"},
        {"id": "weapons", "description": "...", "ui_text": "SETUP WEAPONS", "type": "tutorial"},
        {"id": "weapons_battle", "description": "...", "type": "battle"},
        {"id": "merge", "description": "...", "ui_text": "MERGE WEAPONS", "type": "tutorial"},
        {"id": "merge_battle", "description": "...", "type": "battle"},
        {"id": "victory", "description": "...", "type": "victory"}
    ],
    "copy_texts": {"cta_repair": "REPAIR YOUR SHIP", "cta_weapons": "SETUP WEAPONS", "cta_merge": "MERGE WEAPONS", "cta_reward": "TAKE REWARD"},
    "game_type": "merge|battle|pirate|etc"
}

Return ONLY valid JSON with ALL scenes you can find. Do not limit yourself."""

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=[prompt, types.Part.from_image(image=image)]
        )
        return self._parse_json(response.text)

    def _parse_json(self, text: str) -> Any:
        """Extract JSON from response text"""
        # Remove markdown code blocks if present
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        return json.loads(text.strip())


# Singleton instance
gemini_client = GeminiVision()
