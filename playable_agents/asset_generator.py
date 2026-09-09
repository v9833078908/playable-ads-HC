"""
Asset Generator for Playable Ads

Generates visual assets (characters, backgrounds, tools, UI elements) for playable ads
using FAL.AI Gemini 2.5 Flash Image API.

Pipeline:
    DraftBrief + SceneCards + References → Asset Planning (LLM) →
    → Image Generation (FAL.AI) → Postprocessing (rembg, compression) →
    → AssetManifest (base64 data URIs)
"""

import logging
import base64
import io
from datetime import datetime
from typing import Optional, List, Dict, Any
from PIL import Image as PILImage

# Lazy import rembg to avoid NumPy version conflicts on module load
# Will import only when needed in _postprocess_and_optimize()
# import rembg  # Imported lazily when needed

# Import models
from models import DraftBrief
from playable_agents.scene_card import SceneCard

# Import FAL.AI client (direct import to bypass services/__init__.py)
import sys
from pathlib import Path
if str(Path(__file__).parent.parent / "services") not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent / "services"))

# Now import - this avoids services/__init__.py
import importlib.util
spec = importlib.util.spec_from_file_location(
    "fal_imagen_client",
    Path(__file__).parent.parent / "services" / "fal_imagen_client.py"
)
fal_client_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fal_client_module)
FALImagenClient = fal_client_module.FALImagenClient
get_fal_imagen_client = fal_client_module.get_fal_imagen_client

logger = logging.getLogger(__name__)


# ============================================================================
# Constants
# ============================================================================

# Maximum total size for all assets (2MB for playable ads)
MAX_SIZE_BYTES = 2 * 1024 * 1024  # 2MB

# Number of retry attempts for critical assets
RETRY_ATTEMPTS = 3

# Role-specific templates for image generation
# Each role defines technical requirements and default size
ROLE_TEMPLATES = {
    "character": {
        "suffix": "centered, single object, transparent background, no shadows on ground",
        "size": (512, 512),
        "z_index": 10,
        "aspect_ratio": "1:1"
    },
    "tool": {
        "suffix": "centered, single object, transparent background, simple silhouette",
        "size": (256, 256),
        "z_index": 15,
        "aspect_ratio": "1:1"
    },
    "overlay": {
        "suffix": "seamless texture, tileable, transparent edges",
        "size": (512, 512),
        "z_index": 20,
        "aspect_ratio": "1:1"
    },
    "background": {
        "suffix": "full frame, no characters, no UI elements, 16:9 aspect",
        "size": (960, 540),
        "z_index": 0,
        "aspect_ratio": "16:9"
    },
    "decoration": {
        "suffix": "centered, transparent background, small decorative element",
        "size": (128, 128),
        "z_index": 5,
        "aspect_ratio": "1:1"
    },
    "ui": {
        "suffix": "clean UI element, transparent background, readable",
        "size": (256, 256),
        "z_index": 25,
        "aspect_ratio": "1:1"
    }
}


# ============================================================================
# Exceptions
# ============================================================================

class AssetGenerationError(Exception):
    """Raised when asset generation fails"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.details = details or {}
        self.message = message

    def __str__(self):
        if self.details:
            return f"{self.message}\nDetails: {self.details}"
        return self.message


# ============================================================================
# Main Public API
# ============================================================================

def generate_assets(
    brief: DraftBrief,
    scene_cards: List[SceneCard],
    reference_images: List[str]
) -> Dict[str, Any]:
    """
    Generate visual assets for playable ad using FAL.AI Gemini 2.5 Flash Image.

    Args:
        brief: Extracted PDF brief with title, style, copy texts
        scene_cards: Complete scene descriptions with mechanics and user_actions
        reference_images: Client-provided reference images for style consistency
                         (base64 data URIs or file paths)

    Returns:
        AssetManifest dict:
        {
            "assets": [
                {
                    "name": str,           # "hero_character"
                    "role": str,           # "character" | "tool" | "overlay" | etc
                    "z_index": int,        # Render order (0=back, 25=front)
                    "data": str,           # "data:image/png;base64,..."
                    "size": {"width": int, "height": int},
                    "critical": bool       # True if in user_actions
                },
                ...
            ],
            "total_size_bytes": int,
            "metadata": {
                "generation_time": str,    # ISO timestamp
                "optimized": bool,         # True if auto-optimization applied
                "brief_style": str         # Extracted style keywords
            }
        }

    Raises:
        AssetGenerationError: If critical asset generation fails after retries
    """
    logger.info(f"Starting asset generation for brief: {brief.title}")
    logger.info(f"Scene cards: {len(scene_cards)}, References: {len(reference_images)}")

    start_time = datetime.utcnow()

    try:
        # Step 1: Plan assets (extract list from brief + scene_cards)
        logger.info("Step 1: Planning assets...")
        assets_plan = _plan_assets(brief, scene_cards)
        logger.info(f"Planned {len(assets_plan)} assets")

        # Step 2: Generate images via FAL.AI
        logger.info("Step 2: Generating images...")
        brief_style = _extract_style_from_brief(brief)
        raw_images = _generate_images(assets_plan, brief_style, reference_images)
        logger.info(f"Generated {len(raw_images)} images")

        # Step 3: Postprocess and build manifest
        logger.info("Step 3: Postprocessing and building manifest...")
        manifest = _postprocess_and_optimize(raw_images, assets_plan, brief_style)

        # Add metadata
        manifest["metadata"]["generation_time"] = datetime.utcnow().isoformat()
        manifest["metadata"]["duration_seconds"] = (
            datetime.utcnow() - start_time
        ).total_seconds()

        logger.info(f"✅ Asset generation complete!")
        logger.info(f"   Total assets: {len(manifest['assets'])}")
        logger.info(f"   Total size: {manifest['total_size_bytes'] / 1024:.1f}KB")
        logger.info(f"   Optimized: {manifest['metadata']['optimized']}")

        return manifest

    except Exception as e:
        logger.error(f"Asset generation failed: {e}", exc_info=True)
        raise AssetGenerationError(
            f"Failed to generate assets for '{brief.title}'",
            details={"error": str(e), "brief_title": brief.title}
        )


# ============================================================================
# Internal Implementation Functions (Stubs)
# ============================================================================

def _plan_assets(brief: DraftBrief, scene_cards: List[SceneCard]) -> List[Dict[str, Any]]:
    """
    Plan assets using LLM to extract list from brief + scene_cards.

    Process:
    1. Load asset planner prompt template
    2. Build context with brief + scene_cards
    3. Call Gemini LLM to extract asset list
    4. Parse JSON response
    5. Deduplicate assets by name
    6. Determine critical flag based on user_actions

    Returns:
        List of asset plans:
        [
            {
                "name": "hero_character",
                "role": "character",
                "description": "cartoon knight in blue armor",
                "size_hint": {"width": 512, "height": 512},
                "interactive": True,  # From user_actions
                "critical": True      # Added based on user_actions/role
            },
            ...
        ]
    """
    logger.info("Planning assets with Gemini LLM...")

    # Load prompt template
    prompt_template = _load_asset_planner_prompt()

    # Build context
    context = {
        "brief": brief.model_dump(),
        "scene_cards": [sc.model_dump() for sc in scene_cards],
        "reference_descriptions": brief.visual_references if hasattr(brief, 'visual_references') else []
    }

    # Format prompt
    import json
    prompt = prompt_template.format(
        brief=json.dumps(context["brief"], ensure_ascii=False, indent=2),
        scene_cards=json.dumps(context["scene_cards"], ensure_ascii=False, indent=2),
        references=json.dumps(context["reference_descriptions"], ensure_ascii=False, indent=2)
    )

    # Call Gemini LLM
    logger.debug(f"Calling Gemini LLM with prompt length: {len(prompt)}")
    response_text = _call_gemini_llm(prompt)

    # Parse JSON response
    assets_plan = _parse_json_response(response_text)

    # Deduplicate by name (keep first occurrence)
    seen_names = set()
    deduplicated = []
    for asset in assets_plan:
        if asset["name"] not in seen_names:
            seen_names.add(asset["name"])
            deduplicated.append(asset)
        else:
            logger.debug(f"Deduplicated asset: {asset['name']}")

    # Determine critical flag
    for asset in deduplicated:
        asset["critical"] = _is_critical(asset["name"], scene_cards, asset["role"])

    logger.info(f"Planned {len(deduplicated)} unique assets ({len(assets_plan) - len(deduplicated)} duplicates removed)")

    return deduplicated


def _load_asset_planner_prompt() -> str:
    """
    Load asset planner prompt template from Prompts/asset_planner.txt.

    Returns:
        Prompt template string with {brief}, {scene_cards}, {references} placeholders
    """
    from pathlib import Path

    prompt_path = Path(__file__).parent.parent / "Prompts" / "asset_planner.txt"

    if not prompt_path.exists():
        logger.warning(f"Asset planner prompt not found at {prompt_path}, using default")
        return _get_default_asset_planner_prompt()

    with open(prompt_path, "r", encoding="utf-8") as f:
        template = f.read()

    logger.debug(f"Loaded asset planner prompt from {prompt_path}")
    return template


def _get_default_asset_planner_prompt() -> str:
    """Default asset planner prompt if file not found."""
    return """Ты — asset planner для playable ads.

Вход:
- ТЗ (бриф): {brief}
- Scene cards: {scene_cards}
- Референсные изображения клиента: {references}

Задача: составь полный список ассетов для генерации.

Для каждого ассета верни:
- name: уникальный ключ (snake_case, англ.)
- role: character | tool | overlay | background | decoration | ui
- description: что нарисовать (для промпта генерации)
- size_hint: примерный размер {{"width": int, "height": int}}
- interactive: true если объект участвует в user_action

Правила:
- Объект, упомянутый на нескольких экранах = один ассет
- Фоны и атмосфера (небо, облака) → role: background
- UI элементы (кнопки, прогресс) → role: ui
- Если объект участвует в user_action → отметь interactive: true

Верни ТОЛЬКО JSON array, без дубликатов, без markdown:
[
  {{
    "name": "hero_character",
    "role": "character",
    "description": "cartoon knight in blue armor",
    "size_hint": {{"width": 512, "height": 512}},
    "interactive": true
  }}
]
"""


def _call_gemini_llm(prompt: str, model: str = "gpt-4o") -> str:
    """
    Call LLM via OpenAI API for asset planning using Structured Outputs.

    Args:
        prompt: Text prompt for LLM
        model: OpenAI model name (default: gpt-4o)

    Returns:
        Response text (JSON string) from LLM

    Raises:
        Exception: If API call fails
    """
    import os
    import json
    from openai import OpenAI

    # Check for OPENAI_API_KEY
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")

    client = OpenAI(api_key=api_key)

    logger.info(f"Calling OpenAI LLM with Structured Output: {model}")

    # Define JSON schema for asset list
    asset_schema = {
        "type": "json_schema",
        "json_schema": {
            "name": "asset_list",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "assets": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "Unique asset identifier in snake_case"
                                },
                                "role": {
                                    "type": "string",
                                    "enum": ["character", "tool", "overlay", "background", "decoration", "ui"],
                                    "description": "Asset role/type"
                                },
                                "description": {
                                    "type": "string",
                                    "description": "Visual description for image generation"
                                },
                                "size_hint": {
                                    "type": "object",
                                    "properties": {
                                        "width": {"type": "integer"},
                                        "height": {"type": "integer"}
                                    },
                                    "required": ["width", "height"],
                                    "additionalProperties": False
                                },
                                "interactive": {
                                    "type": "boolean",
                                    "description": "True if asset is used in user actions"
                                }
                            },
                            "required": ["name", "role", "description", "size_hint", "interactive"],
                            "additionalProperties": False
                        }
                    }
                },
                "required": ["assets"],
                "additionalProperties": False
            }
        }
    }

    try:
        # Call OpenAI Chat Completion API with Structured Output
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert at analyzing playable ad specifications and determining visual assets needed."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            response_format=asset_schema,
            temperature=0.3
        )

        response_text = response.choices[0].message.content
        logger.debug(f"LLM response length: {len(response_text)}")

        if not response_text:
            raise ValueError("Empty response from OpenAI LLM")

        # Parse to verify it's valid JSON, then extract assets array
        parsed = json.loads(response_text)
        assets_array = parsed.get("assets", [])

        # Return as JSON string of the array (for compatibility with existing code)
        return json.dumps(assets_array)

    except Exception as e:
        logger.error(f"OpenAI LLM call failed: {e}", exc_info=True)
        raise


def _parse_json_response(response_text: str) -> List[Dict[str, Any]]:
    """
    Parse JSON from LLM response text.

    Handles markdown code blocks and extracts JSON array.

    Args:
        response_text: Raw LLM response

    Returns:
        Parsed list of asset dicts

    Raises:
        ValueError: If JSON parsing fails
    """
    import json
    import re

    # Remove markdown code blocks if present
    text = response_text.strip()

    # Try to extract JSON from markdown code block
    json_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', text, re.DOTALL)
    if json_match:
        text = json_match.group(1)
    # Try to find JSON array directly
    elif not text.startswith('['):
        # Find first [ and last ]
        start = text.find('[')
        end = text.rfind(']')
        if start != -1 and end != -1:
            text = text[start:end+1]

    try:
        assets = json.loads(text)

        if not isinstance(assets, list):
            raise ValueError("Expected JSON array, got: " + type(assets).__name__)

        logger.info(f"Parsed {len(assets)} assets from JSON response")
        return assets

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response: {e}")
        logger.error(f"Response text: {text[:500]}...")
        raise ValueError(f"Invalid JSON in LLM response: {e}")


def _is_critical(asset_name: str, scene_cards: List[SceneCard], role: str) -> bool:
    """
    Determine if asset is critical based on user interactions.

    Priority:
    1. Primary: Check if asset_name mentioned in any scene's user_actions
    2. Fallback: role in ["character", "tool"] → critical

    Args:
        asset_name: Asset name to check
        scene_cards: List of scene cards
        role: Asset role

    Returns:
        True if asset is critical (needs retry on failure)
    """
    # Check user_actions across all scenes
    for scene in scene_cards:
        if not hasattr(scene, 'user_actions'):
            continue

        for action in scene.user_actions:
            # Case-insensitive partial match
            if asset_name.lower() in action.lower():
                logger.debug(f"Asset '{asset_name}' is critical (found in user_action: '{action}')")
                return True

    # Fallback to role
    is_critical_role = role in ["character", "tool"]

    if is_critical_role:
        logger.debug(f"Asset '{asset_name}' is critical (role: {role})")

    return is_critical_role


def _extract_style_from_brief(brief: DraftBrief) -> str:
    """Extract style keywords from brief for consistent prompts."""
    # TODO: Implement proper extraction with LLM or heuristics
    return "cartoon flat colors mobile game style"


def _build_prompt(asset: Dict[str, Any], brief_style: str) -> str:
    """
    Build FAL Imagen prompt from asset plan.

    Format: {description}, {brief_style}, {role_suffix}
    Example: "dirty red car with mud spots, cartoon flat colors mobile game style,
              centered, single object, transparent background"

    Args:
        asset: Asset plan dict with description and role
        brief_style: Style keywords from brief

    Returns:
        Complete prompt string for FAL API
    """
    template = ROLE_TEMPLATES[asset["role"]]

    return (
        f'{asset["description"]}, '
        f'{brief_style}, '
        f'{template["suffix"]}'
    )


def _call_fal_imagen(
    prompt: str,
    aspect_ratio: str,
    output_format: str = "png"
) -> bytes:
    """
    Call FAL Imagen API to generate image.

    Args:
        prompt: Full text prompt
        aspect_ratio: "1:1", "16:9", etc.
        output_format: "png", "jpeg"

    Returns:
        Raw image bytes (PNG/JPEG)

    Raises:
        Exception: If FAL API call fails
    """
    client = get_fal_imagen_client()

    logger.debug(f"FAL API call: aspect_ratio={aspect_ratio}, prompt={prompt[:50]}...")

    try:
        image_bytes = client.generate_image_bytes(
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            format=output_format
        )

        logger.info(f"Image generated: {len(image_bytes)} bytes")
        return image_bytes

    except Exception as e:
        logger.error(f"FAL API call failed: {e}", exc_info=True)
        raise


def _generate_images(
    assets_plan: List[Dict[str, Any]],
    brief_style: str,
    reference_images: List[str]
) -> List[Dict[str, Any]]:
    """
    Generate images via FAL.AI with retry logic for critical assets.

    Args:
        assets_plan: List of asset plans from _plan_assets()
        brief_style: Style keywords from brief
        reference_images: Reference images (not used in Phase 3)

    Returns:
        List of dicts with name, role, image_bytes, size, critical
    """
    results = []

    for i, asset in enumerate(assets_plan):
        logger.info(f"Generating asset {i+1}/{len(assets_plan)}: {asset['name']}")

        # Build prompt
        prompt = _build_prompt(asset, brief_style)

        # Get aspect ratio from role template
        aspect_ratio = ROLE_TEMPLATES[asset["role"]]["aspect_ratio"]

        # Retry logic
        attempts = RETRY_ATTEMPTS if asset["critical"] else 1

        image_bytes = None
        for attempt in range(attempts):
            try:
                image_bytes = _call_fal_imagen(
                    prompt=prompt,
                    aspect_ratio=aspect_ratio,
                    output_format="png"
                )

                logger.info(f"✅ Generated {asset['name']} (attempt {attempt+1})")
                break

            except Exception as e:
                logger.warning(f"Attempt {attempt+1}/{attempts} failed for {asset['name']}: {e}")

                if attempt == attempts - 1:
                    # Final attempt failed
                    raise AssetGenerationError(
                        f"Failed to generate {'critical' if asset['critical'] else 'non-critical'} "
                        f"asset '{asset['name']}' after {attempts} attempts",
                        details={
                            "asset": asset,
                            "error": str(e),
                            "attempts": attempts
                        }
                    )

        # Store result
        if image_bytes:
            results.append({
                "name": asset["name"],
                "role": asset["role"],
                "image_bytes": image_bytes,
                "size": asset["size_hint"],
                "critical": asset["critical"]
            })

    return results


def _auto_optimize(assets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Auto-optimize assets when size exceeds budget.

    Steps:
    1. Reduce JPEG quality: 85 → 70 → 60
    2. Resize large assets (>512px) → 256px
    3. Recompress all with lower quality

    Args:
        assets: List of asset dicts with base64 data URIs

    Returns:
        Optimized assets list with same structure
    """
    optimized = []

    for asset in assets:
        # Decode base64
        data_uri = asset["data"]
        mime_type, base64_data = data_uri.split(",", 1)
        image_bytes = base64.b64decode(base64_data)

        # Load image
        image = PILImage.open(io.BytesIO(image_bytes))

        # Resize if large (>512px on any dimension)
        if max(image.size) > 512:
            ratio = 256 / max(image.size)
            new_size = (int(image.width * ratio), int(image.height * ratio))
            image = image.resize(new_size, PILImage.Resampling.LANCZOS)
            logger.debug(f"Resized {asset['name']}: {asset['size']} → {new_size}")

        # Recompress with lower quality
        output = io.BytesIO()

        if "png" in mime_type:
            # PNG: use lower compression level
            image.save(output, format="PNG", optimize=True, compress_level=9)
        else:
            # JPEG: reduce quality
            image.save(output, format="JPEG", optimize=True, quality=60)

        compressed_bytes = output.getvalue()

        # Re-encode to base64
        base64_data = base64.b64encode(compressed_bytes).decode('utf-8')
        data_uri = f"{mime_type.split(';')[0]};base64,{base64_data}"

        optimized.append({
            **asset,
            "data": data_uri,
            "size": {"width": image.width, "height": image.height}
        })

    return optimized


def _postprocess_and_optimize(
    raw_images: List[Dict[str, Any]],
    assets_plan: List[Dict[str, Any]],
    brief_style: str
) -> Dict[str, Any]:
    """
    Postprocess images and build final manifest.

    Process:
    1. For each image:
       a. SKIP background removal (rembg broken - fix later)
       b. Compress with PIL optimize=True, quality=85
       c. Convert to base64 data URI
    2. Calculate total size
    3. If > MAX_SIZE_BYTES → call _auto_optimize()
    4. Build manifest with z_index from ROLE_TEMPLATES

    Args:
        raw_images: List of dicts with image_bytes from _generate_images()
        assets_plan: Original asset plans (not used currently)
        brief_style: Style keywords for metadata

    Returns:
        AssetManifest dict with assets, total_size_bytes, metadata
    """
    assets = []

    for raw_img in raw_images:
        logger.debug(f"Postprocessing {raw_img['name']} ({raw_img['role']})")

        # Load image
        image = PILImage.open(io.BytesIO(raw_img["image_bytes"]))

        # Compress (optimize=True, quality=85)
        output = io.BytesIO()

        # Use PNG for character/tool (transparency support), JPEG for background
        if raw_img["role"] in ["character", "tool", "overlay", "ui", "decoration"]:
            image.save(output, format="PNG", optimize=True)
            mime_type = "image/png"
        else:
            image.save(output, format="JPEG", optimize=True, quality=85)
            mime_type = "image/jpeg"

        compressed_bytes = output.getvalue()

        # Convert to base64 data URI
        base64_data = base64.b64encode(compressed_bytes).decode('utf-8')
        data_uri = f"data:{mime_type};base64,{base64_data}"

        # Add to assets list
        assets.append({
            "name": raw_img["name"],
            "role": raw_img["role"],
            "z_index": ROLE_TEMPLATES[raw_img["role"]]["z_index"],
            "data": data_uri,
            "size": {"width": image.width, "height": image.height},
            "critical": raw_img["critical"]
        })

        logger.info(f"✅ {raw_img['name']}: {len(compressed_bytes)/1024:.1f}KB")

    # Calculate total size
    total_size = sum(len(a["data"]) for a in assets)

    # Auto-optimize if needed
    optimized = False
    if total_size > MAX_SIZE_BYTES:
        logger.warning(f"Total size {total_size/1024/1024:.2f}MB exceeds limit, auto-optimizing...")
        assets = _auto_optimize(assets)
        total_size = sum(len(a["data"]) for a in assets)
        optimized = True
        logger.info(f"✅ Optimized to {total_size/1024/1024:.2f}MB")

    # Build manifest
    return {
        "assets": sorted(assets, key=lambda a: a["z_index"]),
        "total_size_bytes": total_size,
        "metadata": {
            "generation_time": datetime.utcnow().isoformat(),
            "optimized": optimized,
            "brief_style": brief_style
        }
    }
