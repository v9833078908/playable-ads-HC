# Asset Generator Implementation Plan

**Date:** 2026-02-01
**Module:** `playable_agents/asset_generator.py`
**Purpose:** Generate visual assets for playable ads using Gemini Imagen API

---

## 1. Overview

### 1.1 Purpose
Generate visual assets (characters, backgrounds, tools, UI elements) from text descriptions using Gemini Imagen API based on brief + scene cards + reference images.

### 1.2 Critical Notes

**⚠️ API Migration Status:**
- Project uses `google-genai>=1.0.0` (NEW API) in requirements.txt
- Existing `services/gemini_client.py` still uses DEPRECATED `google.generativeai` API
- `asset_generator.py` MUST use NEW `google-genai` API
- Migration guide: `docs/GEMINI_MIGRATION.md`

**⚠️ Gemini Imagen Availability:**
- Gemini Imagen API for image generation may require separate endpoint
- Check latest API documentation: https://ai.google.dev/api
- Reference images support in Imagen needs verification
- Fallback: Use Gemini Flash with detailed prompts if Imagen unavailable

### 1.3 Pipeline Position
```
PDF/Images → brief_extractor → DraftBrief
                                    ↓
Images → asset analyzer → AssetMapping (reference images)
                                    ↓
DraftBrief + AssetMapping → scenario_builder → list[SceneCard]
                                                      ↓
                                        **asset_generator** → AssetManifest
                                                      ↓
                                              html_generator → HTML
```

### 1.4 Key Design Decisions (from discussion)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Error handling** | Retry 3x for critical, raise with logs | Quality over fallback |
| **Budget** | 2MB max, auto-optimize if exceeded | Playable ad size limit |
| **Критичность** | user_actions → role fallback | Interaction = critical |
| **Парсинг** | LLM asset planner (one call) | Deduplication + smart categorization |
| **Промпты** | role template + brief style | Technical + visual requirements |
| **Референсы** | All references in each API call | Maximum context for consistency |
| **Постобработка** | rembg for character/tool + compression | Transparency + size optimization |
| **Интеграция** | In-memory dict with base64 | No file management needed |
| **Fallback** | None - raise error with logs | Explicit failure over bad quality |
| **Структура** | Single file `asset_generator.py` | Simplicity, no over-engineering |
| **Кэширование** | None - always generate fresh | Stateless, unique each time |

---

## 2. Module Interface

### 2.1 Main Function

```python
def generate_assets(
    brief: DraftBrief,
    scene_cards: list[SceneCard],
    reference_images: list[str]  # base64 data URIs or file paths
) -> dict:
    """
    Generate visual assets for playable ad using Gemini Imagen API.

    Args:
        brief: Extracted PDF brief with title, style, copy texts
        scene_cards: Complete scene descriptions with mechanics and user_actions
        reference_images: Client-provided reference images for style consistency

    Returns:
        AssetManifest dict:
        {
            "assets": [
                {
                    "name": str,           # "hero_character"
                    "role": str,           # "character" | "tool" | "overlay" | "background" | "decoration" | "ui"
                    "z_index": int,        # Render order
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
```

### 2.2 Input Models (existing)

```python
# From models/brief.py
class DraftBrief(BaseModel):
    title: str
    networks: list[str]
    languages: list[str]
    scenes: list[SceneDescription]
    copy_texts: dict[str, str]
    visual_references: list[dict]  # From Gemini PDF analysis

# From playable_agents/scene_card.py
class SceneCard(BaseModel):
    id: str
    title: str
    mechanics: list[str]
    ui_elements: dict[str, str]
    user_actions: list[str]
    technical: dict[str, Any]
```

### 2.3 Output Model (AssetManifest)

```python
# New - to be added to models/ or inline
AssetManifest = dict  # TypedDict structure shown above
```

---

## 3. Implementation Steps

### 3.1 Constants & Configuration

```python
# Asset generation config
MAX_SIZE_BYTES = 2 * 1024 * 1024  # 2MB limit
RETRY_ATTEMPTS = 3                 # For critical assets
GEMINI_MODEL = "gemini-2.0-flash-exp"  # or "imagen-3.0-generate-001"

# Role-specific templates
ROLE_TEMPLATES = {
    "character": {
        "suffix": "centered, single object, transparent background, no shadows on ground",
        "size": (512, 512),
        "z_index": 10
    },
    "tool": {
        "suffix": "centered, single object, transparent background, simple silhouette",
        "size": (256, 256),
        "z_index": 15
    },
    "overlay": {
        "suffix": "seamless texture, tileable, transparent edges",
        "size": (512, 512),
        "z_index": 20
    },
    "background": {
        "suffix": "full frame, no characters, no UI elements, 16:9 aspect",
        "size": (960, 540),
        "z_index": 0
    },
    "decoration": {
        "suffix": "centered, transparent background, small decorative element",
        "size": (128, 128),
        "z_index": 5
    },
    "ui": {
        "suffix": "clean UI element, transparent background, readable text",
        "size": (256, 256),
        "z_index": 25
    }
}
```

### 3.2 Step 1: Asset Planning (LLM)

```python
def _plan_assets(brief: DraftBrief, scene_cards: list[SceneCard]) -> list[dict]:
    """
    Use LLM to extract complete asset list from brief + scene cards.

    Process:
    1. Build prompt with brief context + all scene cards
    2. Call Gemini with asset planner prompt (from docs/misc/prompt)
    3. Parse JSON response with deduplication
    4. Determine critical flag based on user_actions

    Returns:
        [
            {
                "name": "hero_character",
                "role": "character",
                "description": "cartoon knight in blue armor",
                "size_hint": {"width": 512, "height": 512},
                "interactive": True  # From user_actions
            },
            ...
        ]
    """

    # Load asset planner prompt template
    prompt = load_asset_planner_prompt()  # From docs/misc/prompt

    # Build context
    context = {
        "brief": brief.model_dump(),
        "scene_cards": [sc.model_dump() for sc in scene_cards],
        "reference_descriptions": brief.visual_references
    }

    # Call Gemini
    response = gemini_client.generate_content(
        model=GEMINI_MODEL,
        contents=[
            {"text": prompt.format(**context)}
        ]
    )

    # Parse JSON response
    assets_plan = json.loads(extract_json(response.text))

    # Validate and enrich
    for asset in assets_plan:
        asset["critical"] = _is_critical(asset["name"], scene_cards, asset["role"])

    return assets_plan
```

### 3.3 Step 2: Generate Images (Gemini Imagen API)

```python
def _generate_images(
    assets_plan: list[dict],
    brief_style: str,
    reference_images: list[str]
) -> list[dict]:
    """
    Generate images via Gemini Imagen API with retry logic.

    Process:
    1. For each asset in plan:
       a. Build prompt: description + brief_style + role_template_suffix
       b. Call Gemini Imagen with text + all reference images
       c. If critical and fails → retry up to 3 times
       d. If non-critical fails → raise error with logs
    2. Return list of raw image bytes

    Returns:
        [
            {
                "name": "hero_character",
                "role": "character",
                "image_bytes": b"...",  # Raw PNG/JPEG bytes
                "size": (512, 512)
            },
            ...
        ]
    """

    results = []

    for asset in assets_plan:
        # Build prompt
        prompt = _build_prompt(asset, brief_style)

        # Generate with retry
        attempts = RETRY_ATTEMPTS if asset["critical"] else 1

        for attempt in range(attempts):
            try:
                image_bytes = _call_gemini_imagen(
                    prompt=prompt,
                    reference_images=reference_images,
                    size=asset["size_hint"]
                )

                results.append({
                    "name": asset["name"],
                    "role": asset["role"],
                    "image_bytes": image_bytes,
                    "size": asset["size_hint"]
                })
                break

            except Exception as e:
                logger.error(f"Failed to generate {asset['name']}, attempt {attempt+1}/{attempts}", exc_info=True)

                if attempt == attempts - 1:
                    # Final attempt failed
                    raise AssetGenerationError(
                        f"Failed to generate {'critical' if asset['critical'] else 'non-critical'} asset '{asset['name']}'",
                        details={
                            "asset": asset,
                            "error": str(e),
                            "attempts": attempts
                        }
                    )

    return results
```

### 3.4 Step 3: Postprocess & Optimize

```python
def _postprocess_and_optimize(
    raw_images: list[dict],
    assets_plan: list[dict]
) -> dict:
    """
    Postprocess images and build final manifest.

    Process:
    1. For each image:
       a. If role in ["character", "tool"] → apply rembg (background removal)
       b. Compress with PIL optimize=True, quality=85
       c. Convert to base64 data URI
    2. Calculate total size
    3. If > MAX_SIZE_BYTES → auto-optimize:
       a. Reduce JPEG quality: 85 → 70
       b. Resize large assets: 512 → 256
       c. Recalculate size
    4. Build manifest with z_index from ROLE_TEMPLATES

    Returns:
        AssetManifest dict (see 2.1)
    """

    assets = []

    for raw_img, asset_plan in zip(raw_images, assets_plan):
        # Background removal for character/tool
        if raw_img["role"] in ["character", "tool"]:
            image_bytes = rembg.remove(raw_img["image_bytes"])
        else:
            image_bytes = raw_img["image_bytes"]

        # Compress
        image = Image.open(io.BytesIO(image_bytes))
        output = io.BytesIO()
        image.save(output, format="PNG", optimize=True, quality=85)
        compressed_bytes = output.getvalue()

        # Convert to base64
        base64_data = base64.b64encode(compressed_bytes).decode('utf-8')
        data_uri = f"data:image/png;base64,{base64_data}"

        assets.append({
            "name": raw_img["name"],
            "role": raw_img["role"],
            "z_index": ROLE_TEMPLATES[raw_img["role"]]["z_index"],
            "data": data_uri,
            "size": {"width": image.width, "height": image.height},
            "critical": asset_plan["critical"]
        })

    # Calculate total size
    total_size = sum(len(a["data"]) for a in assets)

    # Auto-optimize if needed
    optimized = False
    if total_size > MAX_SIZE_BYTES:
        assets = _auto_optimize(assets)
        total_size = sum(len(a["data"]) for a in assets)
        optimized = True

    # Build manifest
    return {
        "assets": sorted(assets, key=lambda a: a["z_index"]),  # Sort by render order
        "total_size_bytes": total_size,
        "metadata": {
            "generation_time": datetime.utcnow().isoformat(),
            "optimized": optimized,
            "brief_style": _extract_style_from_brief(brief)
        }
    }
```

### 3.5 Helper Functions

```python
def _is_critical(asset_name: str, scene_cards: list[SceneCard], role: str) -> bool:
    """
    Determine if asset is critical based on user interactions.

    Priority:
    1. Primary: Check if asset_name mentioned in any scene's user_actions
    2. Fallback: role in ["character", "tool"] → critical
    """
    # Check user_actions
    for scene in scene_cards:
        for action in scene.user_actions:
            if asset_name.lower() in action.lower():
                return True

    # Fallback to role
    return role in ["character", "tool"]


def _build_prompt(asset: dict, brief_style: str) -> str:
    """
    Build Gemini Imagen prompt from asset plan.

    Format: {description}, {brief_style}, {role_suffix}
    Example: "dirty red car with mud spots, cartoon flat colors mobile game style, centered, single object, transparent background"
    """
    template = ROLE_TEMPLATES[asset["role"]]

    return (
        f'{asset["description"]}, '     # What to draw
        f'{brief_style}, '               # Visual style
        f'{template["suffix"]}'          # Technical requirements
    )


def _extract_style_from_brief(brief: DraftBrief) -> str:
    """
    Extract style keywords from brief for consistent prompts.

    Example: "cartoon flat colors mobile game style"
    """
    # Simple heuristic - can be enhanced with LLM
    style_keywords = ["cartoon", "mobile game", "flat colors"]
    return ", ".join(style_keywords)


def _auto_optimize(assets: list[dict]) -> list[dict]:
    """
    Auto-optimize assets when size exceeds budget.

    Steps:
    1. Reduce JPEG quality: 85 → 70
    2. Resize large assets (>512px) → 256px
    3. Recompress all
    """
    optimized = []

    for asset in assets:
        # Decode base64
        data_uri = asset["data"]
        base64_data = data_uri.split(",")[1]
        image_bytes = base64.b64decode(base64_data)

        # Load image
        image = Image.open(io.BytesIO(image_bytes))

        # Resize if large
        if max(image.size) > 512:
            ratio = 256 / max(image.size)
            new_size = (int(image.width * ratio), int(image.height * ratio))
            image = image.resize(new_size, Image.Resampling.LANCZOS)

        # Recompress with lower quality
        output = io.BytesIO()
        image.save(output, format="PNG", optimize=True, quality=70)
        compressed_bytes = output.getvalue()

        # Re-encode
        base64_data = base64.b64encode(compressed_bytes).decode('utf-8')
        data_uri = f"data:image/png;base64,{base64_data}"

        optimized.append({
            **asset,
            "data": data_uri,
            "size": {"width": image.width, "height": image.height}
        })

    return optimized


def _call_gemini_imagen(prompt: str, reference_images: list[str], size: dict) -> bytes:
    """
    Call Gemini Imagen API to generate image using NEW google-genai API.

    Args:
        prompt: Full text prompt
        reference_images: All reference images (base64 data URIs or file paths)
        size: {"width": int, "height": int}

    Returns:
        Raw image bytes (PNG)

    NOTE: Uses NEW google-genai API (not deprecated google.generativeai)
    """
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    # Determine aspect ratio from size
    width, height = size["width"], size["height"]
    aspect_ratio = "1:1"  # Default square
    if width > height * 1.5:
        aspect_ratio = "16:9"
    elif height > width * 1.5:
        aspect_ratio = "9:16"

    # Prepare reference image parts (if using model that supports it)
    # NOTE: Imagen may not support reference images directly
    # Check latest API docs: https://ai.google.dev/api
    content_parts = [types.Part.from_text(prompt)]

    # If reference images are supported, add them:
    # for ref_img in reference_images:
    #     if ref_img.startswith("data:image"):
    #         # Decode base64 data URI
    #         import base64
    #         mime, b64_data = ref_img.split(",", 1)
    #         img_bytes = base64.b64decode(b64_data)
    #         content_parts.append(types.Part.from_bytes(
    #             data=img_bytes,
    #             mime_type="image/png"
    #         ))

    # Call Imagen API
    # NOTE: Check current API - may be client.models.generate_images or different endpoint
    try:
        response = client.models.generate_images(
            model="imagen-3.0-generate-001",  # Check latest model name
            prompt=prompt,
            config=types.GenerateImageConfig(
                number_of_images=1,
                aspect_ratio=aspect_ratio,
                # Include reference images if API supports it
            )
        )

        # Download generated image
        # API may return URL or bytes directly - check response structure
        if hasattr(response, "images") and response.images:
            image = response.images[0]

            if hasattr(image, "url"):
                # Download from URL
                import requests
                image_bytes = requests.get(image.url).content
            elif hasattr(image, "image_bytes"):
                # Direct bytes
                image_bytes = image.image_bytes
            else:
                raise ValueError(f"Unknown response structure: {type(image)}")

            return image_bytes
        else:
            raise ValueError("No images in response")

    except Exception as e:
        logger.error(f"Gemini Imagen API call failed: {e}", exc_info=True)
        raise

    # ALTERNATIVE: If Imagen API not available, use Gemini with image generation prompt
    # This is a fallback - actual implementation depends on available API endpoints
```

---

## 4. Error Handling

### 4.1 Custom Exception

```python
class AssetGenerationError(Exception):
    """Raised when asset generation fails"""

    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.details = details or {}
```

### 4.2 Logging Strategy

```python
import logging

logger = logging.getLogger(__name__)

# Log levels:
# - INFO: Generation start, completion, asset counts
# - WARNING: Auto-optimization triggered, non-critical failures
# - ERROR: Critical asset failures with full context
# - DEBUG: API calls, prompt details, size calculations
```

---

## 5. Integration Points

### 5.1 Orchestrator Integration

```python
# In playable_agents/orchestrator.py

from playable_agents.asset_generator import generate_assets

def generate_playable(pdf_path: str, images: list[str]) -> str:
    # Existing steps
    brief = extract_brief(pdf_path)
    scene_cards = build_scenario(brief, images)

    # NEW: Generate assets
    try:
        asset_manifest = generate_assets(
            brief=brief,
            scene_cards=scene_cards,
            reference_images=images
        )
    except AssetGenerationError as e:
        logger.error(f"Asset generation failed: {e.details}")
        raise

    # Existing: Generate HTML
    html = generate_html(scene_cards, asset_manifest)

    return html
```

### 5.2 HTML Generator Integration

```python
# In playable_agents/html_generator.py

def generate_html(scene_cards: list[SceneCard], asset_manifest: dict) -> str:
    """
    Generate HTML with assets from manifest.

    Assets are already base64 data URIs, can be directly inserted into <img src="...">
    """

    # Access assets by role or name
    backgrounds = [a for a in asset_manifest["assets"] if a["role"] == "background"]
    characters = [a for a in asset_manifest["assets"] if a["role"] == "character"]

    # Render template
    template = jinja_env.get_template("playable.html")
    html = template.render(
        scenes=scene_cards,
        backgrounds=backgrounds,
        characters=characters,
        # ... other assets
    )

    return html
```

---

## 6. Testing Strategy

### 6.1 Unit Tests

```python
# tests/test_asset_generator.py

def test_is_critical_from_user_actions():
    """Asset mentioned in user_actions should be critical"""
    scene = SceneCard(
        id="s1",
        user_actions=["tap hero_character", "drag sword"]
    )
    assert _is_critical("hero_character", [scene], "decoration") == True


def test_is_critical_fallback_to_role():
    """Character role should be critical by default"""
    scene = SceneCard(id="s1", user_actions=[])
    assert _is_critical("some_character", [scene], "character") == True
    assert _is_critical("some_decoration", [scene], "decoration") == False


def test_build_prompt_format():
    """Prompt should combine description + style + role suffix"""
    asset = {
        "description": "blue knight",
        "role": "character"
    }
    prompt = _build_prompt(asset, "cartoon mobile game")

    assert "blue knight" in prompt
    assert "cartoon mobile game" in prompt
    assert "transparent background" in prompt


def test_auto_optimize_reduces_size():
    """Auto-optimization should reduce total size"""
    # Create mock assets exceeding MAX_SIZE
    large_assets = [create_large_mock_asset() for _ in range(10)]

    optimized = _auto_optimize(large_assets)

    total_before = sum(len(a["data"]) for a in large_assets)
    total_after = sum(len(a["data"]) for a in optimized)

    assert total_after < total_before
```

### 6.2 Integration Test

```python
def test_generate_assets_end_to_end():
    """Full pipeline test with mock Gemini API"""

    # Setup
    brief = DraftBrief(
        title="Test Playable",
        visual_references=[{"style": "cartoon"}]
    )
    scene_cards = [
        SceneCard(
            id="s1",
            mechanics=["drag_drop"],
            user_actions=["drag hero"]
        )
    ]
    references = ["data:image/png;base64,iVBORw0KG..."]  # Mock image

    # Mock Gemini API
    with patch('asset_generator._call_gemini_imagen') as mock_api:
        mock_api.return_value = create_mock_image_bytes()

        # Execute
        manifest = generate_assets(brief, scene_cards, references)

        # Assert
        assert "assets" in manifest
        assert manifest["total_size_bytes"] > 0
        assert manifest["total_size_bytes"] <= MAX_SIZE_BYTES
        assert len(manifest["assets"]) > 0

        # Check asset structure
        asset = manifest["assets"][0]
        assert "name" in asset
        assert "role" in asset
        assert "data" in asset
        assert asset["data"].startswith("data:image/png;base64,")
```

---

## 7. Dependencies

### 7.1 New Dependencies (check requirements.txt)

```txt
# Already present:
google-genai>=1.0.0  ✓
rembg>=2.0.50        ✓
Pillow>=10.2.0       ✓

# May need to add:
requests>=2.31.0     # For downloading generated images (if Imagen returns URLs)
```

**IMPORTANT:** Current `services/gemini_client.py` uses deprecated `google.generativeai` API.
For `asset_generator.py`, use the NEW `google-genai` API as documented in `docs/GEMINI_MIGRATION.md`.

### 7.2 Environment Variables

```bash
# .env
GEMINI_API_KEY=your_api_key_here
```

---

## 8. File Structure

```
playable_agents/
  asset_generator.py          ← NEW (main module)
  orchestrator.py             ← Update to call asset_generator
  html_generator.py           ← Update to use AssetManifest

models/
  assets.py                   ← May add AssetManifest model

docs/
  misc/
    prompt                    ← Asset planner LLM prompt (existing)
    role_template_example     ← Role templates (existing)
  ASSET_GENERATOR_IMPLEMENTATION_PLAN.md  ← THIS FILE

tests/
  test_asset_generator.py     ← NEW
```

---

## 9. Prerequisites (Before Implementation)

### 9.1 API Verification
- [ ] Verify Gemini Imagen API is available and accessible
- [ ] Check API pricing and rate limits
- [ ] Test image generation with sample prompt
- [ ] Confirm reference images support in API

### 9.2 Gemini Client Migration
**Current Issue:** `services/gemini_client.py` uses deprecated API

**Options:**
1. **Migrate existing client** to new API (affects all image analysis)
2. **Create separate client** for asset generation only
3. **Use existing client** temporarily (risky - deprecated)

**Recommendation:** Option 2 - Create `services/imagen_client.py` with new API for asset generation.

### 9.3 Environment Setup
```bash
# Verify dependencies
pip list | grep google-genai
# Should show: google-genai 1.0.0 or higher

# Test new API
python -c "from google import genai; print('✅ New API ready')"

# Verify API key
echo $GEMINI_API_KEY
```

---

## 10. Implementation Checklist

### Phase 1: Core Structure (2-3 hours)
- [ ] Create `playable_agents/asset_generator.py`
- [ ] Define constants (ROLE_TEMPLATES, MAX_SIZE_BYTES)
- [ ] Define AssetGenerationError exception
- [ ] Implement `generate_assets()` main function skeleton
- [ ] Setup logging

### Phase 2: Asset Planning (2-3 hours)
- [ ] Load asset planner prompt from `docs/misc/prompt`
- [ ] Implement `_plan_assets()` with Gemini LLM call
- [ ] Implement `_is_critical()` logic (user_actions → role fallback)
- [ ] Add deduplication logic
- [ ] Unit tests for asset planning

### Phase 3: Image Generation (3-4 hours)
- [ ] Implement `_build_prompt()` with role templates
- [ ] Implement `_call_gemini_imagen()` API integration
- [ ] Implement retry logic for critical assets
- [ ] Add error logging with full context
- [ ] Test with mock API responses

### Phase 4: Postprocessing (2-3 hours)
- [ ] Implement `_postprocess_and_optimize()`
- [ ] Integrate rembg for character/tool background removal
- [ ] Implement compression with PIL
- [ ] Convert to base64 data URIs
- [ ] Test background removal and compression

### Phase 5: Auto-Optimization (2 hours)
- [ ] Implement `_auto_optimize()` function
- [ ] Quality reduction: 85 → 70
- [ ] Resize logic: 512 → 256 for large assets
- [ ] Test size reduction effectiveness

### Phase 6: Integration (2-3 hours)
- [ ] Update `orchestrator.py` to call `generate_assets()`
- [ ] Update `html_generator.py` to use AssetManifest
- [ ] Test full pipeline: PDF → assets → HTML
- [ ] Verify base64 data URIs work in HTML

### Phase 7: Testing & Polish (2-3 hours)
- [ ] Write unit tests (test_asset_generator.py)
- [ ] Write integration test
- [ ] Add logging statements
- [ ] Handle edge cases (empty scene_cards, no references)
- [ ] Documentation in docstrings

### Phase 8: Validation (1-2 hours)
- [ ] Test with real Gemini API
- [ ] Verify size stays under 2MB
- [ ] Check z_index render order
- [ ] Test critical asset retry logic
- [ ] Verify error messages are helpful

**Total Estimated Time:** 16-23 hours

---

## 11. Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Gemini API rate limits | High | Medium | Implement exponential backoff, batch requests |
| Generated images too large | High | Critical | Auto-optimization already planned |
| Background removal fails | Medium | Low | Graceful degradation, log warning |
| Asset planning misses assets | Medium | High | Review prompt quality, add validation |
| Reference images not improving quality | Low | Medium | Test with/without references |

---

## 12. Future Enhancements (Out of Scope for MVP)

- [ ] Caching generated assets by hash(brief + scene_cards)
- [ ] Multiple art styles per playable
- [ ] Progressive quality - generate low-res first for preview
- [ ] Asset variation generation (A/B testing)
- [ ] Custom style transfer from reference images
- [ ] Procedural generation fallback
- [ ] Asset library reuse across playables

---

## 13. Success Criteria

### Must Have
- [x] Generates assets from brief + scene_cards
- [x] Uses Gemini Imagen API
- [x] Applies role-specific templates
- [x] Background removal for character/tool
- [x] Auto-optimization if >2MB
- [x] Retry logic for critical assets
- [x] Returns AssetManifest dict with base64 data URIs
- [x] Integrates into existing pipeline

### Nice to Have
- [ ] Parallel asset generation (async)
- [ ] Progress reporting for UI
- [ ] Asset preview thumbnails
- [ ] Detailed generation metrics

---

**Document Status:** READY FOR IMPLEMENTATION
**Next Step:** Begin Phase 1 - Core Structure
**Estimated Completion:** 16-23 hours of development
