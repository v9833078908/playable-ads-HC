"""
Generator Agent - Generates HTML playable ads using Claude Sonnet 4.5

Uses LLM for intelligent HTML generation with best practices for each game genre.
"""

import base64
import json
import logging
import os
import re
from pathlib import Path
from typing import Any

from agents import Agent, function_tool, RunContextWrapper

logger = logging.getLogger('GeneratorAgent')

# Load prompts directory
PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_prompt(name: str) -> str:
    """Load prompt from prompts directory"""
    prompt_path = PROMPTS_DIR / f"{name}.md"
    if prompt_path.exists():
        return prompt_path.read_text()
    return ""


def _get_genre_prompt(genre: str) -> str:
    """Get genre-specific prompt file"""
    genre_map = {
        "car-wash": "generator_car_wash",
        "car_wash": "generator_car_wash",
        "cleaning": "generator_car_wash",
        "wash": "generator_car_wash",
    }
    prompt_name = genre_map.get(genre.lower(), "generator_car_wash")
    return _load_prompt(prompt_name)


@function_tool
async def generate_html(ctx: RunContextWrapper[Any]) -> str:
    """
    Generate complete HTML playable ad using Claude Sonnet 4.5.

    Uses scene_spec, asset_manifest, and genre-specific best practices
    to generate high-quality HTML with proper game mechanics.

    Returns:
        Status message with generation result
    """
    import anthropic

    memory = ctx.context.get("memory_store")
    if not memory:
        return "Error: Memory store not initialized"

    scene_spec = memory.get("scene_spec")
    asset_manifest = memory.get("asset_manifest")

    if not scene_spec:
        return "Error: Scene specification not found. Run Scenario Agent first."

    if not asset_manifest:
        return "Error: Asset manifest not found. Run Asset Generator first."

    genre = scene_spec.get("genre", "car-wash")
    genre_prompt = _get_genre_prompt(genre)

    # Build context for Claude
    context = {
        "scene_spec": scene_spec,
        "asset_manifest": {
            name: {
                "role": data.get("role"),
                "size": data.get("size")
            }
            for name, data in asset_manifest.items()
        },
        "ui_texts": scene_spec.get("ui_texts", {}),
        "store_urls": scene_spec.get("store_urls", {}),
    }

    # Build prompt
    system_prompt = genre_prompt or """You are an expert HTML5 game developer specializing in playable ads.
Generate a complete, self-contained HTML file with inlined CSS and JavaScript.
All assets should be embedded as base64 data URIs.
Follow mobile-first practices with proper touch event handling."""

    user_prompt = f"""Generate a complete HTML playable ad based on this specification:

## Scene Specification
```json
{json.dumps(context['scene_spec'], indent=2)}
```

## Available Assets (use placeholders, actual base64 will be injected later)
```json
{json.dumps(context['asset_manifest'], indent=2)}
```

CRITICAL: For assets, use a STATIC object with literal PLACEHOLDER strings.
DO NOT use template literals, dynamic string construction, or loops to build asset URLs.

✅ CORRECT - Static object with literal strings:
```javascript
const assetData = {{
  car_clean: 'PLACEHOLDER_car_clean',
  background_road: 'PLACEHOLDER_background_road',
  hand_cursor: 'PLACEHOLDER_hand_cursor',
  // ... each asset must be a separate literal string
}};
```

❌ WRONG - Dynamic template literals will NOT work:
```javascript
// DON'T DO THIS:
assetNames.forEach(name => {{
  img.src = `PLACEHOLDER_${{name}}`;  // ← WRONG! Not replaceable
}});
```

The base64 data will be injected by replacing literal PLACEHOLDER strings after generation.

Requirements:
1. Single HTML file with all CSS/JS inlined
2. Use PLACEHOLDER_<asset_name> for each asset (base64 will be injected)
3. Touch events with mouse fallback
4. MRAID integration for store redirect
5. Canvas-based rendering
6. Game loop with requestAnimationFrame
7. Progress tracking and victory sequence
8. Animated CTA button with shimmer effect

Return ONLY the complete HTML code, no explanations."""

    try:
        # Call Claude Sonnet 4.5 with streaming for large responses
        client = anthropic.Anthropic()

        html_chunks = []
        stop_reason = None

        with client.messages.stream(
            model="claude-sonnet-4-5-20250929",
            max_tokens=64000,
            messages=[
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            system=system_prompt
        ) as stream:
            for text in stream.text_stream:
                html_chunks.append(text)
            stop_reason = stream.get_final_message().stop_reason

        html = ''.join(html_chunks)

        # Check if output was truncated
        if stop_reason == "max_tokens":
            logger.warning("HTML generation was truncated (hit max_tokens). Attempting continuation...")
            # Request continuation of the truncated HTML
            continuation_chunks = []
            with client.messages.stream(
                model="claude-sonnet-4-5-20250929",
                max_tokens=64000,
                messages=[
                    {"role": "user", "content": user_prompt},
                    {"role": "assistant", "content": html},
                    {"role": "user", "content": "Continue generating the HTML from where you stopped. Output ONLY the remaining HTML code, no explanations."}
                ],
                system=system_prompt
            ) as stream:
                for text in stream.text_stream:
                    continuation_chunks.append(text)
                cont_stop_reason = stream.get_final_message().stop_reason

            html += ''.join(continuation_chunks)
            if cont_stop_reason == "max_tokens":
                logger.error("HTML still truncated after continuation attempt")

        # Clean up if wrapped in markdown
        if html.startswith("```html"):
            html = html[7:]
        if html.startswith("```"):
            html = html[3:]
        if html.endswith("```"):
            html = html[:-3]
        html = html.strip()

        # Inject actual asset data URIs
        html = _inject_assets(html, asset_manifest)

        # Store in memory
        version = memory.append_html_version(html)

        # Calculate size
        size_kb = len(html.encode('utf-8')) / 1024

        return f"""HTML generated successfully!
- Version: {version}
- Size: {size_kb:.1f}KB
- Genre: {genre}
- Assets embedded: {len(asset_manifest)}"""

    except Exception as e:
        logger.error(f"Failed to generate HTML: {e}", exc_info=True)
        return f"Error generating HTML: {str(e)}"


@function_tool
async def fix_issues(ctx: RunContextWrapper[Any], issues: str) -> str:
    """
    Fix issues in the generated HTML based on QA feedback.

    Args:
        issues: JSON string or text describing issues to fix

    Returns:
        Status message with fix result
    """
    import anthropic

    memory = ctx.context.get("memory_store")
    if not memory:
        return "Error: Memory store not initialized"

    current_html = memory.get_latest_html()
    if not current_html:
        return "Error: No HTML to fix. Generate HTML first."

    # Parse issues
    try:
        issues_data = json.loads(issues)
        issues_text = json.dumps(issues_data, indent=2)
    except json.JSONDecodeError:
        issues_text = issues

    # Build fix prompt
    prompt = f"""Fix these issues in the HTML playable ad:

## Issues to Fix
{issues_text}

## Current HTML
```html
{current_html[:15000]}...
```

Requirements:
1. Fix all listed issues
2. Maintain existing functionality
3. Keep the same structure and style
4. Don't break working features

Return the complete fixed HTML code only, no explanations."""

    try:
        client = anthropic.Anthropic()

        # Use streaming for large responses
        fixed_html_chunks = []
        with client.messages.stream(
            model="claude-sonnet-4-5-20250929",
            max_tokens=64000,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            system="You are an expert at fixing HTML/JS code issues. Fix the issues while maintaining all existing functionality."
        ) as stream:
            for text in stream.text_stream:
                fixed_html_chunks.append(text)

        # Extract fixed HTML
        fixed_html = ''.join(fixed_html_chunks)

        # Clean up markdown
        if fixed_html.startswith("```html"):
            fixed_html = fixed_html[7:]
        if fixed_html.startswith("```"):
            fixed_html = fixed_html[3:]
        if fixed_html.endswith("```"):
            fixed_html = fixed_html[:-3]
        fixed_html = fixed_html.strip()

        # Re-inject assets if needed
        asset_manifest = memory.get("asset_manifest") or {}
        fixed_html = _inject_assets(fixed_html, asset_manifest)

        # Store new version
        version = memory.append_html_version(fixed_html)

        return f"Fixed HTML saved as version {version}"

    except Exception as e:
        logger.error(f"Failed to fix issues: {e}", exc_info=True)
        return f"Error fixing issues: {str(e)}"


@function_tool
def get_html_status(ctx: RunContextWrapper[Any]) -> str:
    """
    Get status of current HTML generation.

    Returns version count, size, and basic validation info.
    """
    memory = ctx.context.get("memory_store")
    if not memory:
        return "Error: Memory store not initialized"

    html_versions = memory.get("html_versions") or []

    if not html_versions:
        return "No HTML generated yet."

    latest = html_versions[-1]
    html = latest.get("html", "")

    # Basic checks
    has_canvas = "<canvas" in html
    has_touch = "touchstart" in html and "touchmove" in html
    has_mraid = "mraid" in html
    has_raf = "requestAnimationFrame" in html

    size_kb = len(html.encode('utf-8')) / 1024

    return f"""HTML Status:
- Versions: {len(html_versions)}
- Latest size: {size_kb:.1f}KB
- Has canvas: {'Yes' if has_canvas else 'No'}
- Has touch events: {'Yes' if has_touch else 'No'}
- Has MRAID: {'Yes' if has_mraid else 'No'}
- Has game loop: {'Yes' if has_raf else 'No'}"""


@function_tool
def export_html(ctx: RunContextWrapper[Any]) -> str:
    """
    Export the latest HTML to the context for QA validation.

    Copies the latest HTML version to ctx.context['html'] for use by QA agents.
    """
    memory = ctx.context.get("memory_store")
    if not memory:
        return "Error: Memory store not initialized"

    html = memory.get_latest_html()
    if not html:
        return "Error: No HTML to export"

    # Also store in context for legacy compatibility
    ctx.context["html"] = html

    size_kb = len(html.encode('utf-8')) / 1024
    return f"Exported HTML ({size_kb:.1f}KB) to context for QA validation"


def _inject_assets(html: str, asset_manifest: dict) -> str:
    """
    Inject actual base64 asset data into HTML.

    Finds asset references in JavaScript objects and replaces placeholder
    base64 strings with actual asset data.

    Handles both static placeholders and dynamic template literal patterns.
    """

    # SPECIAL CASE: Detect dynamic template literal pattern and replace entire block
    # Pattern: img.src = `PLACEHOLDER_${name}`
    if 'PLACEHOLDER_${' in html or '`PLACEHOLDER_' in html:
        logger.warning("Detected dynamic template literal pattern - replacing with static dict")

        # Build static assetData object
        asset_dict_lines = ["const assetData = {"]
        for name, data in asset_manifest.items():
            data_uri = data.get("data", "") if isinstance(data, dict) else data
            if data_uri:
                # Escape single quotes in data URI (unlikely but safe)
                data_uri_escaped = data_uri.replace("'", "\\'")
                asset_dict_lines.append(f"    '{name}': '{data_uri_escaped}',")
        asset_dict_lines.append("};")
        asset_dict_js = "\n".join(asset_dict_lines)

        # Find and replace the assetNames array and forEach loop
        # Pattern 1: const assetNames = [...]; ... forEach(name => { img.src = `PLACEHOLDER_${name}` })
        import_pattern = r'const assetNames = \[[^\]]+\];[\s\S]*?\.forEach\(.*?=>\s*\{[\s\S]*?`PLACEHOLDER_\$\{[^}]+\}`[\s\S]*?\}\);'
        match = re.search(import_pattern, html)
        if match:
            # Replace entire block with static dictionary + simple loading
            replacement = f"""{asset_dict_js}

        function loadAssets() {{
            const images = {{}};
            for (const [name, dataUri] of Object.entries(assetData)) {{
                const img = new Image();
                img.onload = () => {{
                    assetsLoaded++;
                    if (assetsLoaded === totalAssets) {{
                        startGame();
                    }}
                }};
                img.onerror = () => {{
                    console.error('Failed to load asset:', name);
                    assetsLoaded++;
                    if (assetsLoaded === totalAssets) {{
                        startGame();
                    }}
                }};
                img.src = dataUri;
                images[name] = img;
            }}
            return images;
        }}

        const images = loadAssets();
        const totalAssets = Object.keys(assetData).length;"""

            html = html[:match.start()] + replacement + html[match.end():]
            logger.info(f"Replaced dynamic pattern with static dict for {len(asset_manifest)} assets")
            return html

    # STANDARD CASE: Static placeholder replacement
    for name, data in asset_manifest.items():
        data_uri = data.get("data", "") if isinstance(data, dict) else data

        if not data_uri:
            logger.warning(f"No data URI for asset: {name}")
            continue

        # Pattern 1: PLACEHOLDER_name format (primary approach)
        placeholder1 = f'PLACEHOLDER_{name}'
        if placeholder1 in html:
            html = html.replace(placeholder1, data_uri)
            logger.info(f"Injected asset via PLACEHOLDER: {name}")
            continue

        # Pattern 2: JS object property with base64 placeholder
        # Matches: car_clean: 'data:image/png;base64,...'
        pattern2 = rf"({re.escape(name)}:\s*['\"])(data:image/[^;]+;base64,[A-Za-z0-9+/=]{{10,200}})(['\"])"
        matches = re.findall(pattern2, html)
        if matches:
            html = re.sub(pattern2, rf"\g<1>{data_uri}\g<3>", html)
            logger.info(f"Injected asset via pattern2: {name}")
            continue

        # Pattern 3: Same with double quotes
        pattern3 = rf'({re.escape(name)}:\s*")([^"]*data:image[^"]*)(")'
        if re.search(pattern3, html):
            html = re.sub(pattern3, rf'\g<1>{data_uri}\g<3>', html)
            logger.info(f"Injected asset via pattern3: {name}")
            continue

        # Pattern 4: Original placeholder patterns (fallback)
        fallback_patterns = [
            f'{{{{asset:{name}}}}}',
            f'{{asset:{name}}}',
            f'ASSET_{name.upper()}',
            f'"assets/{name}"',
            f"'assets/{name}'",
        ]

        for pattern in fallback_patterns:
            if pattern in html:
                html = html.replace(pattern, data_uri)
                logger.info(f"Injected asset via fallback: {name}")
                break

    return html


# Create the agent
generator_agent = Agent(
    name="GeneratorAgent",
    handoff_description="Generates HTML playable ads using Claude Sonnet 4.5 based on scene spec and assets",
    instructions="""You are a Playable Ad Generator using Claude Sonnet 4.5.

Your job is to generate high-quality HTML playable ads based on the scene specification
and generated assets.

Workflow:
1. Call generate_html() to create the initial HTML using LLM
2. Call get_html_status() to verify the generation
3. If issues are reported by QA, call fix_issues(issues) to fix them
4. Call export_html() when ready for QA validation

The generated HTML should include:
- Complete game mechanics for the specified genre
- All assets embedded as base64 data URIs
- Touch and mouse event handling
- MRAID integration for store redirects
- Canvas-based rendering with requestAnimationFrame
- Progress tracking and victory sequence
- Animated CTA button

For Car Wash genre, include:
- Dirt mask erasure with globalCompositeOperation
- Water particle system
- Hose physics (Verlet integration)
- Proper z-index layering""",
    tools=[generate_html, fix_issues, get_html_status, export_html],
)
