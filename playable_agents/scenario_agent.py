"""
Scenario Agent - Analyzes TZ and style references to create scene specification

Uses Gemini 3 Pro for vision analysis and understanding.
"""

import base64
import json
import logging
import os
from pathlib import Path
from typing import Any

from agents import Agent, function_tool, RunContextWrapper

logger = logging.getLogger('ScenarioAgent')

# Load system prompt from file
PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_prompt(name: str) -> str:
    """Load prompt from prompts directory"""
    prompt_path = PROMPTS_DIR / f"{name}.md"
    if prompt_path.exists():
        return prompt_path.read_text()
    return ""


@function_tool
async def analyze_spec(ctx: RunContextWrapper[Any]) -> str:
    """
    Analyze the technical specification (TZ) text to extract requirements.

    Parses the specification to identify:
    - Genre/type of playable ad
    - Game mechanics
    - Scene structure
    - UI texts and copy
    - Store URLs
    """
    from services.gemini_client import gemini_client

    memory = ctx.context.get("memory_store")
    if not memory:
        return "Error: Memory store not initialized"

    spec_text = memory.get("spec_text")
    if not spec_text:
        return "Error: No specification text provided"

    # Use Gemini to parse the spec
    prompt = f"""Analyze this playable ad specification and extract structured data.

SPECIFICATION TEXT:
{spec_text}

Return JSON with:
{{
    "genre": "car-wash|merge|match-3|dress-up|runner|puzzle",
    "mechanics": ["drag-to-clean", "reveal-mask", "progress-bar", ...],
    "scenes": [
        {{"name": "gameplay", "description": "...", "mechanic": "drag-to-clean"}},
        {{"name": "victory", "description": "...", "mechanic": "cta"}}
    ],
    "ui_texts": {{
        "hint": "localized hint text",
        "cta": "CTA button text"
    }},
    "store_urls": {{
        "android": "https://play.google.com/...",
        "ios": "https://apps.apple.com/..."
    }},
    "language": "RU|EN|etc",
    "requirements": ["specific requirement 1", "..."]
}}

Return ONLY valid JSON."""

    try:
        response = gemini_client.client.models.generate_content(
            model=gemini_client.model_name,
            contents=[prompt]
        )
        result = gemini_client._parse_json(response.text)

        # Store in memory
        memory.set("scene_spec", result)

        # Build summary
        summary = f"""Specification analyzed:
- Genre: {result.get('genre', 'unknown')}
- Mechanics: {', '.join(result.get('mechanics', []))}
- Scenes: {len(result.get('scenes', []))}
- Language: {result.get('language', 'unknown')}
- Store URLs: {'Yes' if result.get('store_urls') else 'No'}"""

        return summary

    except Exception as e:
        logger.error(f"Failed to analyze spec: {e}", exc_info=True)
        return f"Error analyzing specification: {str(e)}"


@function_tool
async def analyze_references(ctx: RunContextWrapper[Any]) -> str:
    """
    Analyze style reference images using vision.

    Extracts:
    - Visual style (cartoon/realistic/pixel)
    - Color palette
    - Design patterns
    - Target audience indicators
    """
    from services.gemini_client import gemini_client
    import PIL.Image
    import io

    memory = ctx.context.get("memory_store")
    if not memory:
        return "Error: Memory store not initialized"

    style_references = memory.get("style_references")
    if not style_references:
        return "No style references provided - will use default style"

    prompt = """Analyze these style reference images for a playable ad.

Extract:
1. Visual style: cartoon/realistic/pixel/flat
2. Color palette: list of hex colors
3. Art direction: shading type, line style, etc
4. Target audience: casual/mid-core/hardcore
5. Key visual elements to replicate

Return JSON:
{
    "style": "cartoon",
    "shading": "flat|cell|gradient",
    "colors": ["#hex1", "#hex2", ...],
    "line_style": "thick/thin/none",
    "target_audience": "casual",
    "key_elements": ["rounded shapes", "bright colors", ...]
}

Return ONLY valid JSON."""

    try:
        from google.genai import types

        contents = [prompt]

        # Add images
        for name, b64_data in style_references.items():
            # Handle both raw base64 and data URI
            if b64_data.startswith("data:"):
                b64_data = b64_data.split(",", 1)[1]
            img_bytes = base64.b64decode(b64_data)
            image = PIL.Image.open(io.BytesIO(img_bytes))
            contents.append(types.Part.from_image(image=image))

        response = gemini_client.client.models.generate_content(
            model=gemini_client.model_name,
            contents=contents
        )
        result = gemini_client._parse_json(response.text)

        # Store in memory
        memory.set("style_description", result)

        # Build summary
        summary = f"""Style references analyzed:
- Style: {result.get('style', 'cartoon')}
- Shading: {result.get('shading', 'flat')}
- Colors: {', '.join(result.get('colors', [])[:5])}
- Target: {result.get('target_audience', 'casual')}"""

        return summary

    except Exception as e:
        logger.error(f"Failed to analyze references: {e}", exc_info=True)
        return f"Error analyzing references: {str(e)}"


@function_tool
async def create_asset_list(ctx: RunContextWrapper[Any]) -> str:
    """
    Create a list of assets needed for the playable ad.

    Based on scene_spec and style_description, generates an asset list
    with names, descriptions, and roles for image generation.
    """
    from services.gemini_client import gemini_client

    memory = ctx.context.get("memory_store")
    if not memory:
        return "Error: Memory store not initialized"

    scene_spec = memory.get("scene_spec")
    style_desc = memory.get("style_description") or {}

    if not scene_spec:
        return "Error: Scene spec not available. Run analyze_spec first."

    genre = scene_spec.get("genre", "generic")
    mechanics = scene_spec.get("mechanics", [])

    prompt = f"""Based on this playable ad specification, create a list of visual assets needed.

GENRE: {genre}
MECHANICS: {', '.join(mechanics)}
STYLE: {json.dumps(style_desc)}
SCENES: {json.dumps(scene_spec.get('scenes', []))}

Create asset list with each asset having:
- name: snake_case identifier
- description: detailed visual description for image generation (include style details)
- role: main_object|tool|background|ui_element|effect
- states: list of states if applicable (e.g., ["dirty", "clean"])
- size: "512x512"|"256x256"|"960x540" based on role

For car-wash genre, typical assets:
- Main object (car, teeth, etc) in dirty and clean states
- Cleaning tool (hose, brush, etc)
- Background scene
- Dirt/mud overlay texture
- Water splash effects
- UI elements (progress bar, hint bubble)

Return JSON:
{{
    "assets": [
        {{
            "name": "car_dirty",
            "description": "Cartoon dirty car with mud splatters, {style_desc.get('style', 'cartoon')} style, bright colors",
            "role": "main_object",
            "states": ["dirty"],
            "size": "512x512"
        }},
        ...
    ]
}}

Return ONLY valid JSON."""

    try:
        response = gemini_client.client.models.generate_content(
            model=gemini_client.model_name,
            contents=[prompt]
        )
        result = gemini_client._parse_json(response.text)

        # Store in memory
        memory.set("asset_list", result.get("assets", []))

        assets = result.get("assets", [])
        summary = f"""Asset list created ({len(assets)} assets):
"""
        for asset in assets[:6]:  # Show first 6
            summary += f"- {asset['name']} ({asset['role']}): {asset['description'][:50]}...\n"

        if len(assets) > 6:
            summary += f"... and {len(assets) - 6} more assets"

        return summary

    except Exception as e:
        logger.error(f"Failed to create asset list: {e}", exc_info=True)
        return f"Error creating asset list: {str(e)}"


@function_tool
def confirm_understanding(ctx: RunContextWrapper[Any]) -> str:
    """
    Generate a confirmation summary of the understood requirements.

    Returns a human-readable summary for user verification.
    """
    memory = ctx.context.get("memory_store")
    if not memory:
        return "Error: Memory store not initialized"

    scene_spec = memory.get("scene_spec") or {}
    style_desc = memory.get("style_description") or {}
    asset_list = memory.get("asset_list") or []

    genre = scene_spec.get("genre", "unknown")
    mechanics = scene_spec.get("mechanics", [])
    scenes = scene_spec.get("scenes", [])
    ui_texts = scene_spec.get("ui_texts", {})
    store_urls = scene_spec.get("store_urls", {})

    summary = f"""
## Understanding Confirmation

### Genre & Mechanics
- **Genre:** {genre}
- **Mechanics:** {', '.join(mechanics)}

### Scenes ({len(scenes)} total)
"""

    for i, scene in enumerate(scenes, 1):
        summary += f"{i}. **{scene.get('name', 'Scene')}**: {scene.get('description', 'No description')[:100]}\n"

    summary += f"""
### Visual Style
- **Style:** {style_desc.get('style', 'Not specified')}
- **Shading:** {style_desc.get('shading', 'Not specified')}
- **Target:** {style_desc.get('target_audience', 'casual')}

### UI Texts
- **Hint:** {ui_texts.get('hint', 'Not specified')}
- **CTA:** {ui_texts.get('cta', 'Not specified')}

### Assets ({len(asset_list)} planned)
"""

    roles = {}
    for asset in asset_list:
        role = asset.get("role", "other")
        roles[role] = roles.get(role, 0) + 1

    for role, count in roles.items():
        summary += f"- {role}: {count}\n"

    summary += f"""
### Store URLs
- **Android:** {'Yes' if store_urls.get('android') else 'Missing'}
- **iOS:** {'Yes' if store_urls.get('ios') else 'Missing'}

---
**Is this understanding correct?** Reply with any corrections or "confirmed" to proceed.
"""

    return summary


# Create the agent
scenario_agent = Agent(
    name="ScenarioAgent",
    handoff_description="Analyzes TZ specification and style references to create scene specification and asset list",
    instructions=_load_prompt("scenario_agent") or """You are a Scenario Analyst for playable ad creation.

Your job is to analyze the technical specification (TZ) and any style references to create:
1. A detailed scene specification with mechanics and UI texts
2. A comprehensive asset list for image generation
3. A style guide based on references

Workflow:
1. Call analyze_spec() to parse the TZ text
2. Call analyze_references() if style images are provided
3. Call create_asset_list() to generate the asset requirements
4. Call confirm_understanding() to summarize and get user confirmation

Always be thorough and ask clarifying questions if requirements are unclear.""",
    tools=[analyze_spec, analyze_references, create_asset_list, confirm_understanding],
)
