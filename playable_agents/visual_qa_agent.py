"""
Visual QA Agent - Validates visual aspects of generated playable ads

Uses Gemini 3 Flash with Vision for screenshot analysis.
"""

import base64
import json
import logging
import os
from pathlib import Path
from typing import Any

from agents import Agent, function_tool, RunContextWrapper

logger = logging.getLogger('VisualQAAgent')

# Load prompts
PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_prompt(name: str) -> str:
    """Load prompt from prompts directory"""
    prompt_path = PROMPTS_DIR / f"{name}.md"
    if prompt_path.exists():
        return prompt_path.read_text()
    return ""


@function_tool
async def validate_visual(ctx: RunContextWrapper[Any], screenshot_base64: str = "") -> str:
    """
    Validate visual aspects of the playable ad using Gemini Vision.

    Args:
        screenshot_base64: Base64 encoded screenshot (optional, will use context if not provided)

    Returns:
        JSON validation result with issues list
    """
    from services.gemini_client import gemini_client
    import PIL.Image
    import io

    memory = ctx.context.get("memory_store")
    if not memory:
        return '{"passed": false, "issues": [{"severity": "critical", "description": "Memory store not initialized"}]}'

    scene_spec = memory.get("scene_spec") or {}
    asset_list = memory.get("asset_list") or []

    # Get screenshot
    if not screenshot_base64:
        # Try to get from context
        screenshot_base64 = ctx.context.get("screenshot_base64", "")

    if not screenshot_base64:
        return '{"passed": false, "issues": [{"severity": "critical", "description": "No screenshot provided for visual validation"}]}'

    # Load visual QA prompt
    qa_prompt = _load_prompt("visual_qa")

    prompt = f"""{qa_prompt}

## Scene Specification
```json
{json.dumps(scene_spec, indent=2)}
```

## Expected Assets
```json
{json.dumps(asset_list, indent=2)}
```

Analyze the screenshot and return a JSON validation result:
{{
    "passed": true/false,
    "issues": [
        {{
            "severity": "critical|major|minor|warning",
            "category": "asset_presence|positioning|z_index|effects|ui|victory|style",
            "description": "...",
            "suggestion": "..."
        }}
    ],
    "notes": "overall assessment"
}}

Return ONLY valid JSON."""

    try:
        # Decode screenshot
        if screenshot_base64.startswith("data:"):
            screenshot_base64 = screenshot_base64.split(",", 1)[1]

        img_bytes = base64.b64decode(screenshot_base64)
        image = PIL.Image.open(io.BytesIO(img_bytes))

        # Call Gemini Vision
        response = await gemini_client.model.generate_content_async([prompt, image])
        result_text = response.text

        # Parse JSON
        result = gemini_client._parse_json(result_text)

        # Store in memory
        qa_history = memory.get("qa_history") or []
        memory.append_qa_result(
            iteration=len(qa_history) + 1,
            visual_qa=result,
            technical_qa={}  # Will be filled by technical QA
        )

        # Return formatted result
        issues = result.get("issues", [])
        passed = result.get("passed", False)

        summary = f"Visual QA: {'PASSED' if passed else 'FAILED'}\n"
        if issues:
            summary += f"Issues found: {len(issues)}\n"
            for issue in issues[:3]:  # Show first 3
                summary += f"- [{issue.get('severity', 'unknown')}] {issue.get('description', 'No description')}\n"
            if len(issues) > 3:
                summary += f"... and {len(issues) - 3} more issues\n"

        return json.dumps(result, indent=2)

    except Exception as e:
        logger.error(f"Visual validation failed: {e}", exc_info=True)
        return json.dumps({
            "passed": False,
            "issues": [{
                "severity": "critical",
                "category": "validation_error",
                "description": f"Vision analysis failed: {str(e)}",
                "suggestion": "Check screenshot format and Gemini API availability"
            }]
        })


@function_tool
def check_asset_presence(ctx: RunContextWrapper[Any]) -> str:
    """
    Quick check if all expected assets are referenced in HTML.

    Does a simple text search in the HTML for asset references.
    This is a fast pre-check before full visual validation.
    """
    memory = ctx.context.get("memory_store")
    if not memory:
        return "Error: Memory store not initialized"

    html = memory.get_latest_html()
    asset_list = memory.get("asset_list") or []
    asset_manifest = memory.get("asset_manifest") or {}

    if not html:
        return "Error: No HTML generated"

    if not asset_list:
        return "Warning: No asset list defined"

    # Check each asset
    found = []
    missing = []

    for asset in asset_list:
        name = asset.get("name", "unknown")

        # Check if asset is in manifest
        if name not in asset_manifest:
            missing.append(f"{name} (not generated)")
            continue

        # Check if data URI is in HTML
        asset_data = asset_manifest.get(name, {})
        data_uri = asset_data.get("data", "") if isinstance(asset_data, dict) else asset_data

        # Check for first 50 chars of base64 data (enough to verify presence)
        if data_uri and len(data_uri) > 50:
            check_str = data_uri[:50]
            if check_str in html:
                found.append(name)
            else:
                missing.append(f"{name} (not embedded)")
        else:
            missing.append(f"{name} (invalid data)")

    result = f"Asset Presence Check:\n"
    result += f"- Found: {len(found)}/{len(asset_list)}\n"

    if missing:
        result += f"- Missing: {', '.join(missing)}\n"

    return result


@function_tool
def get_visual_qa_history(ctx: RunContextWrapper[Any]) -> str:
    """
    Get history of visual QA results.

    Shows all visual QA iterations and their results.
    """
    memory = ctx.context.get("memory_store")
    if not memory:
        return "Error: Memory store not initialized"

    qa_history = memory.get("qa_history") or []

    if not qa_history:
        return "No visual QA history yet."

    result = f"Visual QA History ({len(qa_history)} iterations):\n\n"

    for entry in qa_history:
        iteration = entry.get("iteration", "?")
        visual_qa = entry.get("visual_qa", {})
        passed = visual_qa.get("passed", False)
        issues = visual_qa.get("issues", [])

        result += f"Iteration {iteration}: {'PASSED' if passed else 'FAILED'}\n"
        if issues:
            result += f"  Issues: {len(issues)}\n"
            for issue in issues[:2]:
                result += f"  - {issue.get('description', 'No description')[:60]}...\n"
        result += "\n"

    return result


# Create the agent
visual_qa_agent = Agent(
    name="VisualQAAgent",
    handoff_description="Validates visual aspects of playable ads using Gemini Vision",
    instructions=_load_prompt("visual_qa") or """You are a Visual QA Agent for playable ads.

Your job is to validate the visual quality and correctness of generated playable ads
by analyzing screenshots.

Workflow:
1. Call check_asset_presence() for a quick pre-check
2. Call validate_visual(screenshot_base64) with a screenshot
3. Call get_visual_qa_history() to review past iterations

Checklist for Visual Validation:
- [ ] All assets from asset_list are visible
- [ ] Assets are properly positioned (not cut off)
- [ ] Z-index layering is correct
- [ ] Water/particle effects are visible (for car-wash)
- [ ] Progress bar is visible and styled
- [ ] UI texts match specification
- [ ] Victory screen appears correctly
- [ ] CTA button is prominent and animated

Severity levels:
- critical: Blocks functionality or severely impacts UX
- major: Significantly affects visual quality
- minor: Small visual imperfection
- warning: Suggestion for improvement""",
    tools=[validate_visual, check_asset_presence, get_visual_qa_history],
)
