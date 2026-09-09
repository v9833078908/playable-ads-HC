"""Test answer processing for Task 2.2"""

from models import DraftBrief, AssetMapping
from playable_agents.scenario_builder import ScenarioBuilder, Question
from playable_agents.scene_card import create_empty_scene, SceneState


def test_answer_processing():
    """
    Test answer processing logic.

    Acceptance criteria:
    - Correctly updates card fields
    - Handles various answer formats (text, numbers, selections)
    - Tracks which fields use defaults
    - Doesn't crash on unexpected input
    """

    builder = ScenarioBuilder(
        DraftBrief(title="Test"),
        AssetMapping(components=[], style="cartoon"),
    )

    print("\n=== Test 1: Process UI Text Answer ===")

    card = create_empty_scene("scene1", "Scene 1", 0)
    question = Question(
        text="What text should appear on screen?",
        reasoning="Test",
        category="ui",
    )

    builder.process_answer(question, "REPAIR YOUR SHIP", card)

    print(f"UI elements: {card.ui_elements}")
    print(f"State: {card.state}")

    assert "title" in card.ui_elements or "text" in card.ui_elements, \
        "Should update UI elements"
    assert card.state == SceneState.IN_PROGRESS, \
        "Should transition to in_progress"
    print("✅ Processes UI text answers")

    print("\n=== Test 2: Process Timing Answer (Number) ===")

    card2 = create_empty_scene("scene2", "Scene 2", 1)
    question = Question(
        text="How long should the battle last?",
        reasoning="Test",
        category="timing",
    )

    builder.process_answer(question, "5 seconds", card2)

    print(f"Timing: {card2.timing}")

    assert "duration" in card2.timing, "Should extract duration"
    assert card2.timing["duration"] == 5.0, f"Should parse number, got {card2.timing['duration']}"
    print("✅ Extracts numbers from text")

    print("\n=== Test 3: Process Timing Answer (Qualitative) ===")

    card3 = create_empty_scene("scene3", "Scene 3", 2)
    builder.process_answer(question, "fast", card3)

    print(f"Timing: {card3.timing}")
    print(f"Using defaults: {card3.defaults_used}")

    assert "duration" in card3.timing, "Should set duration"
    assert card3.timing["duration"] <= 3.0, "Fast should be short duration"
    assert card3.is_using_default("timing.duration"), "Should track as default"
    print("✅ Handles qualitative answers with defaults")

    print("\n=== Test 4: Process Mechanics Answer ===")

    card4 = create_empty_scene("scene4", "Scene 4", 3)
    card4.mechanics = ["battle"]
    question = Question(
        text="What happens during the battle?",
        reasoning="Test",
        category="mechanics",
    )

    builder.process_answer(
        question,
        "Player and enemy exchange damage until one reaches zero HP",
        card4
    )

    print(f"Technical: {card4.technical}")

    assert "battle_logic" in card4.technical, "Should store battle logic"
    assert "hp" in card4.technical.get("battle_logic", "").lower(), \
        "Should capture HP mention"
    print("✅ Processes mechanics answers")

    print("\n=== Test 5: Handle Skip/Default ===")

    card5 = create_empty_scene("scene5", "Scene 5", 4)
    question = Question(
        text="What should the CTA button text be?",
        reasoning="Test",
        category="ui",
        default_value="TAKE REWARD",
    )

    builder.process_answer(question, "skip", card5)

    print(f"UI elements: {card5.ui_elements}")
    print(f"Defaults used: {card5.defaults_used}")

    assert "cta_text" in card5.ui_elements, "Should apply default"
    assert card5.ui_elements["cta_text"] == "TAKE REWARD", \
        "Should use default value"
    assert card5.is_using_default("ui_elements.cta_text"), \
        "Should track default usage"
    print("✅ Applies defaults when skipped")

    print("\n=== Test 6: Handle Empty Answer ===")

    card6 = create_empty_scene("scene6", "Scene 6", 5)
    question_no_default = Question(
        text="What happens?",
        reasoning="Test",
        category="mechanics",
    )

    # Empty answer, no default - should not crash
    builder.process_answer(question_no_default, "", card6)
    print("✅ Handles empty answer without default")

    print("\n=== Test 7: Handle Various Answer Formats ===")

    test_cases = [
        ("3", "timing", "duration"),  # Plain number
        ("5 sec", "timing", "duration"),  # Number with unit
        ("medium (5s)", "timing", "duration"),  # Selection with number
        ("auto-advance", "timing", "auto_advance"),  # Keyword
        ("VICTORY!", "ui", "title"),  # Caps text
        ("Drag cannon onto grid", "mechanics", "user_actions"),  # Sentence
    ]

    for answer, category, expected_field in test_cases:
        card = create_empty_scene("test", "Test", 0)
        question = Question(
            text=f"Test question about {expected_field}?",
            reasoning="Test",
            category=category,
        )

        try:
            builder.process_answer(question, answer, card)
            print(f"✓ Handled: '{answer}' ({category})")
        except Exception as e:
            assert False, f"Failed to process '{answer}': {e}"

    print("✅ Handles various answer formats")

    print("\n=== Test 8: Technical/VFX Answer ===")

    card7 = create_empty_scene("scene7", "Scene 7", 6)
    question = Question(
        text="What visual effects should appear?",
        reasoning="Test",
        category="technical",
    )

    builder.process_answer(
        question,
        "Damage numbers, fire effects, screen shake",
        card7
    )

    print(f"Technical: {card7.technical}")

    assert "vfx" in card7.technical, "Should store VFX description"
    if "vfx_list" in card7.technical:
        print(f"Parsed effects: {card7.technical['vfx_list']}")
        assert len(card7.technical["vfx_list"]) >= 2, "Should parse multiple effects"
    print("✅ Processes technical answers")

    print("\n=== Test 9: Multiple Answers Build Up Card ===")

    card8 = create_empty_scene("scene8", "Full Scene", 7)
    card8.mechanics = ["battle"]

    questions_and_answers = [
        (Question(text="Main action?", reasoning="Test", category="mechanics"),
         "Auto battle with damage"),
        (Question(text="What text?", reasoning="Test", category="ui"),
         "FIGHT!"),
        (Question(text="How long?", reasoning="Test", category="timing"),
         "5"),
        (Question(text="What effects?", reasoning="Test", category="technical"),
         "Fire and explosions"),
    ]

    for q, a in questions_and_answers:
        builder.process_answer(q, a, card8)

    print(f"\nFinal card state:")
    print(f"  UI elements: {len(card8.ui_elements)}")
    print(f"  Timing: {card8.timing}")
    print(f"  Technical: {len(card8.technical)}")
    print(f"  State: {card8.state}")

    assert len(card8.ui_elements) > 0, "Should have UI elements"
    assert "duration" in card8.timing, "Should have timing"
    assert len(card8.technical) > 0, "Should have technical details"
    assert card8.state == SceneState.IN_PROGRESS, "Should be in progress"
    print("✅ Multiple answers progressively build card")

    print("\n=== Task 2.2 Acceptance: PASSED ===")


if __name__ == "__main__":
    test_answer_processing()
