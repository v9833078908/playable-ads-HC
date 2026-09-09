"""Test scene detection logic for Task 1.3"""

from models import DraftBrief, AssetMapping, SceneDescription
from playable_agents.scenario_builder import ScenarioBuilder


def test_scene_detection_pirate_ships():
    """
    Test scene detection with pirate-ships-like data.

    Acceptance criteria:
    - Correctly identifies scenes from PDF
    - Distinguishes between clear vs. inferred scenes
    - Creates SceneCards with titles and basic metadata
    """

    # Create mock DraftBrief similar to pirate-ships
    brief = DraftBrief(
        title="Pirate Ships - Build and Fight",
        networks=["applovin", "unity"],
        languages=["EN"],
        scenes=[
            SceneDescription(
                id="hook",
                description="Hook: enemy ship attacks empty player ship",
                type="battle",
            ),
            SceneDescription(
                id="repair_tutorial",
                description="Scene 1: Repair ship - drag repairer to grid slot",
                ui_text="REPAIR YOUR SHIP",
                type="tutorial",
            ),
            SceneDescription(
                id="battle_1",
                description="Battle with repair - repairer fixes ship during combat",
                type="battle",
            ),
            SceneDescription(
                id="weapons_tutorial",
                description="Scene 2: Setup weapons - drag cannons to slots",
                ui_text="SETUP WEAPONS",
                type="tutorial",
            ),
            SceneDescription(
                id="merge_tutorial",
                description="Merge two cannons into skeleton cannon",
                type="tutorial",
            ),
            SceneDescription(
                id="victory",
                description="Victory screen with rewards and CTA button",
                ui_text="VICTORY!",
                type="victory",
            ),
            # Test unclear scene
            SceneDescription(
                id="unknown_scene",
                description="Some scene",
                type=None,
            ),
        ],
    )

    # Create mock AssetMapping
    assets = AssetMapping(
        components=[],
        background=None,
        style="cartoon",
    )

    # Initialize ScenarioBuilder
    builder = ScenarioBuilder(brief, assets)

    # Run scene detection
    result = builder.detect_scenes()

    print("\n=== Scene Detection Results ===")
    print(f"Detected (clear): {len(result.detected)}")
    for scene in result.detected:
        print(f"  - {scene.id}: {scene.title} [{scene.confidence}]")
        print(f"    Mechanics: {scene.detected_mechanics}")

    print(f"\nInferred: {len(result.inferred)}")
    for scene in result.inferred:
        print(f"  - {scene.id}: {scene.title} [{scene.confidence}]")
        print(f"    Mechanics: {scene.detected_mechanics}")

    print(f"\nMissing info: {len(result.missing_info)}")
    for info in result.missing_info:
        print(f"  - {info}")

    # Verify scene cards created
    print(f"\n=== Scene Cards ===")
    scene_cards = builder.get_scene_cards()
    print(f"Total cards created: {len(scene_cards)}")
    for card in scene_cards:
        print(f"  {card}")
        print(f"    ID: {card.id}")
        print(f"    Mechanics: {card.mechanics}")
        print(f"    PDF Source: {card.pdf_source[:50] if card.pdf_source else None}...")

    # Acceptance checks
    print("\n=== Acceptance Criteria ===")

    # 1. Correctly identifies scenes
    assert len(result.detected) + len(result.inferred) >= 6, \
        f"Should detect at least 6 scenes, got {len(result.detected) + len(result.inferred)}"
    print("✅ Correctly identifies scenes")

    # 2. Distinguishes clear vs inferred
    assert len(result.detected) > 0, "Should have some clear scenes"
    assert result.detected[0].confidence == "clear", "Clear scenes should have 'clear' confidence"
    print("✅ Distinguishes between clear vs. inferred scenes")

    # 3. Creates SceneCards with titles and metadata
    assert len(scene_cards) == len(result.detected) + len(result.inferred), \
        "Should create card for each detected+inferred scene"

    # Check cards have required fields
    for idx, card in enumerate(scene_cards):
        assert card.id, f"Card {idx} should have id"
        assert card.title, f"Card {idx} should have title"
        assert card.pdf_source, f"Card {idx} should have PDF source"
        assert card.order == idx, f"Card {idx} should have order={idx}"
    print("✅ Creates SceneCards with titles and basic metadata")

    # Check mechanics detection
    repair_card = builder.get_scene_by_id("repair_tutorial")
    assert repair_card is not None, "Should find repair_tutorial card"
    assert "drag-drop" in repair_card.mechanics or "tutorial" in repair_card.mechanics, \
        f"Repair tutorial should detect drag-drop or tutorial mechanics, got {repair_card.mechanics}"
    print("✅ Detects mechanics from descriptions")

    print("\n=== Task 1.3 Acceptance: PASSED ===")


if __name__ == "__main__":
    test_scene_detection_pirate_ships()
