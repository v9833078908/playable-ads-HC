"""
Screenshot Tool — Multi-state Playwright screenshots for Orchestrator V2

Takes screenshots of HTML playable ads in different game states
by simulating touch/mouse interactions via Playwright.
"""

import asyncio
import base64
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger('ScreenshotTool')

# Mechanic → Playwright action mapping
MECHANIC_ACTIONS = {
    "drag-to-clean": "touch_swipe",
    "scratch": "touch_swipe",
    "reveal-mask": "touch_swipe",
    "tap-target": "tap",
    "whack-a-mole": "tap",
    "drag-and-drop": "touch_drag",
    "cta": "tap_cta",
}


async def take_screenshots(
    html_path: str,
    scene_spec: dict,
    viewport: dict = None,
) -> list[dict]:
    """
    Take multi-state screenshots of an HTML playable ad.

    Args:
        html_path: Path to HTML file
        scene_spec: Scene specification with scenes list
        viewport: Optional viewport size {width, height}

    Returns:
        List of {state_name: str, screenshot_base64: str}
    """
    from playwright.async_api import async_playwright

    if not viewport:
        viewport = {"width": 540, "height": 960}

    html_file = Path(html_path)
    if not html_file.exists():
        logger.error(f"HTML file not found: {html_path}")
        return []

    file_url = f"file://{html_file.absolute()}"

    # Build states from scene_spec
    states = _build_states(scene_spec)
    logger.info(f"Taking {len(states)} screenshots for {len(scene_spec.get('scenes', []))} scenes")

    screenshots = []

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport=viewport,
                device_scale_factor=2,  # Retina for better quality
                has_touch=True,
            )
            page = await context.new_page()

            # Navigate to HTML
            try:
                await page.goto(file_url, wait_until="networkidle", timeout=15000)
            except Exception as e:
                logger.warning(f"Page load timeout/error (may be ok): {e}")

            # Wait for initial render
            await page.wait_for_timeout(1500)

            for state in states:
                try:
                    # Execute action if any (with timeout)
                    if state.get("action"):
                        try:
                            await asyncio.wait_for(
                                _simulate_action(page, state["action"], viewport),
                                timeout=10.0,
                            )
                        except asyncio.TimeoutError:
                            logger.warning(f"Action timeout for state '{state['name']}', continuing")

                    # Wait for animations/state changes
                    wait_ms = state.get("wait", 500)
                    await page.wait_for_timeout(wait_ms)

                    # Take screenshot
                    screenshot_bytes = await page.screenshot(type="png")
                    b64 = base64.b64encode(screenshot_bytes).decode('utf-8')

                    screenshots.append({
                        "state_name": state["name"],
                        "screenshot_base64": b64,
                    })
                    logger.info(f"Screenshot: {state['name']} ({len(screenshot_bytes)} bytes)")

                except Exception as e:
                    logger.error(f"Failed screenshot for state '{state['name']}': {e}")
                    screenshots.append({
                        "state_name": state["name"],
                        "screenshot_base64": "",
                        "error": str(e),
                    })

            await browser.close()

    except Exception as e:
        logger.error(f"Playwright error: {e}", exc_info=True)
        return [{"state_name": "error", "screenshot_base64": "", "error": str(e)}]

    return screenshots


def _build_states(scene_spec: dict) -> list[dict]:
    """
    Build screenshot states from scene_spec.scenes.

    Each scene becomes 1-2 states depending on mechanic.
    """
    scenes = scene_spec.get("scenes", [])
    states = []

    # Always start with initial state
    states.append({
        "name": "initial",
        "action": None,
        "wait": 1500,
    })

    for scene in scenes:
        name = scene.get("name", "unknown")
        mechanic = scene.get("mechanic", "")

        action_type = MECHANIC_ACTIONS.get(mechanic)

        if mechanic == "cta":
            # CTA scene — just wait, don't click (would navigate away)
            states.append({
                "name": f"{name}",
                "action": None,
                "wait": 1000,
            })
        elif action_type == "touch_swipe":
            # Swipe mechanics: take screenshot at 50% progress
            states.append({
                "name": f"{name}_50",
                "action": {"type": "touch_swipe", "coverage": 0.5},
                "wait": 1000,
            })
        elif action_type == "tap":
            # Tap mechanics: tap center
            states.append({
                "name": f"{name}_tap",
                "action": {"type": "tap", "x": 0.5, "y": 0.5},
                "wait": 800,
            })
        elif action_type == "touch_drag":
            states.append({
                "name": f"{name}_drag",
                "action": {"type": "touch_drag", "from_x": 0.3, "from_y": 0.5, "to_x": 0.7, "to_y": 0.5},
                "wait": 1000,
            })
        else:
            # Unknown mechanic — just wait
            states.append({
                "name": name,
                "action": None,
                "wait": 800,
            })

    return states


async def _simulate_action(page, action: dict, viewport: dict) -> None:
    """Execute a simulated user interaction on the page."""
    action_type = action.get("type")
    w = viewport["width"]
    h = viewport["height"]

    if action_type == "touch_swipe":
        coverage = action.get("coverage", 0.5)
        await _touch_swipe(page, w, h, coverage)

    elif action_type == "tap":
        x = int(action.get("x", 0.5) * w)
        y = int(action.get("y", 0.5) * h)
        await page.tap(f"canvas", position={"x": x, "y": y}, force=True)

    elif action_type == "tap_cta":
        # Try to find CTA button
        cta = await page.query_selector(".cta-button, .cta, [class*='cta'], button")
        if cta:
            await cta.tap()
        else:
            # Tap bottom center (common CTA position)
            await page.tap("body", position={"x": w // 2, "y": int(h * 0.85)}, force=True)

    elif action_type == "touch_drag":
        fx = int(action.get("from_x", 0.3) * w)
        fy = int(action.get("from_y", 0.5) * h)
        tx = int(action.get("to_x", 0.7) * w)
        ty = int(action.get("to_y", 0.5) * h)
        await _touch_drag(page, fx, fy, tx, ty)


async def _touch_swipe(page, width: int, height: int, coverage: float) -> None:
    """
    Simulate touch swipe across the canvas to trigger cleaning/reveal mechanics.
    Covers `coverage` fraction of the canvas area with zigzag pattern.
    """
    canvas = await page.query_selector("canvas")
    if not canvas:
        logger.warning("No canvas found, swiping on body")

    # Zigzag pattern across the canvas
    steps = int(coverage * 20)  # More steps = more coverage
    step_y = height // max(steps, 1)

    for i in range(steps):
        y = int(step_y * i + step_y / 2)
        # Alternate left-to-right and right-to-left
        if i % 2 == 0:
            x_start, x_end = int(width * 0.15), int(width * 0.85)
        else:
            x_start, x_end = int(width * 0.85), int(width * 0.15)

        # Dispatch touch events via JS for reliability
        await page.evaluate(f"""() => {{
            const canvas = document.querySelector('canvas') || document.body;
            const rect = canvas.getBoundingClientRect();

            function dispatchTouch(type, x, y) {{
                const touch = new Touch({{
                    identifier: 1,
                    target: canvas,
                    clientX: rect.left + x,
                    clientY: rect.top + y,
                }});
                canvas.dispatchEvent(new TouchEvent(type, {{
                    touches: type === 'touchend' ? [] : [touch],
                    changedTouches: [touch],
                    cancelable: true,
                }}));
            }}

            dispatchTouch('touchstart', {x_start}, {y});
            const dx = ({x_end} - {x_start}) > 0 ? 15 : -15;
            for (let x = {x_start}; dx > 0 ? x < {x_end} : x > {x_end}; x += dx) {{
                dispatchTouch('touchmove', x, {y});
            }}
            dispatchTouch('touchend', {x_end}, {y});
        }}""")
        await page.wait_for_timeout(50)


async def _touch_drag(page, from_x: int, from_y: int, to_x: int, to_y: int) -> None:
    """Simulate a touch drag from one point to another."""
    await page.evaluate(f"""() => {{
        const canvas = document.querySelector('canvas') || document.body;
        const rect = canvas.getBoundingClientRect();

        function dispatchTouch(type, x, y) {{
            const touch = new Touch({{
                identifier: 1,
                target: canvas,
                clientX: rect.left + x,
                clientY: rect.top + y,
            }});
            canvas.dispatchEvent(new TouchEvent(type, {{
                touches: type === 'touchend' ? [] : [touch],
                changedTouches: [touch],
                cancelable: true,
            }}));
        }}

        dispatchTouch('touchstart', {from_x}, {from_y});
        const steps = 10;
        for (let i = 1; i <= steps; i++) {{
            const t = i / steps;
            const x = {from_x} + ({to_x} - {from_x}) * t;
            const y = {from_y} + ({to_y} - {from_y}) * t;
            dispatchTouch('touchmove', x, y);
        }}
        dispatchTouch('touchend', {to_x}, {to_y});
    }}""")
