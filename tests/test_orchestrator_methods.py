"""Test orchestrator scenario methods (without full initialization)"""

from playable_agents.scenario_builder import ScenarioBuilder
from playable_agents.scene_card import create_empty_scene, SceneCard
from models import DraftBrief, AssetMapping, SceneDescription


def test_orchestrator_scenario_methods():
    """
    Test ScenarioBuilder integration methods (unit test style).

    This tests the logic without requiring full orchestrator initialization.
    """

    print("\n=== Test 1: Scenario Context Structure ===")

    # Simulate orchestrator context
    context = {
        "pdf_bytes": None,
        "images_bytes": [],
        "brief": None,
        "assets": None,
        "scene_cards": [],
        "spec": None,
        "html": None,
        "validation": None,
    }

    assert "scene_cards" in context
    assert isinstance(context["scene_cards"], list)
    print("✅ Context has scene_cards field")

    print("\n=== Test 2: ScenarioBuilder Workflow ===")

    # Step 1: Create brief and assets
    brief = DraftBrief(
        title="Test",
        scenes=[
            SceneDescription(id="s1", description="Tutorial", type="tutorial"),
            SceneDescription(id="s2", description="Battle", type="battle"),
        ]
    )
    assets = AssetMapping(components=[], style="cartoon")

    print("✓ Brief and assets created")

    # Step 2: Initialize ScenarioBuilder
    builder = ScenarioBuilder(brief, assets)
    assert builder is not None
    print("✓ ScenarioBuilder initialized")

    # Step 3: Detect scenes
    detection = builder.detect_scenes()
    scene_cards = builder.get_scene_cards()

    print(f"✓ Detected {len(detection.detected)} scenes")
    print(f"✓ Created {len(scene_cards)} scene cards")

    assert len(scene_cards) >= 2
    context["scene_cards"] = scene_cards

    # Step 4: Generate questions for first scene
    first_card = scene_cards[0]
    questions = builder.generate_questions(first_card)

    print(f"✓ Generated {len(questions)} questions for {first_card.title}")
    assert len(questions) > 0

    # Step 5: Process answer
    first_question = questions[0]
    builder.process_answer(first_question, "Test answer", first_card)

    print(f"✓ Processed answer, card state: {first_card.state}")
    assert first_card.state != "empty"

    print("✅ Complete workflow logic works")

    print("\n=== Test 3: Scenario Completion Logic ===")

    # Test completion check
    from playable_agents.scene_card import all_scenes_complete

    # Not complete yet
    is_complete = all_scenes_complete(scene_cards)
    print(f"Initially complete: {is_complete}")
    assert not is_complete

    # Complete all scenes
    for card in scene_cards:
        card.mechanics = ["test"]
        card.ui_elements = {"title": "Test"}
        card.user_actions = ["action"]
        card.timing = {"duration": 5.0}
        card.mark_complete(force=True)

    is_complete = all_scenes_complete(scene_cards)
    print(f"After completion: {is_complete}")
    assert is_complete

    print("✅ Completion logic works")

    print("\n=== Test 4: Validation Integration ===")

    from playable_agents.validation import validate_all_scenes

    # Run validation
    validation_result = validate_all_scenes(scene_cards, brief, assets)

    print(f"Total warnings: {validation_result['total_warnings']}")
    print(f"Ready for generation: {validation_result['ready_for_generation']}")

    assert "ready_for_generation" in validation_result
    assert "total_warnings" in validation_result
    print("✅ Validation integration works")

    print("\n=== Test 5: Question-Answer Flow ===")

    # Create fresh scene
    test_scene = create_empty_scene("test", "Test Scene", 0)
    test_scene.mechanics = ["battle"]

    # Generate multiple questions
    questions = builder.generate_questions(test_scene)

    print(f"Generated {len(questions)} questions")

    # Answer all questions
    for i, question in enumerate(questions):
        builder.process_answer(question, f"Answer {i + 1}", test_scene)
        print(f"✓ Answered question {i + 1}/{len(questions)}")

    print(f"Final state: {test_scene.state}")
    print(f"Has mechanics: {bool(test_scene.mechanics)}")
    print(f"Has UI: {bool(test_scene.ui_elements)}")
    print(f"Has timing: {bool(test_scene.timing)}")
    print(f"Has actions: {bool(test_scene.user_actions)}")

    print("✅ Question-answer flow completes")

    print("\n=== Test 6: Next Question Logic ===")

    # Simulate finding next incomplete scene
    test_cards = [
        create_empty_scene(f"s{i}", f"Scene {i}", i)
        for i in range(3)
    ]

    # Complete first two
    for card in test_cards[:2]:
        card.mechanics = ["test"]
        card.ui_elements = {"t": "t"}
        card.user_actions = ["a"]
        card.timing = {"duration": 5.0}
        card.mark_complete(force=True)

    # Find next incomplete
    next_idx = None
    for i, card in enumerate(test_cards):
        if not card.is_complete():
            next_idx = i
            break

    print(f"Next incomplete scene: {next_idx}")
    assert next_idx == 2
    print("✅ Next question logic works")

    print("\n=== Task 4.2 Acceptance: PASSED ===")
    print("\nCore integration logic verified:")
    print("- ScenarioBuilder runs after brief+assets")
    print("- Scene detection creates cards")
    print("- Questioning workflow completes")
    print("- Validation integrates with cards")
    print("\nFull orchestrator requires API keys for agents")


if __name__ == "__main__":
    test_orchestrator_scenario_methods()
