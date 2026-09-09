"""
Technical QA Agent - Validates technical aspects of generated playable ads

Uses Claude Haiku 4.5 for code analysis and validation checks.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any

from agents import Agent, function_tool, RunContextWrapper

logger = logging.getLogger('TechnicalQAAgent')

# Load prompts
PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_prompt(name: str) -> str:
    """Load prompt from prompts directory"""
    prompt_path = PROMPTS_DIR / f"{name}.md"
    if prompt_path.exists():
        return prompt_path.read_text()
    return ""


# Maximum size for playable ads (5MB)
MAX_SIZE_BYTES = 5 * 1024 * 1024


def _check_size(html: str) -> dict:
    """Internal size check logic."""
    size_bytes = len(html.encode('utf-8'))
    size_kb = size_bytes / 1024
    size_mb = size_bytes / (1024 * 1024)
    passed = size_bytes < MAX_SIZE_BYTES

    return {
        "passed": passed,
        "size_bytes": size_bytes,
        "size_kb": round(size_kb, 1),
        "size_mb": round(size_mb, 2),
        "limit_mb": 5,
        "issue": None if passed else f"Size {size_mb:.2f}MB exceeds 5MB limit"
    }


@function_tool
def check_size(ctx: RunContextWrapper[Any]) -> str:
    """
    Check if HTML file size is within limits.

    Playable ads must be under 5MB for most ad networks.

    Returns:
        JSON result with size info and pass/fail status
    """
    memory = ctx.context.get("memory_store")
    if not memory:
        return '{"passed": false, "issue": "Memory store not initialized"}'

    html = memory.get_latest_html()
    if not html:
        return '{"passed": false, "issue": "No HTML to check"}'

    result = _check_size(html)
    return json.dumps(result)


def _check_touch_events(html: str) -> dict:
    """Internal touch events check logic."""
    issues = []

    # Check for touch events
    if "touchstart" not in html:
        issues.append("Missing touchstart event handler")
    if "touchmove" not in html:
        issues.append("Missing touchmove event handler")
    if "touchend" not in html:
        issues.append("Missing touchend event handler")

    # Check for passive: false (needed for preventDefault)
    if "touchmove" in html and "passive" not in html:
        issues.append("touchmove may need { passive: false } for preventDefault")

    # Check for preventDefault
    if "touchmove" in html and "preventDefault" not in html:
        issues.append("Missing preventDefault() on touch events (may cause scrolling)")

    passed = len(issues) == 0

    return {
        "passed": passed,
        "has_touchstart": "touchstart" in html,
        "has_touchmove": "touchmove" in html,
        "has_touchend": "touchend" in html,
        "has_prevent_default": "preventDefault" in html,
        "issues": issues
    }


@function_tool
def check_touch_events(ctx: RunContextWrapper[Any]) -> str:
    """
    Check if touch event handlers are properly implemented.

    Mobile playables must handle touchstart, touchmove, and touchend.

    Returns:
        JSON result with touch event check status
    """
    memory = ctx.context.get("memory_store")
    if not memory:
        return '{"passed": false, "issue": "Memory store not initialized"}'

    html = memory.get_latest_html()
    if not html:
        return '{"passed": false, "issue": "No HTML to check"}'

    result = _check_touch_events(html)
    return json.dumps(result)


def _check_mraid(html: str, scene_spec: dict) -> dict:
    """Internal MRAID check logic."""
    issues = []

    # Check for mraid reference
    has_mraid_check = "mraid" in html.lower()

    if not has_mraid_check:
        issues.append("No MRAID check found - ad may not work in ad networks")

    # Check for mraid.open
    has_mraid_open = "mraid.open" in html

    if not has_mraid_open:
        issues.append("Missing mraid.open() - CTA redirect may not work")

    # Check store URLs
    store_urls = scene_spec.get("store_urls", {})
    android_url = store_urls.get("android", "")
    ios_url = store_urls.get("ios", "")

    if android_url:
        if "play.google.com" not in android_url:
            issues.append(f"Invalid Android URL format: {android_url}")
        if android_url not in html:
            issues.append("Android store URL not found in HTML")

    if ios_url:
        if "apps.apple.com" not in ios_url and "itunes.apple.com" not in ios_url:
            issues.append(f"Invalid iOS URL format: {ios_url}")
        if ios_url not in html:
            issues.append("iOS store URL not found in HTML")

    # Check platform detection
    has_platform_detection = (
        "navigator.userAgent" in html or
        "navigator.platform" in html or
        "userAgent" in html
    )

    if not has_platform_detection:
        issues.append("No platform detection - may open wrong store")

    passed = len(issues) == 0

    return {
        "passed": passed,
        "has_mraid_check": has_mraid_check,
        "has_mraid_open": has_mraid_open,
        "has_platform_detection": has_platform_detection,
        "android_url": android_url if android_url else None,
        "ios_url": ios_url if ios_url else None,
        "issues": issues
    }


@function_tool
def check_mraid(ctx: RunContextWrapper[Any]) -> str:
    """
    Check MRAID integration for ad network compatibility.

    MRAID is required for proper store redirects in ad networks.

    Returns:
        JSON result with MRAID check status
    """
    memory = ctx.context.get("memory_store")
    if not memory:
        return '{"passed": false, "issue": "Memory store not initialized"}'

    html = memory.get_latest_html()
    scene_spec = memory.get("scene_spec") or {}

    if not html:
        return '{"passed": false, "issue": "No HTML to check"}'

    result = _check_mraid(html, scene_spec)
    return json.dumps(result)


def _check_viewport(html: str) -> dict:
    """Internal viewport check logic."""
    issues = []

    # Check for viewport meta
    has_viewport = 'name="viewport"' in html or "name='viewport'" in html

    if not has_viewport:
        issues.append("Missing viewport meta tag")
    else:
        # Check viewport settings
        if "user-scalable=no" not in html and "user-scalable = no" not in html:
            issues.append("Missing user-scalable=no in viewport")

        if "maximum-scale=1" not in html and "maximum-scale = 1" not in html:
            issues.append("Missing maximum-scale=1 in viewport")

    # Check touch-action CSS
    has_touch_action = "touch-action" in html

    if not has_touch_action:
        issues.append("Missing touch-action CSS (may cause scrolling)")
    elif "touch-action: none" not in html and "touch-action:none" not in html:
        issues.append("touch-action should be 'none' for playables")

    # Check overflow hidden
    has_overflow_hidden = "overflow: hidden" in html or "overflow:hidden" in html

    if not has_overflow_hidden:
        issues.append("Missing overflow: hidden (may allow scrolling)")

    passed = len(issues) == 0

    return {
        "passed": passed,
        "has_viewport": has_viewport,
        "has_touch_action": has_touch_action,
        "has_overflow_hidden": has_overflow_hidden,
        "issues": issues
    }


@function_tool
def check_viewport(ctx: RunContextWrapper[Any]) -> str:
    """
    Check viewport meta tag for mobile compatibility.

    Playables need proper viewport settings to prevent zoom/scroll.

    Returns:
        JSON result with viewport check status
    """
    memory = ctx.context.get("memory_store")
    if not memory:
        return '{"passed": false, "issue": "Memory store not initialized"}'

    html = memory.get_latest_html()
    if not html:
        return '{"passed": false, "issue": "No HTML to check"}'

    result = _check_viewport(html)
    return json.dumps(result)


def _check_game_loop(html: str) -> dict:
    """Internal game loop check logic."""
    issues = []

    # Check for requestAnimationFrame
    has_raf = "requestAnimationFrame" in html

    if not has_raf:
        issues.append("Missing requestAnimationFrame - game loop may not be smooth")

    # Check for setInterval/setTimeout game loops (not recommended)
    if "setInterval" in html and "gameLoop" in html.lower():
        issues.append("setInterval used for game loop - prefer requestAnimationFrame")

    # Check for canvas
    has_canvas = "<canvas" in html

    if not has_canvas:
        issues.append("No canvas element found - may not be a canvas-based playable")

    # Check for getContext
    has_context = "getContext" in html

    if not has_context:
        issues.append("Missing getContext - canvas may not be set up properly")

    passed = len(issues) == 0 and has_raf

    return {
        "passed": passed,
        "has_request_animation_frame": has_raf,
        "has_canvas": has_canvas,
        "has_context": has_context,
        "issues": issues
    }


@function_tool
def check_game_loop(ctx: RunContextWrapper[Any]) -> str:
    """
    Check game loop implementation.

    Proper game loop should use requestAnimationFrame.

    Returns:
        JSON result with game loop check status
    """
    memory = ctx.context.get("memory_store")
    if not memory:
        return '{"passed": false, "issue": "Memory store not initialized"}'

    html = memory.get_latest_html()
    if not html:
        return '{"passed": false, "issue": "No HTML to check"}'

    result = _check_game_loop(html)
    return json.dumps(result)


@function_tool
def run_all_checks(ctx: RunContextWrapper[Any]) -> str:
    """
    Run all technical checks and return combined result.

    This is the main entry point for technical QA.

    Returns:
        JSON result with all check results combined
    """
    memory = ctx.context.get("memory_store")
    if not memory:
        return '{"passed": false, "issues": [{"description": "Memory store not initialized"}]}'

    html = memory.get_latest_html()
    if not html:
        return '{"passed": false, "issues": [{"description": "No HTML to check"}]}'

    scene_spec = memory.get("scene_spec") or {}

    # Run all checks by calling internal functions directly
    size_result = _check_size(html)
    touch_result = _check_touch_events(html)
    mraid_result = _check_mraid(html, scene_spec)
    viewport_result = _check_viewport(html)
    game_loop_result = _check_game_loop(html)

    # Combine issues
    all_issues = []

    if not size_result.get("passed"):
        all_issues.append({
            "severity": "critical",
            "category": "size",
            "description": size_result.get("issue", "Size check failed")
        })

    for issue in touch_result.get("issues", []):
        all_issues.append({
            "severity": "major" if "Missing" in issue else "minor",
            "category": "touch_events",
            "description": issue
        })

    for issue in mraid_result.get("issues", []):
        all_issues.append({
            "severity": "critical" if "mraid.open" in issue else "major",
            "category": "mraid",
            "description": issue
        })

    for issue in viewport_result.get("issues", []):
        all_issues.append({
            "severity": "major",
            "category": "viewport",
            "description": issue
        })

    for issue in game_loop_result.get("issues", []):
        all_issues.append({
            "severity": "major" if "requestAnimationFrame" in issue else "minor",
            "category": "game_loop",
            "description": issue
        })

    # Determine overall pass/fail
    critical_issues = [i for i in all_issues if i.get("severity") == "critical"]
    passed = len(critical_issues) == 0

    result = {
        "passed": passed,
        "issues": all_issues,
        "metrics": {
            "file_size_kb": size_result.get("size_kb"),
            "has_touch_events": touch_result.get("has_touchstart", False),
            "has_mraid": mraid_result.get("has_mraid_open", False),
            "uses_raf": game_loop_result.get("has_request_animation_frame", False)
        }
    }

    # Store in memory
    qa_history = memory.get("qa_history") or []
    iteration = len(qa_history)
    if iteration > 0:
        # Update latest entry with technical QA
        qa_history[-1]["technical_qa"] = result
        memory.set("qa_history", qa_history)
    else:
        memory.append_qa_result(
            iteration=1,
            visual_qa={},
            technical_qa=result
        )

    return json.dumps(result, indent=2)


# Create the agent
technical_qa_agent = Agent(
    name="TechnicalQAAgent",
    handoff_description="Validates technical aspects of playable ads (size, touch, MRAID, etc.)",
    instructions=_load_prompt("technical_qa") or """You are a Technical QA Agent for playable ads.

Your job is to validate the technical correctness and compatibility of generated HTML.

Workflow:
1. Call run_all_checks() to run all technical validations at once
2. Or run individual checks for targeted validation:
   - check_size() - verify file size < 5MB
   - check_touch_events() - verify touch event handlers
   - check_mraid() - verify MRAID integration
   - check_viewport() - verify viewport settings
   - check_game_loop() - verify requestAnimationFrame usage

Technical Requirements:
- Size: < 5MB total
- Touch: touchstart, touchmove, touchend with preventDefault
- MRAID: mraid.open() for store redirect
- Viewport: user-scalable=no, maximum-scale=1
- Game loop: requestAnimationFrame (not setInterval)
- Canvas: proper 2D context setup

Severity levels:
- critical: Will cause the ad to fail
- major: May cause issues on some devices
- minor: Best practice violation
- warning: Optimization suggestion""",
    tools=[check_size, check_touch_events, check_mraid, check_viewport, check_game_loop, run_all_checks],
)
