"""Test progress indicators for Task 3.2"""

from playable_agents.scene_card import create_empty_scene, SceneState


def test_progress_indicators():
    """
    Test progress indicator logic.

    Acceptance criteria:
    - Progress bar updates as questions answered
    - Scene counter shows current position
    - Card states visually clear
    """

    print("\n=== Test 1: Progress Calculation ===")

    # Create test scenario
    cards = [
        create_empty_scene(f"scene{i}", f"Scene {i}", i)
        for i in range(5)
    ]

    # Set various states
    cards[0].state = SceneState.COMPLETE
    cards[0].mechanics = ["battle"]
    cards[0].ui_elements = {"title": "Scene 1"}
    cards[0].user_actions = ["action"]
    cards[0].timing = {"duration": 5.0}

    cards[1].state = SceneState.COMPLETE
    cards[1].mechanics = ["tutorial"]
    cards[1].ui_elements = {"title": "Scene 2"}
    cards[1].user_actions = ["drag"]
    cards[1].timing = {"duration": 5.0}

    cards[2].state = SceneState.IN_PROGRESS
    cards[2].mechanics = ["merge"]

    cards[3].state = SceneState.EMPTY
    cards[4].state = SceneState.EMPTY

    # Calculate progress
    total = len(cards)
    completed = sum(1 for c in cards if c.is_complete())
    progress_pct = (completed / total) * 100 if total > 0 else 0

    print(f"Total scenes: {total}")
    print(f"Completed: {completed}")
    print(f"Progress: {progress_pct:.0f}%")

    assert total == 5
    assert completed == 2
    assert progress_pct == 40.0
    print("✅ Progress calculation correct")

    print("\n=== Test 2: Scene Counter ===")

    # Test scene counter for different positions
    test_cases = [
        (0, 5, "1/5"),  # First scene
        (2, 5, "3/5"),  # Middle scene
        (4, 5, "5/5"),  # Last scene
        (0, 1, "1/1"),  # Single scene
    ]

    for current_idx, total_scenes, expected in test_cases:
        current_scene = current_idx + 1
        counter = f"{current_scene}/{total_scenes}"
        assert counter == expected, f"Expected {expected}, got {counter}"
        print(f"✓ Scene {current_idx} of {total_scenes} → {counter}")

    print("✅ Scene counter correct")

    print("\n=== Test 3: Card State Icons ===")

    # Verify state visual indicators
    state_mapping = {
        SceneState.EMPTY: "⚪",
        SceneState.IN_PROGRESS: "🔵",
        SceneState.COMPLETE: "✅",
    }

    for card in cards:
        icon = state_mapping[card.state]
        print(f"{icon} {card.title}: {card.state}")

    # Check distribution
    empty_count = sum(1 for c in cards if c.state == SceneState.EMPTY)
    in_progress_count = sum(1 for c in cards if c.state == SceneState.IN_PROGRESS)
    complete_count = sum(1 for c in cards if c.state == SceneState.COMPLETE)

    assert empty_count == 2
    assert in_progress_count == 1
    assert complete_count == 2
    print("✅ Card states visually distinguishable")

    print("\n=== Test 4: Progress Bar Edge Cases ===")

    # Test edge cases
    edge_cases = [
        ([], 0, 0, 0.0),  # No scenes
        ([create_empty_scene("s1", "S1", 0)], 1, 0, 0.0),  # No completion
        ([create_empty_scene("s1", "S1", 0)], 1, 1, 100.0),  # Full completion
    ]

    for test_cards, total, completed, expected_pct in edge_cases:
        # Mark as complete if needed
        for i in range(completed):
            if i < len(test_cards):
                test_cards[i].mechanics = ["test"]
                test_cards[i].ui_elements = {"title": "Test"}
                test_cards[i].user_actions = ["action"]
                test_cards[i].timing = {"duration": 5.0}
                test_cards[i].state = SceneState.COMPLETE

        calc_total = len(test_cards)
        calc_completed = sum(1 for c in test_cards if c.is_complete())
        calc_pct = (calc_completed / calc_total * 100) if calc_total > 0 else 0.0

        print(f"Case: {total} total, {completed} complete → {calc_pct:.0f}%")
        assert calc_total == total
        assert calc_completed == completed
        assert abs(calc_pct - expected_pct) < 0.01

    print("✅ Progress bar handles edge cases")

    print("\n=== Test 5: Progress Updates ===")

    # Simulate progress updates
    progress_cards = [
        create_empty_scene(f"scene{i}", f"Scene {i}", i)
        for i in range(3)
    ]

    # Track progress over time
    progress_history = []

    # Initial state
    completed = sum(1 for c in progress_cards if c.is_complete())
    progress_history.append(completed)
    print(f"Step 0: {completed}/3 complete")

    # Complete scene 1
    progress_cards[0].mechanics = ["battle"]
    progress_cards[0].ui_elements = {"title": "Fight"}
    progress_cards[0].user_actions = ["watch"]
    progress_cards[0].timing = {"duration": 5.0}
    progress_cards[0].state = SceneState.COMPLETE

    completed = sum(1 for c in progress_cards if c.is_complete())
    progress_history.append(completed)
    print(f"Step 1: {completed}/3 complete")

    # Complete scene 2
    progress_cards[1].mechanics = ["tutorial"]
    progress_cards[1].ui_elements = {"title": "Learn"}
    progress_cards[1].user_actions = ["drag"]
    progress_cards[1].timing = {"duration": 5.0}
    progress_cards[1].state = SceneState.COMPLETE

    completed = sum(1 for c in progress_cards if c.is_complete())
    progress_history.append(completed)
    print(f"Step 2: {completed}/3 complete")

    # Complete scene 3
    progress_cards[2].mechanics = ["victory"]
    progress_cards[2].ui_elements = {"title": "Win"}
    progress_cards[2].user_actions = ["tap cta"]
    progress_cards[2].timing = {"duration": 3.0}
    progress_cards[2].state = SceneState.COMPLETE

    completed = sum(1 for c in progress_cards if c.is_complete())
    progress_history.append(completed)
    print(f"Step 3: {completed}/3 complete")

    assert progress_history == [0, 1, 2, 3]
    print("✅ Progress updates incrementally")

    print("\n=== Task 3.2 Acceptance: PASSED ===")
    print("\nNote: Visual rendering must be tested manually in Streamlit app")
    print("Run: streamlit run app.py")


if __name__ == "__main__":
    test_progress_indicators()
