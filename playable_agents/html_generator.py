"""
HTML Generator - Dynamic HTML generation without templates

DEPRECATED: This module is deprecated and will be removed in a future version.
Use generator_agent.py instead, which uses LLM for intelligent HTML generation.

This module generates HTML programmatically based on PlayableSpec mechanics.
Replaces Jinja2 template system with dynamic code generation.

Phase 2 of fix-orchestrator-reset-plan.md

Enhanced with smart effects detection system:
- Detects effects based on mechanics, assets, and scene types
- Generates modular JS blocks for each effect
- Only includes effects that are relevant to the game
"""

import warnings
warnings.warn(
    "html_generator.py is deprecated. Use generator_agent.py instead.",
    DeprecationWarning,
    stacklevel=2
)

import logging
from typing import Any
from models import PlayableSpec, SceneSpec

logger = logging.getLogger(__name__)


# ============================================================================
# EFFECTS DETECTION SYSTEM
# ============================================================================

def detect_effects(spec: PlayableSpec) -> dict[str, bool]:
    """
    Detect which effects should be included in the HTML.

    Uses multi-layer detection:
    1. Mechanics (high priority) - e.g., "car-wash" → water particles
    2. Assets (medium priority) - e.g., "hose" → hose physics
    3. Scene types (additional) - e.g., "tutorial" → tutorial hand
    4. Combined detection - combo rules

    Returns dict of effect_name → enabled
    """
    effects = {
        "hose_physics": False,
        "water_particles": False,
        "parallax_clouds": False,
        "tutorial_hand": False,
        "shimmer_button": True,  # Always enabled for polish
    }

    # Layer 1: Detect by mechanics
    effects.update(_detect_by_mechanics(spec))

    # Layer 2: Detect by assets
    effects.update(_detect_by_assets(spec))

    # Layer 3: Detect by scene types
    effects.update(_detect_by_scene_types(spec))

    # Layer 4: Combined detection
    effects.update(_detect_combined_effects(spec))

    logger.info(f"Detected effects: { {k:v for k,v in effects.items() if v} }")
    return effects


def _detect_by_mechanics(spec: PlayableSpec) -> dict[str, bool]:
    """Detect effects based on mechanics list"""
    effects = {}
    mechanics_str = " ".join(spec.mechanics).lower()

    # Car wash mechanics
    if any(m in mechanics_str for m in ["car-wash", "wash", "clean", "washing"]):
        effects["water_particles"] = True
        effects["parallax_clouds"] = True

    # Drag & drop mechanics
    if any(m in mechanics_str for m in ["drag-drop", "canvas", "drag"]):
        # Hose physics added by asset detection or combined
        pass

    return effects


def _detect_by_assets(spec: PlayableSpec) -> dict[str, bool]:
    """Detect effects based on asset names"""
    effects = {}
    asset_keys = [k.lower() for k in spec.assets.get("images", {}).keys()]

    # If there's a hose/spray tool → add hose physics
    if any(key in asset for key in ["hose", "spray", "karcher", "pressure", "washer"]
           for asset in asset_keys):
        effects["hose_physics"] = True
        effects["water_particles"] = True

    # If there's a hand asset → add tutorial
    if any("hand" in key or "finger" in key for key in asset_keys):
        effects["tutorial_hand"] = True

    # If there are bubbles → add water particles
    if any("bubble" in key for key in asset_keys):
        effects["water_particles"] = True

    # If there are clouds/sky → add parallax
    if any("cloud" in key or "sky" in key for key in asset_keys):
        effects["parallax_clouds"] = True

    return effects


def _detect_by_scene_types(spec: PlayableSpec) -> dict[str, bool]:
    """Detect effects based on scene types"""
    effects = {}

    for scene in spec.scenes:
        if scene.type == "tutorial":
            effects["tutorial_hand"] = True

    return effects


def _detect_combined_effects(spec: PlayableSpec) -> dict[str, bool]:
    """Detect effects based on combinations"""
    effects = {}
    mechanics_str = " ".join(spec.mechanics).lower()
    asset_keys = [k.lower() for k in spec.assets.get("images", {}).keys()]

    # Drag-drop + water assets → both hose physics and particles
    if (any(m in mechanics_str for m in ["drag-drop", "canvas"]) and
        any(key in asset for key in ["water", "hose", "wash", "clean"]
            for asset in asset_keys)):
        effects["water_particles"] = True

    return effects


def generate_html(spec: PlayableSpec) -> str:
    """
    Generate complete HTML from PlayableSpec dynamically.

    This is the main entry point for HTML generation.
    Determines game type from spec.mechanics and generates appropriate HTML.
    """
    logger.info(f"Generating HTML for game: {spec.meta.get('title')}")
    logger.info(f"Mechanics detected: {spec.mechanics}")

    # Detect game type from mechanics
    if any(m in spec.mechanics for m in ["drag-drop", "canvas", "DragDrop"]):
        logger.info("Generating canvas-based drag & drop HTML")
        return generate_canvas_html(spec)
    elif any(m in spec.mechanics for m in ["GridPlacement", "grid"]):
        logger.info("Generating grid-based HTML")
        return generate_grid_html(spec)
    else:
        logger.warning(f"Unknown mechanics: {spec.mechanics}, using default")
        return generate_default_html(spec)


def generate_canvas_html(spec: PlayableSpec) -> str:
    """
    Generate HTML for canvas-based games (car wash, painting, etc.)

    Structure:
    - Canvas element for game rendering
    - Progress bar overlay
    - Victory screen with CTA button
    - Drag & drop JavaScript logic
    """
    title = spec.meta.get('title', 'Playable Game')

    # Extract store URLs with proper fallback
    mraid = spec.mraid if spec.mraid else {}

    store_url = (
        mraid.get('android_url') or
        'https://play.google.com/store/apps/details?id=com.hunterhamster.snailbobrelax'
    )

    ios_url = (
        mraid.get('ios_url') or
        'https://apps.apple.com/app/snail-bob-relax/id6738248473'
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=1.0,user-scalable=no">
<title>{title}</title>
{generate_canvas_styles()}
</head>
<body>
<div id="container">
    <canvas id="canvas" width="640" height="960"></canvas>

    <div id="progressContainer">
        <div id="progressBarBg">
            <div id="waterIcon">💧</div>
            <div id="progressBarFill"></div>
            <div id="progressText">0% Clean</div>
        </div>
    </div>

    <div id="info">🎉 Perfect!</div>
    <button id="nextButton">Next level</button>
</div>

<script>
{generate_canvas_game_logic(spec, store_url, ios_url)}
</script>
</body>
</html>"""

    return html


def generate_canvas_styles() -> str:
    """Generate CSS styles for canvas-based games"""
    return """<style>
/* ========================================
   GLOBAL STYLES
   ======================================== */

* {
    margin: 0;
    padding: 0;
}

body {
    background: #87CEEB;
    overflow: hidden;
    touch-action: none;
    font-family: Arial, sans-serif;
}

#container {
    position: relative;
    width: 100vw;
    height: 100vh;
    display: flex;
    justify-content: center;
    align-items: center;
}

#canvas {
    border: 2px solid #333;
    background: #87CEEB;
    cursor: grab;
}

#canvas:active {
    cursor: grabbing;
}

/* ========================================
   PROGRESS BAR
   ======================================== */

#progressContainer {
    position: absolute;
    top: 170px;
    left: 50%;
    transform: translateX(-50%);
    width: 420px;
    z-index: 100;
    transition: opacity 1s ease;
}

#progressBarBg {
    width: 100%;
    height: 50px;
    background: rgba(50, 50, 50, 0.4);
    border: 3px solid white;
    border-radius: 27px;
    overflow: hidden;
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.25),
                inset 0 2px 6px rgba(0, 0, 0, 0.15);
    position: relative;
}

#progressBarFill {
    height: 100%;
    width: 0%;
    background: linear-gradient(90deg, #3D9AFF 0%, #5FC0FF 50%, #7FD8FF 100%);
    border-radius: 24px;
    transition: width 0.3s ease-out;
    position: relative;
    box-shadow: 0 3px 12px rgba(77, 166, 255, 0.6);
}

#progressBarFill::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 50%;
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.4), transparent);
    border-radius: 24px 24px 0 0;
}

#waterIcon {
    position: absolute;
    left: 15px;
    top: 50%;
    transform: translateY(-50%);
    font-size: 24px;
    z-index: 2;
    filter: drop-shadow(0 2px 3px rgba(0, 0, 0, 0.3));
}

#progressText {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    color: white;
    font-size: 22px;
    font-weight: 700;
    text-shadow: 0 2px 6px rgba(0, 0, 0, 0.6);
    z-index: 1;
    white-space: nowrap;
}

/* Victory text */
#info {
    position: absolute;
    top: 150px;
    left: 50%;
    transform: translateX(-50%);
    color: white;
    font-size: 64px;
    font-weight: bold;
    text-shadow: 3px 3px 6px #000;
    z-index: 99;
    display: none;
    opacity: 0;
    transition: opacity 1s ease;
}

/* CTA Button */
#nextButton {
    position: absolute;
    top: 330px;
    left: 50%;
    transform: translateX(-50%);
    background: linear-gradient(180deg, #5FD068 0%, #4CAF50 50%, #3D8B40 100%);
    color: white;
    font-size: 32px;
    font-weight: 700;
    padding: 20px 60px;
    border: none;
    border-radius: 20px;
    cursor: pointer;
    box-shadow: 0 6px 0 #2d6d32, 0 8px 16px rgba(0,0,0,0.3);
    text-shadow: 0 2px 4px rgba(0,0,0,0.3);
    z-index: 100;
    display: none;
    opacity: 1;
    transition: transform 0.2s ease;
}

#nextButton:hover {
    transform: translateX(-50%) scale(1.05);
    box-shadow: 0 6px 0 #2d6d32, 0 10px 20px rgba(0,0,0,0.4);
}

#nextButton:active {
    transform: translateX(-50%) scale(0.98);
    box-shadow: 0 3px 0 #2d6d32, 0 4px 8px rgba(0,0,0,0.3);
}

/* Animations */
@keyframes pulse {
    0%, 100% {
        transform: translateX(-50%) scale(1);
    }
    50% {
        transform: translateX(-50%) scale(1.05);
    }
}

@keyframes buttonAppear {
    0% {
        opacity: 0;
        transform: translateX(-50%) scale(0.8) translateY(20px);
    }
    50% {
        opacity: 1;
        transform: translateX(-50%) scale(1.08) translateY(-3px);
    }
    100% {
        opacity: 1;
        transform: translateX(-50%) scale(1) translateY(0);
    }
}

#nextButton.appear {
    animation: buttonAppear 0.5s cubic-bezier(0.68, -0.55, 0.265, 1.55) forwards,
               pulse 1.2s ease-in-out infinite 0.5s;
}

/* Shimmer effect */
#nextButton::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 40%;
    height: 100%;
    background: linear-gradient(
        90deg,
        transparent,
        rgba(255, 255, 255, 0.6),
        transparent
    );
    transform: skewX(-20deg);
}

@keyframes shimmer {
    0% {
        left: -100%;
    }
    100% {
        left: 150%;
    }
}

#nextButton.appear::before {
    animation: shimmer 1s ease-out 1.5s infinite 3s;
}
</style>"""


def generate_canvas_game_logic(spec: PlayableSpec, store_url: str, ios_url: str) -> str:
    """Generate JavaScript game logic for canvas drag & drop games"""

    # Extract UI text from first scene
    scene1_ui = spec.scenes[0].ui if spec.scenes else {}
    progress_text = scene1_ui.get('progress_text', '0% Clean')
    victory_text = scene1_ui.get('victory_text', '🎉 Perfect!')
    cta_text = scene1_ui.get('cta_button', 'Next level')

    # Extract assets
    assets_js = generate_assets_embed(spec.assets)

    return f"""/* ========================================
   GAME LOGIC - Canvas Drag & Drop
   Generated dynamically from PlayableSpec
   ======================================== */

console.log("=== Canvas Playable - Generated ===");

/* ========================================
   STORE CONFIGURATION
   ======================================== */

const STORE_CONFIG = {{
    googlePlay: '{store_url}',
    appStore: '{ios_url}'
}};

/* ========================================
   MRAID & DOWNLOAD HANDLER
   ======================================== */

function openStore() {{
    const userAgent = navigator.userAgent || navigator.vendor || '';
    const isAndroid = /android/i.test(userAgent);
    const storeUrl = isAndroid ? STORE_CONFIG.googlePlay : STORE_CONFIG.appStore;

    console.log('Opening store:', storeUrl, '(Platform:', isAndroid ? 'Android' : 'iOS', ')');

    if (window.mraid) {{
        console.log('Using MRAID API');
        mraid.open(storeUrl);
    }} else {{
        console.log('MRAID not available, using window.open fallback');
        window.open(storeUrl, '_blank');
    }}
}}

/* ========================================
   DOM ELEMENTS
   ======================================== */

const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');
const progressContainer = document.getElementById('progressContainer');
const progressBarFill = document.getElementById('progressBarFill');
const progressText = document.getElementById('progressText');
const info = document.getElementById('info');
const nextButton = document.getElementById('nextButton');

/* ========================================
   GAME STATE
   ======================================== */

const game = {{
    width: 640,
    height: 960,
    cleanPercent: 0,
    tutorialDone: false,
    gameComplete: false,
    victoryAnimProgress: 0,
    victoryStartTime: 0,
    washTextAlpha: 1.0,
    hose: {{
        x: 320,
        y: 820,
        width: 150,
        height: 150,
        isDragging: false
    }}
}};

/* ========================================
   ASSETS
   ======================================== */

{assets_js}

/* ========================================
   DRAG & DROP LOGIC
   ======================================== */

let isDragging = false;
let mouseX = 0;
let mouseY = 0;

// Mouse events
canvas.addEventListener('mousedown', (e) => {{
    const rect = canvas.getBoundingClientRect();
    mouseX = (e.clientX - rect.left) * (canvas.width / rect.width);
    mouseY = (e.clientY - rect.top) * (canvas.height / rect.height);

    if (isOverHose(mouseX, mouseY)) {{
        isDragging = true;
        game.hose.isDragging = true;
        game.tutorialDone = true;
    }}
}});

canvas.addEventListener('mousemove', (e) => {{
    const rect = canvas.getBoundingClientRect();
    mouseX = (e.clientX - rect.left) * (canvas.width / rect.width);
    mouseY = (e.clientY - rect.top) * (canvas.height / rect.height);

    if (isDragging) {{
        game.hose.x = mouseX;
        game.hose.y = mouseY;

        // Increase clean progress when dragging
        if (!game.gameComplete) {{
            game.cleanPercent = Math.min(100, game.cleanPercent + 0.5);
            updateProgress();
        }}
    }}
}});

canvas.addEventListener('mouseup', () => {{
    isDragging = false;
    game.hose.isDragging = false;
}});

// Touch events
canvas.addEventListener('touchstart', (e) => {{
    e.preventDefault();
    const rect = canvas.getBoundingClientRect();
    const touch = e.touches[0];
    mouseX = (touch.clientX - rect.left) * (canvas.width / rect.width);
    mouseY = (touch.clientY - rect.top) * (canvas.height / rect.height);

    if (isOverHose(mouseX, mouseY)) {{
        isDragging = true;
        game.hose.isDragging = true;
        game.tutorialDone = true;
    }}
}});

canvas.addEventListener('touchmove', (e) => {{
    e.preventDefault();
    const rect = canvas.getBoundingClientRect();
    const touch = e.touches[0];
    mouseX = (touch.clientX - rect.left) * (canvas.width / rect.width);
    mouseY = (touch.clientY - rect.top) * (canvas.height / rect.height);

    if (isDragging) {{
        game.hose.x = mouseX;
        game.hose.y = mouseY;

        if (!game.gameComplete) {{
            game.cleanPercent = Math.min(100, game.cleanPercent + 0.5);
            updateProgress();
        }}
    }}
}});

canvas.addEventListener('touchend', () => {{
    isDragging = false;
    game.hose.isDragging = false;
}});

function isOverHose(x, y) {{
    return x >= game.hose.x - game.hose.width/2 &&
           x <= game.hose.x + game.hose.width/2 &&
           y >= game.hose.y - game.hose.height/2 &&
           y <= game.hose.y + game.hose.height/2;
}}

/* ========================================
   PROGRESS & VICTORY
   ======================================== */

function updateProgress() {{
    const percent = Math.floor(game.cleanPercent);
    progressBarFill.style.width = percent + '%';
    progressText.textContent = percent + '% Clean';

    if (percent >= 100 && !game.gameComplete) {{
        triggerVictory();
    }}
}}

function triggerVictory() {{
    game.gameComplete = true;
    game.victoryStartTime = Date.now();

    // Hide progress bar
    progressContainer.style.opacity = '0';
    setTimeout(() => {{
        progressContainer.style.display = 'none';
    }}, 1000);

    // Show victory text
    info.textContent = '{victory_text}';
    info.style.display = 'block';
    setTimeout(() => {{
        info.style.opacity = '1';
    }}, 100);

    // Show CTA button
    setTimeout(() => {{
        nextButton.textContent = '{cta_text}';
        nextButton.style.display = 'block';
        nextButton.classList.add('appear');
    }}, 800);
}}

// CTA button click
nextButton.addEventListener('click', (e) => {{
    e.stopPropagation();
    openStore();
}});

// Click anywhere after victory to open store
document.addEventListener('click', (e) => {{
    if (game.gameComplete && e.target !== nextButton) {{
        openStore();
    }}
}});

/* ========================================
   GAME LOOP
   ======================================== */

function gameLoop() {{
    // Clear canvas
    ctx.clearRect(0, 0, game.width, game.height);

    // Draw sky background
    ctx.fillStyle = '#87CEEB';
    ctx.fillRect(0, 0, game.width, game.height);

    // === CAR (Critical) ===
    const carX = 170;
    const carY = 400;
    const carW = 300;
    const carH = 150;

    // Find car images (flexible naming)
    const carClean = images.char_0 || images.main_gameplay_object_0;
    const carDirt = images.decoration_0;

    if (carClean && carClean.complete) {{
        // Use real image
        ctx.drawImage(carClean, carX, carY, carW, carH);

        // === DIRT OVERLAY (Optional) ===
        if (carDirt && carDirt.complete && game.cleanPercent < 100) {{
            ctx.globalAlpha = 1 - (game.cleanPercent / 100);
            ctx.drawImage(carDirt, carX, carY, carW, carH);
            ctx.globalAlpha = 1.0;
        }} else if (game.cleanPercent < 100) {{
            // Fallback: dark overlay
            ctx.fillStyle = `rgba(100, 80, 60, ${{0.6 * (1 - game.cleanPercent / 100)}})`;
            ctx.fillRect(carX, carY, carW, carH);
        }}
    }} else {{
        // Fallback: colored rectangle
        ctx.fillStyle = '#CC0000';
        ctx.fillRect(carX, carY, carW, carH);
        ctx.fillStyle = '#FF6666';
        ctx.fillRect(carX, carY - 20, carW, 20);

        // Add visual feedback that cleaning works
        if (game.cleanPercent > 0) {{
            ctx.fillStyle = `rgba(255, 100, 100, ${{game.cleanPercent / 100}})`;
            ctx.fillRect(carX, carY, carW * (game.cleanPercent / 100), carH);
        }}
    }}

    // === HOSE (Important) ===
    const hoseImg = images.tool_0 || images.interactive_tool_0;
    const hW = 80;
    const hH = 120;

    if (hoseImg && hoseImg.complete) {{
        ctx.drawImage(hoseImg, game.hose.x - hW/2, game.hose.y - hH/2, hW, hH);
    }} else {{
        // Fallback: blue circle
        ctx.fillStyle = '#4A90E2';
        ctx.beginPath();
        ctx.arc(game.hose.x, game.hose.y, 40, 0, Math.PI * 2);
        ctx.fill();
    }}

    // Draw water spray if dragging
    if (game.hose.isDragging) {{
        ctx.strokeStyle = 'rgba(100, 200, 255, 0.6)';
        ctx.lineWidth = 15;
        ctx.beginPath();
        ctx.moveTo(game.hose.x, game.hose.y);
        ctx.lineTo(game.hose.x, game.hose.y - 100);
        ctx.stroke();
    }}

    requestAnimationFrame(gameLoop);
}}

// Start game loop
gameLoop();
console.log("Game loop started");
"""


def generate_assets_embed(assets: dict[str, Any]) -> str:
    """
    Generate JavaScript code to embed assets as base64

    Returns: JavaScript object containing all assets with image loading logic
    """
    images_dict = assets.get("images", {})
    background = assets.get("background")

    # Build JavaScript object with all images
    js_images = "{\n"
    for key, data_url in images_dict.items():
        # Escape quotes in data URL
        escaped_url = data_url.replace('"', '\\"') if data_url else ""
        js_images += f'        "{key}": "{escaped_url}",\n'
    js_images = js_images.rstrip(",\n") + "\n    }"

    js_bg = f'"{background}"' if background else "null"

    return f"""const ASSETS = {{
    images: {js_images},
    background: {js_bg}
}};

const images = {{}};
let imagesLoaded = 0;
const totalImages = Object.keys(ASSETS.images).length;

function loadImage(key, src) {{
    return new Promise((resolve) => {{
        const img = new Image();
        img.onload = () => {{
            images[key] = img;
            imagesLoaded++;
            console.log(`Loaded: ${{key}} (${{img.width}}x${{img.height}})`);
            resolve();
        }};
        img.onerror = () => {{
            console.error(`Failed to load: ${{key}}`);
            resolve();
        }};
        img.src = src;
    }});
}}

Promise.all(
    Object.entries(ASSETS.images).map(([key, src]) => loadImage(key, src))
).then(() => {{
    const requiredAssets = ['char_0', 'tool_0', 'decoration_0'];
    const missingAssets = requiredAssets.filter(key => !images[key]);

    if (missingAssets.length > 0) {{
        console.warn('Missing assets, using fallbacks:', missingAssets);
    }}

    console.log(`Game ready: ${{imagesLoaded}}/${{totalImages}} images loaded`);
}});

console.log("Assets initialized:", totalImages, "images to load");
"""


def generate_grid_html(spec: PlayableSpec) -> str:
    """
    Generate HTML for grid-based games (merge, placement, etc.)

    TODO: Implement grid generation (currently not used)
    """
    logger.warning("Grid HTML generation not yet implemented, using template fallback")
    # Fallback to old template system for now
    from tools.spec_tools import render_template
    return render_template(spec, "ship_grid_merge_v1")


def generate_default_html(spec: PlayableSpec) -> str:
    """
    Generate default HTML when mechanics are unknown

    Falls back to template system
    """
    logger.warning(f"Unknown mechanics {spec.mechanics}, using template fallback")
    from tools.spec_tools import render_template
    return render_template(spec, "ship_grid_merge_v1")
