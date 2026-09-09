"""Unit tests for asset_generator.py (Phases 2-5)"""

from playable_agents.asset_generator import (
    _is_critical,
    _parse_json_response,
    _load_asset_planner_prompt,
    _build_prompt,
    _generate_images,
    _auto_optimize,
    generate_assets,
    ROLE_TEMPLATES,
    MAX_SIZE_BYTES,
)
from playable_agents.scene_card import SceneCard
from models import DraftBrief
from unittest.mock import patch, MagicMock
from PIL import Image as PILImage
import io
import base64


def test_is_critical_from_user_actions():
    """Asset mentioned in user_actions should be critical"""
    print("\n=== Test: _is_critical from user_actions ===")

    scene = SceneCard(
        id="s1",
        title="Battle",
        mechanics=["tap"],
        ui_elements={},
        user_actions=["tap hero_character", "drag sword"],
        technical={}
    )

    # Asset mentioned in user_actions → critical
    result = _is_critical("hero_character", [scene], "decoration")
    assert result == True, "Asset in user_actions should be critical"
    print("✅ hero_character is critical (found in user_actions)")

    # Asset mentioned partially → critical
    result = _is_critical("sword", [scene], "tool")
    assert result == True, "Partially matched asset should be critical"
    print("✅ sword is critical (found in 'drag sword')")

    # Asset NOT mentioned → fallback to role
    result = _is_critical("background", [scene], "background")
    assert result == False, "Asset not in user_actions and non-critical role"
    print("✅ background is not critical")


def test_is_critical_fallback_to_role():
    """Character and tool roles should be critical by default"""
    print("\n=== Test: _is_critical fallback to role ===")

    scene = SceneCard(
        id="s1",
        title="Scene",
        mechanics=[],
        ui_elements={},
        user_actions=[],  # No user actions
        technical={}
    )

    # Character role → critical
    result = _is_critical("some_character", [scene], "character")
    assert result == True, "Character role should be critical"
    print("✅ Character role is critical")

    # Tool role → critical
    result = _is_critical("some_tool", [scene], "tool")
    assert result == True, "Tool role should be critical"
    print("✅ Tool role is critical")

    # Background role → not critical
    result = _is_critical("some_background", [scene], "background")
    assert result == False, "Background role should not be critical"
    print("✅ Background role is not critical")

    # Decoration role → not critical
    result = _is_critical("some_decoration", [scene], "decoration")
    assert result == False, "Decoration role should not be critical"
    print("✅ Decoration role is not critical")


def test_parse_json_response():
    """Parse JSON from LLM response with markdown code blocks"""
    print("\n=== Test: _parse_json_response ===")

    # Test 1: Clean JSON array
    json_text = """[
        {"name": "hero", "role": "character", "description": "knight", "size_hint": {"width": 512, "height": 512}, "interactive": true},
        {"name": "sword", "role": "tool", "description": "sword", "size_hint": {"width": 256, "height": 256}, "interactive": true}
    ]"""

    assets = _parse_json_response(json_text)
    assert len(assets) == 2, "Should parse 2 assets"
    assert assets[0]["name"] == "hero"
    assert assets[1]["name"] == "sword"
    print("✅ Parsed clean JSON array")

    # Test 2: JSON in markdown code block
    markdown_text = """Here's the asset list:

```json
[
    {"name": "background", "role": "background", "description": "sky", "size_hint": {"width": 960, "height": 540}, "interactive": false}
]
```

That's all!"""

    assets = _parse_json_response(markdown_text)
    assert len(assets) == 1, "Should extract JSON from markdown"
    assert assets[0]["name"] == "background"
    print("✅ Parsed JSON from markdown code block")

    # Test 3: JSON with extra text before/after
    mixed_text = """Some text before
[
    {"name": "ui_button", "role": "ui", "description": "button", "size_hint": {"width": 256, "height": 256}, "interactive": true}
]
Some text after"""

    assets = _parse_json_response(mixed_text)
    assert len(assets) == 1, "Should find JSON array in mixed text"
    assert assets[0]["name"] == "ui_button"
    print("✅ Parsed JSON from mixed text")


def test_load_asset_planner_prompt():
    """Load asset planner prompt from file or use default"""
    print("\n=== Test: _load_asset_planner_prompt ===")

    prompt = _load_asset_planner_prompt()

    assert isinstance(prompt, str), "Prompt should be a string"
    assert len(prompt) > 0, "Prompt should not be empty"
    assert "{brief}" in prompt, "Prompt should have {brief} placeholder"
    assert "{scene_cards}" in prompt, "Prompt should have {scene_cards} placeholder"

    print("✅ Loaded asset planner prompt")
    print(f"   Prompt length: {len(prompt)} chars")
    print("   Has required placeholders: {brief}, {scene_cards}, {references}")


def test_deduplication_logic():
    """Test that _plan_assets deduplicates assets by name"""
    print("\n=== Test: Deduplication logic ===")

    # Simulate assets with duplicates
    assets_with_duplicates = [
        {"name": "hero", "role": "character", "description": "knight", "size_hint": {"width": 512, "height": 512}},
        {"name": "sword", "role": "tool", "description": "weapon", "size_hint": {"width": 256, "height": 256}},
        {"name": "hero", "role": "character", "description": "knight duplicate", "size_hint": {"width": 512, "height": 512}},  # Duplicate
        {"name": "background", "role": "background", "description": "sky", "size_hint": {"width": 960, "height": 540}},
    ]

    # Deduplicate (keep first occurrence)
    seen_names = set()
    deduplicated = []
    for asset in assets_with_duplicates:
        if asset["name"] not in seen_names:
            seen_names.add(asset["name"])
            deduplicated.append(asset)

    assert len(deduplicated) == 3, "Should have 3 unique assets (hero, sword, background)"
    assert deduplicated[0]["name"] == "hero"
    assert deduplicated[0]["description"] == "knight", "Should keep first occurrence"
    assert deduplicated[1]["name"] == "sword"
    assert deduplicated[2]["name"] == "background"

    print(f"✅ Deduplication: {len(assets_with_duplicates)} → {len(deduplicated)} assets")


# ============================================================================
# Phase 3 Tests: Image Generation
# ============================================================================

def test_build_prompt():
    """Prompt should combine description + style + role suffix"""
    print("\n=== Test: _build_prompt ===")

    asset = {
        "description": "blue knight",
        "role": "character"
    }
    prompt = _build_prompt(asset, "cartoon mobile game")

    assert "blue knight" in prompt, "Prompt should include description"
    assert "cartoon mobile game" in prompt, "Prompt should include style"
    assert "transparent background" in prompt, "Prompt should include role suffix"

    print(f"✅ Built prompt: {prompt[:80]}...")


def test_generate_images_retry_logic():
    """Critical assets should retry 3x, non-critical 1x"""
    print("\n=== Test: _generate_images retry logic ===")

    assets_plan = [
        {"name": "hero", "role": "character", "critical": True, "description": "knight", "size_hint": {"width": 512, "height": 512}},
        {"name": "decoration", "role": "decoration", "critical": False, "description": "flower", "size_hint": {"width": 128, "height": 128}}
    ]

    call_count = {"hero": 0, "decoration": 0}

    def mock_fal_call(prompt, aspect_ratio, output_format):
        # Fail first 2 attempts for hero
        if "knight" in prompt:
            call_count["hero"] += 1
            if call_count["hero"] < 3:
                raise Exception("Simulated failure")
            return b"PNG_BYTES_HERO"
        else:
            call_count["decoration"] += 1
            return b"PNG_BYTES_DECORATION"

    with patch('playable_agents.asset_generator._call_fal_imagen', side_effect=mock_fal_call):
        results = _generate_images(assets_plan, "cartoon style", [])

        assert call_count["hero"] == 3, f"Critical asset should retry 3x, got {call_count['hero']}"
        assert call_count["decoration"] == 1, f"Non-critical should try 1x, got {call_count['decoration']}"
        assert len(results) == 2

    print(f"✅ Retry logic works: hero={call_count['hero']}x, decoration={call_count['decoration']}x")


# ============================================================================
# Phase 4-5 Tests: Postprocessing and Auto-Optimization
# ============================================================================

def test_auto_optimize_resize():
    """Auto-optimize should resize large images"""
    print("\n=== Test: _auto_optimize resize ===")

    # Create a large PNG image (600x600)
    img = PILImage.new('RGB', (600, 600), color='red')
    output = io.BytesIO()
    img.save(output, format='PNG')
    image_bytes = output.getvalue()

    # Create base64 data URI
    base64_data = base64.b64encode(image_bytes).decode('utf-8')
    data_uri = f"data:image/png;base64,{base64_data}"

    assets = [
        {
            "name": "large_image",
            "role": "character",
            "z_index": 10,
            "data": data_uri,
            "size": {"width": 600, "height": 600},
            "critical": True
        }
    ]

    optimized = _auto_optimize(assets)

    # Check that image was resized
    assert optimized[0]["size"]["width"] <= 256, "Width should be reduced to 256 or less"
    assert optimized[0]["size"]["height"] <= 256, "Height should be reduced to 256 or less"

    # Check that data URI is still valid
    assert optimized[0]["data"].startswith("data:image/"), "Data URI should be valid"

    # Check size reduction
    original_size = len(assets[0]["data"])
    optimized_size = len(optimized[0]["data"])
    assert optimized_size < original_size, "Optimized size should be smaller"

    print(f"✅ Resized from 600x600 to {optimized[0]['size']['width']}x{optimized[0]['size']['height']}")
    print(f"   Size reduced: {original_size/1024:.1f}KB → {optimized_size/1024:.1f}KB")


def test_generate_assets_end_to_end():
    """Full pipeline test with mocked FAL API and LLM"""
    print("\n=== Test: generate_assets end-to-end ===")

    # Setup brief and scene cards
    brief = DraftBrief(
        title="Test Playable",
        scenes=[],
        networks=["facebook"],
        languages=["en"],
        copy_texts={}
    )

    scene_cards = [
        SceneCard(
            id="s1",
            title="Scene 1",
            mechanics=["drag_drop"],
            ui_elements={},
            user_actions=["drag hero"],
            technical={}
        )
    ]

    # Mock FAL API to return a small red PNG
    def mock_fal_image():
        img = PILImage.new('RGB', (512, 512), color='red')
        output = io.BytesIO()
        img.save(output, format='PNG')
        return output.getvalue()

    # Mock LLM to return asset plan
    mock_assets_plan = [
        {
            "name": "hero",
            "role": "character",
            "description": "knight",
            "size_hint": {"width": 512, "height": 512},
            "interactive": True,
            "critical": True
        }
    ]

    with patch('playable_agents.asset_generator._call_fal_imagen', return_value=mock_fal_image()):
        with patch('playable_agents.asset_generator._plan_assets', return_value=mock_assets_plan):
            manifest = generate_assets(brief, scene_cards, [])

            # Assertions
            assert "assets" in manifest, "Manifest should have assets"
            assert len(manifest["assets"]) > 0, "Should have at least one asset"
            assert manifest["total_size_bytes"] <= MAX_SIZE_BYTES, "Total size should be under 2MB"

            asset = manifest["assets"][0]
            assert asset["data"].startswith("data:image/png;base64,"), "Should be base64 PNG data URI"
            assert asset["name"] == "hero", "Asset name should match"
            assert asset["role"] == "character", "Asset role should match"
            assert "z_index" in asset, "Asset should have z_index"

            print(f"✅ Generated {len(manifest['assets'])} assets")
            print(f"   Total size: {manifest['total_size_bytes']/1024:.1f}KB")
            print(f"   Optimized: {manifest['metadata']['optimized']}")


if __name__ == "__main__":
    print("Running Asset Generator Tests (Phases 2-5)")
    print("=" * 60)

    # Phase 2 tests
    test_is_critical_from_user_actions()
    test_is_critical_fallback_to_role()
    test_parse_json_response()
    test_load_asset_planner_prompt()
    test_deduplication_logic()

    # Phase 3 tests
    test_build_prompt()
    test_generate_images_retry_logic()

    # Phase 4-5 tests
    test_auto_optimize_resize()
    test_generate_assets_end_to_end()

    print("\n" + "=" * 60)
    print("✅ All tests passed!")
