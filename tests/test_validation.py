"""Test validation logic for Task 1.2"""

from models import DraftBrief, AssetMapping, SceneDescription
from playable_agents.scene_card import create_empty_scene, WarningSeverity
from playable_agents.validation import (
    check_pdf_deviation,
    check_asset_availability,
    check_logic_conflicts,
    get_completeness_status,
    validate_all_scenes,
)


def test_validation_logic():
    """
    Test validation logic.

    Acceptance criteria:
    - Returns warnings without blocking
    - Detects common issues (missing assets, duration mismatches, logic conflicts)
    - Works with partial data (doesn't crash on incomplete cards)
    """

    print("\n=== Test 1: PDF Deviation Detection ===")

    # Create PDF data
    pdf_data = DraftBrief(
        title="Test Playable",
        scenes=[
            SceneDescription(
                id="battle_1",
                description="Battle scene lasting 5 seconds",
                type="battle",
            )
        ],
    )

    # Create card with deviated duration
    card = create_empty_scene("battle_1", "Battle", 0)
    card.mechanics = ["battle"]
    card.timing = {"duration": 15.0}  # Too long for battle

    warnings = check_pdf_deviation(card, pdf_data)
    print(f"Warnings: {len(warnings)}")
    for w in warnings:
        print(f"  {w}")

    assert len(warnings) > 0, "Should detect duration deviation"
    assert any("duration" in w.message.lower() for w in warnings), \
        "Should warn about duration"
    print("✅ Detects PDF deviations")

    print("\n=== Test 2: Asset Availability Check ===")

    # Empty assets
    empty_assets = AssetMapping(components=[], style="cartoon")

    # Card with drag-drop but no assets
    drag_card = create_empty_scene("tutorial", "Drag Tutorial", 0)
    drag_card.mechanics = ["drag-drop"]

    warnings = check_asset_availability(drag_card, empty_assets)
    print(f"Warnings: {len(warnings)}")
    for w in warnings:
        print(f"  {w}")

    assert len(warnings) > 0, "Should detect missing draggable assets"
    assert any(w.severity == WarningSeverity.HIGH for w in warnings), \
        "Missing critical assets should be HIGH severity"
    print("✅ Detects missing assets")

    print("\n=== Test 3: Logic Conflicts ===")

    # Scenarios with logic issues
    cards = [
        # No victory scene
        create_empty_scene("scene1", "Battle", 0),
        create_empty_scene("scene2", "Tutorial", 1),
    ]
    cards[0].mechanics = ["battle"]
    cards[1].mechanics = ["tutorial"]
    # Both missing duration
    cards[0].timing = {}
    cards[1].timing = {}

    warnings = check_logic_conflicts(cards)
    print(f"Warnings: {len(warnings)}")
    for w in warnings:
        print(f"  {w}")

    # Should detect: no victory, missing durations
    assert len(warnings) >= 2, f"Should detect multiple issues, got {len(warnings)}"
    victory_warning = any("victory" in w.message.lower() for w in warnings)
    duration_warning = any("duration" in w.message.lower() for w in warnings)
    assert victory_warning, "Should detect missing victory scene"
    assert duration_warning, "Should detect missing duration"
    print("✅ Detects logic conflicts")

    print("\n=== Test 4: Completeness Status ===")

    # Incomplete card
    incomplete = create_empty_scene("scene1", "Scene", 0)
    status = get_completeness_status(incomplete)
    print(f"Complete: {status['complete']}")
    print(f"Missing: {status['missing_fields']}")

    assert not status["complete"], "Empty card should not be complete"
    assert len(status["missing_fields"]) >= 3, "Should have multiple missing fields"
    print("✅ Tracks completeness correctly")

    # Complete card
    complete = create_empty_scene("scene1", "Scene", 0)
    complete.mechanics = ["battle"]
    complete.ui_elements = {"title": "Fight!"}
    complete.user_actions = ["watch battle"]
    complete.timing = {"duration": 5.0}

    status = get_completeness_status(complete)
    print(f"\nComplete card - Complete: {status['complete']}")
    print(f"Missing: {status['missing_fields']}")

    assert status["complete"], "Filled card should be complete"
    assert len(status["missing_fields"]) == 0, "Should have no missing fields"
    print("✅ Recognizes complete cards")

    print("\n=== Test 5: Works with Partial Data ===")

    # Test that validation doesn't crash with partial/empty data
    empty_card = create_empty_scene("empty", "Empty", 0)
    empty_pdf = DraftBrief(title="Empty", scenes=[])
    empty_assets = AssetMapping(components=[], style="cartoon")

    try:
        check_pdf_deviation(empty_card, empty_pdf)
        check_asset_availability(empty_card, empty_assets)
        check_logic_conflicts([empty_card])
        get_completeness_status(empty_card)
        print("✅ No crashes with partial/empty data")
    except Exception as e:
        assert False, f"Should not crash on partial data: {e}"

    print("\n=== Test 6: Validate All Scenes ===")

    # Create scenario with multiple issues
    pdf = DraftBrief(
        title="Test",
        scenes=[
            SceneDescription(id="battle", description="Battle", type="battle"),
            SceneDescription(id="victory", description="Victory", type="victory"),
        ],
    )
    assets = AssetMapping(components=[], style="cartoon")

    cards = [
        create_empty_scene("battle", "Battle", 0),
        create_empty_scene("victory", "Victory", 1),
    ]
    cards[0].mechanics = ["battle", "drag-drop"]  # Will warn about missing assets
    cards[0].timing = {"duration": 20.0}  # Too long
    cards[1].mechanics = ["victory"]
    # Both incomplete (missing ui_elements, user_actions)

    result = validate_all_scenes(cards, pdf, assets)
    print(f"\nValidation result:")
    print(f"  Total warnings: {result['total_warnings']}")
    print(f"  Critical: {result['critical']}")
    print(f"  Warnings: {result['warnings']}")
    print(f"  Info: {result['info']}")
    print(f"  Incomplete scenes: {result['incomplete_scenes']}")
    print(f"  Ready for generation: {result['ready_for_generation']}")

    assert result["total_warnings"] > 0, "Should detect warnings"
    assert not result["ready_for_generation"], "Incomplete scenes should block generation"
    print("✅ Comprehensive validation works")

    # Now complete the cards
    for card in cards:
        card.ui_elements = {"title": "Text"}
        card.user_actions = ["action"]
        if "duration" not in card.timing:
            card.timing["duration"] = 5.0

    result = validate_all_scenes(cards, pdf, assets)
    print(f"\nAfter completing cards:")
    print(f"  Ready for generation: {result['ready_for_generation']}")
    assert result["ready_for_generation"], "Complete cards should be ready"
    print("✅ Validation unblocks when complete")

    print("\n=== Task 1.2 Acceptance: PASSED ===")


if __name__ == "__main__":
    test_validation_logic()
