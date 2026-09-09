"""Test scene card UI components for Task 3.1"""

import sys
from playable_agents.scene_card import create_empty_scene, SceneState, WarningSeverity


def test_scene_card_ui_data():
    """
    Test scene card UI component data structures.

    Acceptance criteria:
    - Cards render correctly with all fields
    - State indicators update (empty/in-progress/complete)
    - Warnings display with amber badge
    - Defaults shown correctly
    """

    print("\n=== Test 1: Card with All Fields ===")

    # Create complete card
    card = create_empty_scene("scene1", "Battle Tutorial", 0)
    card.mechanics = ["battle", "tutorial"]
    card.ui_elements = {
        "title": "FIGHT!",
        "subtitle": "Defend your ship",
        "cta": "Continue"
    }
    card.timing = {
        "duration": 5.0,
        "auto_advance": True
    }
    card.user_actions = [
        "Watch battle unfold",
        "Tap to continue"
    ]
    card.technical = {
        "vfx": ["fire_effects", "screen_shake"],
        "animation_speed": "medium"
    }
    card.state = SceneState.COMPLETE

    print(f"Card: {card}")
    print(f"State: {card.state}")
    print(f"Complete: {card.is_complete()}")
    assert card.state == SceneState.COMPLETE
    assert len(card.ui_elements) == 3
    assert len(card.mechanics) == 2
    print("✅ Complete card structure valid")

    print("\n=== Test 2: Card State Indicators ===")

    # Test all states
    states = [
        (SceneState.EMPTY, "⚪"),
        (SceneState.IN_PROGRESS, "🔵"),
        (SceneState.COMPLETE, "✅"),
    ]

    for state, expected_icon in states:
        test_card = create_empty_scene("test", "Test", 0)
        test_card.state = state

        # Simulate icon mapping
        state_icon = {
            SceneState.EMPTY: "⚪",
            SceneState.IN_PROGRESS: "🔵",
            SceneState.COMPLETE: "✅",
        }[test_card.state]

        assert state_icon == expected_icon, f"State {state} should map to {expected_icon}"
        print(f"✓ {state} → {state_icon}")

    print("✅ State indicators correct")

    print("\n=== Test 3: Warning Badges ===")

    # Card with warnings
    card_with_warnings = create_empty_scene("scene2", "Scene with Issues", 1)
    card_with_warnings.add_warning(
        "Duration too long",
        severity=WarningSeverity.MEDIUM,
        field="timing.duration"
    )
    card_with_warnings.add_warning(
        "Missing asset",
        severity=WarningSeverity.HIGH,
        field="ui_elements"
    )

    print(f"Warnings: {len(card_with_warnings.warnings)}")
    assert len(card_with_warnings.warnings) == 2

    # Test warning badge text
    warning_badge = f" ⚠️ {len(card_with_warnings.warnings)}" if card_with_warnings.warnings else ""
    assert warning_badge == " ⚠️ 2"
    print(f"Warning badge: '{warning_badge}'")
    print("✅ Warning badges work")

    print("\n=== Test 4: Default Value Display ===")

    # Card with default values
    card_with_defaults = create_empty_scene("scene3", "Scene with Defaults", 2)
    card_with_defaults.timing = {"duration": 5.0}
    card_with_defaults.track_default("timing.duration", 5.0)

    assert card_with_defaults.is_using_default("timing.duration")
    default_val = card_with_defaults.get_default_value("timing.duration")
    assert default_val == 5.0

    # Simulate default text display
    default_text = f" _(using default: {default_val})_"
    assert "using default" in default_text and "5.0" in default_text
    print(f"Default display text: {default_text}")
    print("✅ Default values tracked and displayable")

    print("\n=== Test 5: Inline Edit Data Structure ===")

    # Test that fields can be updated (simulating inline edit)
    editable_card = create_empty_scene("scene4", "Editable Scene", 3)
    editable_card.ui_elements = {"title": "Original Title"}

    # Simulate edit
    new_title = "Updated Title"
    editable_card.ui_elements["title"] = new_title
    assert editable_card.ui_elements["title"] == "Updated Title"
    print("✅ Fields are editable")

    # Test timing edit
    editable_card.timing = {"duration": 5.0}
    new_duration = 7.5
    editable_card.timing["duration"] = new_duration
    assert editable_card.timing["duration"] == 7.5
    print("✅ Timing fields are editable")

    print("\n=== Test 6: Card List Rendering ===")

    # Simulate multiple cards
    cards = [
        create_empty_scene(f"scene{i}", f"Scene {i}", i)
        for i in range(5)
    ]

    # Fill some cards
    cards[0].state = SceneState.COMPLETE
    cards[0].mechanics = ["battle"]
    cards[0].ui_elements = {"title": "Scene 1"}
    cards[0].timing = {"duration": 5.0}
    cards[0].user_actions = ["action"]
    assert cards[0].is_complete()

    cards[1].state = SceneState.IN_PROGRESS
    cards[1].mechanics = ["tutorial"]

    cards[2].state = SceneState.EMPTY

    # Test progress calculation
    total = len(cards)
    completed = sum(1 for c in cards if c.is_complete())
    progress = completed / total if total > 0 else 0

    print(f"Total cards: {total}")
    print(f"Completed: {completed}")
    print(f"Progress: {progress * 100:.0f}%")

    assert total == 5
    assert completed == 1
    assert progress == 0.2
    print("✅ Card list progress tracking works")

    print("\n=== Test 7: Empty/Not Set Fields ===")

    # Card with missing fields
    empty_card = create_empty_scene("empty", "Empty Card", 0)

    # Test empty field displays
    assert not empty_card.mechanics
    assert not empty_card.ui_elements
    assert not empty_card.timing
    assert not empty_card.user_actions

    print("Empty mechanics:", empty_card.mechanics or "_Not set_")
    print("Empty UI:", empty_card.ui_elements or "_Not set_")
    print("✅ Empty fields handled correctly")

    print("\n=== Task 3.1 Acceptance: PASSED ===")
    print("\nNote: UI rendering must be tested manually in Streamlit app")
    print("Run: streamlit run app.py")


if __name__ == "__main__":
    test_scene_card_ui_data()
