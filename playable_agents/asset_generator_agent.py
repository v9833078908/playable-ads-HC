"""
Asset Generator Agent - Generates visual assets using FAL API

Uses Claude Haiku 4.5 for prompt building and FAL API Gemini Image for generation.
"""

import base64
import io
import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

from agents import Agent, function_tool, RunContextWrapper

logger = logging.getLogger('AssetGeneratorAgent')

# Role-specific configuration for asset generation
ROLE_CONFIG = {
    "main_object": {
        "suffix": "centered, single object, transparent background, no shadows",
        "size": (512, 512),
        "format": "png",
        "aspect_ratio": "1:1"
    },
    "tool": {
        "suffix": "centered, simple, transparent background, clean silhouette",
        "size": (256, 256),
        "format": "png",
        "aspect_ratio": "1:1"
    },
    "background": {
        "suffix": "full frame, scenic, no characters, no UI",
        "size": (960, 540),
        "format": "jpeg",
        "aspect_ratio": "16:9"
    },
    "ui_element": {
        "suffix": "clean UI element, transparent background, readable",
        "size": (256, 256),
        "format": "png",
        "aspect_ratio": "1:1"
    },
    "effect": {
        "suffix": "effect overlay, transparent background, seamless",
        "size": (512, 512),
        "format": "png",
        "aspect_ratio": "1:1"
    },
    "decoration": {
        "suffix": "small decorative element, transparent background",
        "size": (128, 128),
        "format": "png",
        "aspect_ratio": "1:1"
    }
}


def _build_prompt(asset: dict, style_desc: dict) -> str:
    """
    Build image generation prompt from asset spec and style description.

    Args:
        asset: Asset dict with name, description, role
        style_desc: Style description dict with style, colors, etc.

    Returns:
        Complete prompt string for FAL API
    """
    role = asset.get("role", "main_object")
    config = ROLE_CONFIG.get(role, ROLE_CONFIG["main_object"])

    # Build style string
    style_parts = []
    if style_desc:
        if style_desc.get("style"):
            style_parts.append(f"{style_desc['style']} style")
        if style_desc.get("shading"):
            style_parts.append(f"{style_desc['shading']} shading")
        if style_desc.get("colors"):
            style_parts.append(f"colors: {', '.join(style_desc['colors'][:3])}")

    style_str = ", ".join(style_parts) if style_parts else "cartoon style, bright colors"

    # Combine: description + style + role suffix
    prompt = f"{asset['description']}, {style_str}, {config['suffix']}"

    return prompt


def _get_role_for_asset(name: str, asset_list: list) -> str:
    """Get role for asset from asset_list."""
    for a in asset_list:
        if a.get("name") == name:
            return a.get("role", "main_object")
    return "main_object"


def _get_image_size(data_uri: str) -> dict:
    """Extract image dimensions from base64 data URI."""
    from PIL import Image

    if data_uri.startswith("data:"):
        b64_data = data_uri.split(",", 1)[1]
    else:
        b64_data = data_uri

    img_bytes = base64.b64decode(b64_data)
    img = Image.open(io.BytesIO(img_bytes))
    return {"width": img.width, "height": img.height}


def _get_fal_client():
    """Get or create FAL API client."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "fal_imagen_client",
        Path(__file__).parent.parent / "services" / "fal_imagen_client.py"
    )
    fal_client_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fal_client_module)
    return fal_client_module.get_fal_imagen_client()


def _optimize_image(image_bytes: bytes, role: str, target_format: str = "png") -> bytes:
    """
    Optimize image for playable ad usage.

    - Resize based on role
    - Compress PNG/JPEG
    - Convert to target format

    Args:
        image_bytes: Original image bytes from FAL API
        role: Asset role (main_object, tool, background, etc.)
        target_format: Target format (png or jpeg)

    Returns:
        Optimized image bytes
    """
    from PIL import Image

    # Target sizes by role
    target_sizes = {
        "main_object": (512, 512),
        "tool": (256, 256),
        "background": (960, 540),
        "ui_element": (256, 256),
        "effect": (256, 256),
        "decoration": (128, 128),
    }

    img = Image.open(io.BytesIO(image_bytes))
    target_size = target_sizes.get(role, (512, 512))

    # Resize if larger than target
    if img.width > target_size[0] or img.height > target_size[1]:
        img.thumbnail(target_size, Image.Resampling.LANCZOS)
        logger.info(f"Resized from original to {img.width}x{img.height}")

    # Save with optimization
    output = io.BytesIO()
    if target_format == "jpeg":
        img = img.convert("RGB")
        img.save(output, format="JPEG", quality=85, optimize=True)
    else:
        img.save(output, format="PNG", optimize=True)

    optimized_bytes = output.getvalue()
    original_kb = len(image_bytes) / 1024
    optimized_kb = len(optimized_bytes) / 1024
    logger.info(f"Optimized: {original_kb:.1f}KB → {optimized_kb:.1f}KB (saved {original_kb - optimized_kb:.1f}KB)")

    return optimized_bytes


@function_tool
async def use_reference_assets(ctx: RunContextWrapper[Any]) -> str:
    """
    Map loaded reference assets to asset_list items.

    Checks reference_assets in memory and maps them to corresponding
    items in asset_list. Already loaded assets skip generation.

    Returns:
        Summary of matched reference assets
    """
    memory = ctx.context.get("memory_store")
    if not memory:
        return "Error: Memory store not initialized"

    reference_assets = memory.get("reference_assets") or {}  # {name: base64_data}
    asset_list = memory.get("asset_list") or []

    if not reference_assets:
        return "No reference assets found in memory. Nothing to map."

    # Mapping rules: reference_filename → asset_list_name
    name_mapping = {
        "car_clean": ["car_clean"],
        "car_dirt": ["car_dirt_overlay"],
        "car_bright": ["car_bright"],
        "hand": ["hand_hint"],
        "karcher_one": ["karcher_one"],
        "karcher_water": ["water_stream"],
    }

    manifest = memory.get("asset_manifest") or {}
    matched = []

    for ref_name, ref_data in reference_assets.items():
        target_names = name_mapping.get(ref_name, [ref_name])
        for target_name in target_names:
            manifest[target_name] = {
                "data": ref_data,
                "role": _get_role_for_asset(target_name, asset_list),
                "size": _get_image_size(ref_data),
                "source": "reference"
            }
            matched.append(target_name)
            logger.info(f"Mapped reference asset: {ref_name} → {target_name}")

    memory.set("asset_manifest", manifest)
    return f"Mapped {len(matched)} reference assets: {', '.join(matched)}"


@function_tool
async def generate_asset(ctx: RunContextWrapper[Any], asset_name: str) -> str:
    """
    Generate a single asset image using FAL API.

    Args:
        asset_name: Name of the asset to generate (must be in asset_list)

    Returns:
        Status message with generation result
    """
    from PIL import Image

    memory = ctx.context.get("memory_store")
    if not memory:
        return "Error: Memory store not initialized"

    asset_list = memory.get("asset_list") or []
    style_desc = memory.get("style_description") or {}

    # Find asset in list
    asset = None
    for a in asset_list:
        if a.get("name") == asset_name:
            asset = a
            break

    if not asset:
        return f"Error: Asset '{asset_name}' not found in asset_list"

    role = asset.get("role", "main_object")
    config = ROLE_CONFIG.get(role, ROLE_CONFIG["main_object"])

    # Build prompt
    prompt = _build_prompt(asset, style_desc)
    logger.info(f"Generating {asset_name}: {prompt[:100]}...")

    try:
        # Call FAL API
        fal_client = _get_fal_client()
        image_bytes = fal_client.generate_image_bytes(
            prompt=prompt,
            aspect_ratio=config["aspect_ratio"],
            format=config["format"]
        )

        # Optimize image
        image_bytes = _optimize_image(image_bytes, role, config["format"])

        # Convert to base64 data URI
        mime_type = f"image/{config['format']}"
        b64_data = base64.b64encode(image_bytes).decode('utf-8')
        data_uri = f"data:{mime_type};base64,{b64_data}"

        # Get image dimensions
        img = Image.open(io.BytesIO(image_bytes))

        # Store in asset_manifest
        manifest = memory.get("asset_manifest") or {}
        manifest[asset_name] = {
            "data": data_uri,
            "role": role,
            "size": {"width": img.width, "height": img.height}
        }
        memory.set("asset_manifest", manifest)

        return f"Generated {asset_name}: {img.width}x{img.height}, {len(image_bytes)/1024:.1f}KB"

    except Exception as e:
        logger.error(f"Failed to generate {asset_name}: {e}", exc_info=True)
        return f"Error generating {asset_name}: {str(e)}"


@function_tool
async def generate_all_assets(ctx: RunContextWrapper[Any]) -> str:
    """
    Generate all assets from the asset_list.

    Iterates through asset_list and generates each asset using FAL API.
    Results are stored in asset_manifest in memory.

    Returns:
        Summary of generation results
    """
    from PIL import Image

    memory = ctx.context.get("memory_store")
    if not memory:
        return "Error: Memory store not initialized"

    asset_list = memory.get("asset_list") or []
    style_desc = memory.get("style_description") or {}

    if not asset_list:
        return "Error: No assets in asset_list. Run create_asset_list first."

    logger.info(f"Generating {len(asset_list)} assets...")

    manifest = {}
    success_count = 0
    failed_assets = []

    for i, asset in enumerate(asset_list):
        asset_name = asset.get("name", f"asset_{i}")
        role = asset.get("role", "main_object")
        config = ROLE_CONFIG.get(role, ROLE_CONFIG["main_object"])

        logger.info(f"Generating {i+1}/{len(asset_list)}: {asset_name}")

        # Build prompt
        prompt = _build_prompt(asset, style_desc)

        # Retry logic for important assets
        max_attempts = 3 if role in ["main_object", "tool"] else 1

        for attempt in range(max_attempts):
            try:
                # Call FAL API
                fal_client = _get_fal_client()
                image_bytes = fal_client.generate_image_bytes(
                    prompt=prompt,
                    aspect_ratio=config["aspect_ratio"],
                    format=config["format"]
                )

                # Optimize image
                image_bytes = _optimize_image(image_bytes, role, config["format"])

                # Convert to base64 data URI
                mime_type = f"image/{config['format']}"
                b64_data = base64.b64encode(image_bytes).decode('utf-8')
                data_uri = f"data:{mime_type};base64,{b64_data}"

                # Get image dimensions
                img = Image.open(io.BytesIO(image_bytes))

                manifest[asset_name] = {
                    "data": data_uri,
                    "role": role,
                    "size": {"width": img.width, "height": img.height}
                }
                success_count += 1
                logger.info(f"✅ {asset_name}: {img.width}x{img.height}")
                break

            except Exception as e:
                logger.warning(f"Attempt {attempt+1}/{max_attempts} failed for {asset_name}: {e}")
                if attempt == max_attempts - 1:
                    failed_assets.append(asset_name)
                    logger.error(f"❌ Failed to generate {asset_name}")

    # Store manifest
    memory.set("asset_manifest", manifest)

    # Calculate total size
    total_size = sum(len(a["data"]) for a in manifest.values())

    summary = f"""Asset generation complete:
- Generated: {success_count}/{len(asset_list)} assets
- Failed: {len(failed_assets)} ({', '.join(failed_assets) if failed_assets else 'none'})
- Total size: {total_size / 1024:.1f}KB"""

    return summary


@function_tool
async def generate_missing_assets(ctx: RunContextWrapper[Any]) -> str:
    """
    Generate only assets that are not yet in asset_manifest.

    Uses FAL API to generate assets that weren't provided as references.

    Returns:
        Summary of generation results for missing assets
    """
    from PIL import Image

    memory = ctx.context.get("memory_store")
    if not memory:
        return "Error: Memory store not initialized"

    asset_list = memory.get("asset_list") or []
    manifest = memory.get("asset_manifest") or {}
    style_desc = memory.get("style_description") or {}

    if not asset_list:
        return "Error: No assets in asset_list. Run create_asset_list first."

    # Find missing assets
    missing = [a for a in asset_list if a.get("name") not in manifest]

    if not missing:
        return "All assets already present. No generation needed."

    logger.info(f"Generating {len(missing)} missing assets...")

    success_count = 0
    failed_assets = []

    for i, asset in enumerate(missing):
        asset_name = asset.get("name", f"asset_{i}")
        role = asset.get("role", "main_object")
        config = ROLE_CONFIG.get(role, ROLE_CONFIG["main_object"])

        logger.info(f"Generating {i+1}/{len(missing)}: {asset_name}")

        # Build prompt
        prompt = _build_prompt(asset, style_desc)

        # Retry logic for important assets
        max_attempts = 3 if role in ["main_object", "tool"] else 1

        for attempt in range(max_attempts):
            try:
                # Call FAL API
                fal_client = _get_fal_client()
                image_bytes = fal_client.generate_image_bytes(
                    prompt=prompt,
                    aspect_ratio=config["aspect_ratio"],
                    format=config["format"]
                )

                # Optimize image
                image_bytes = _optimize_image(image_bytes, role, config["format"])

                # Convert to base64 data URI
                mime_type = f"image/{config['format']}"
                b64_data = base64.b64encode(image_bytes).decode('utf-8')
                data_uri = f"data:{mime_type};base64,{b64_data}"

                # Get image dimensions
                img = Image.open(io.BytesIO(image_bytes))

                manifest[asset_name] = {
                    "data": data_uri,
                    "role": role,
                    "size": {"width": img.width, "height": img.height},
                    "source": "generated"
                }
                success_count += 1
                logger.info(f"✅ {asset_name}: {img.width}x{img.height}")
                break

            except Exception as e:
                logger.warning(f"Attempt {attempt+1}/{max_attempts} failed for {asset_name}: {e}")
                if attempt == max_attempts - 1:
                    failed_assets.append(asset_name)
                    logger.error(f"❌ Failed to generate {asset_name}")

    # Update manifest
    memory.set("asset_manifest", manifest)

    summary = f"""Generated {len(missing)} missing assets:
- Success: {success_count}/{len(missing)}
- Failed: {len(failed_assets)} ({', '.join(failed_assets) if failed_assets else 'none'})
- Assets: {', '.join(a.get('name') for a in missing)}"""

    return summary


@function_tool
def get_asset_status(ctx: RunContextWrapper[Any]) -> str:
    """
    Get current status of asset generation.

    Returns summary of which assets have been generated.
    """
    memory = ctx.context.get("memory_store")
    if not memory:
        return "Error: Memory store not initialized"

    asset_list = memory.get("asset_list") or []
    manifest = memory.get("asset_manifest") or {}

    if not asset_list:
        return "No assets planned yet. Run create_asset_list first."

    status_lines = [f"Asset Status ({len(manifest)}/{len(asset_list)} generated):\n"]

    for asset in asset_list:
        name = asset.get("name", "unknown")
        role = asset.get("role", "unknown")

        if name in manifest:
            size = manifest[name].get("size", {})
            status_lines.append(f"✅ {name} ({role}): {size.get('width', '?')}x{size.get('height', '?')}")
        else:
            status_lines.append(f"⏳ {name} ({role}): pending")

    return "\n".join(status_lines)


@function_tool
def validate_asset(ctx: RunContextWrapper[Any], asset_name: str) -> str:
    """
    Validate a generated asset using vision model.

    Checks if the asset matches its description and is suitable for use.

    Args:
        asset_name: Name of asset to validate

    Returns:
        Validation result with suggestions if needed
    """
    memory = ctx.context.get("memory_store")
    if not memory:
        return "Error: Memory store not initialized"

    manifest = memory.get("asset_manifest") or {}

    if asset_name not in manifest:
        return f"Error: Asset '{asset_name}' not found in manifest"

    # Get asset data
    asset_data = manifest[asset_name]

    # Get original description
    asset_list = memory.get("asset_list") or []
    description = "unknown"
    for a in asset_list:
        if a.get("name") == asset_name:
            description = a.get("description", "unknown")
            break

    # For now, return basic validation
    # TODO: Add vision validation with Gemini
    return f"""Asset validation for '{asset_name}':
- Role: {asset_data.get('role', 'unknown')}
- Size: {asset_data.get('size', {}).get('width', '?')}x{asset_data.get('size', {}).get('height', '?')}
- Expected: {description}
- Status: Generated (manual validation recommended)"""


# Create the agent
asset_generator_agent = Agent(
    name="AssetGeneratorAgent",
    handoff_description="Generates visual assets using FAL API based on asset list from Scenario Agent",
    instructions="""You are an Asset Generator for playable ads.

Workflow:
1. Call use_reference_assets() to map loaded reference images to asset_list
2. Call get_asset_status() to see what's missing
3. Call generate_missing_assets() to generate only missing assets via FAL API
4. Validate critical assets if needed

IMPORTANT: Always use reference assets when available! Only generate what's missing.

For each asset, the system will:
- Build an appropriate prompt based on the asset description and style
- Use the correct aspect ratio and format based on the asset role
- Retry important assets (main_object, tool) up to 3 times if generation fails

Role configurations:
- main_object: 512x512 PNG, centered, transparent background
- tool: 256x256 PNG, simple silhouette
- background: 960x540 JPEG, scenic
- ui_element: 256x256 PNG, clean
- effect: 512x512 PNG, overlay
- decoration: 128x128 PNG, small

After generation is complete, report the status and any assets that failed.""",
    tools=[use_reference_assets, generate_asset, generate_all_assets, generate_missing_assets, get_asset_status, validate_asset],
)
