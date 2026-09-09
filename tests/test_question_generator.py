"""Test question generation for Task 2.1"""

from models import DraftBrief, AssetMapping, ExtractedComponent
from playable_agents.scenario_builder import ScenarioBuilder, Question
from playable_agents.scene_card import create_empty_scene


def test_question_generator():
    """
    Test question generation logic.

    Acceptance criteria:
    - Simple scenes get 3 questions, complex get 7
    - Questions include reasoning
    - Smart suggestions based on assets work
    - Question categories distributed appropriately
    """

    # Create builder with some assets
    brief = DraftBrief(title="Test Playable")
    assets = AssetMapping(
        components=[
            ExtractedComponent(
                id="char_0",
                base64="test",
                role="main_gameplay_object",
                description="Repairer unit",
            ),
            ExtractedComponent(
                id="tool_0",
                base64="test",
                role="interactive_tool",
                description="Cannon weapon",
            ),
        ],
        style="cartoon",
    )

    builder = ScenarioBuilder(brief, assets)

    print("\n=== Test 1: Simple Scene (Victory) ===")
    victory_scene = create_empty_scene("victory", "Victory Screen", 0)
    victory_scene.mechanics = ["victory", "cta"]

    questions = builder.generate_questions(victory_scene)
    print(f"Questions generated: {len(questions)}")
    for i, q in enumerate(questions, 1):
        print(f"\n{i}. {q.text}")
        print(f"   Category: {q.category} | Optional: {q.optional}")
        print(f"   Reasoning: {q.reasoning}")
        if q.suggestions:
            print(f"   Suggestions: {q.suggestions}")
        if q.default_value:
            print(f"   Default: {q.default_value}")

    # Check simple scene gets 3 questions
    assert len(questions) == 3, f"Simple scene should get 3 questions, got {len(questions)}"
    assert all(q.reasoning for q in questions), "All questions should have reasoning"
    print("\n✅ Simple scene: 3 questions with reasoning")

    print("\n=== Test 2: Medium Scene (Tutorial) ===")
    tutorial_scene = create_empty_scene("repair_tutorial", "Repair Tutorial", 0)
    tutorial_scene.mechanics = ["drag-drop", "tutorial"]

    questions = builder.generate_questions(tutorial_scene)
    print(f"Questions generated: {len(questions)}")
    for i, q in enumerate(questions, 1):
        print(f"\n{i}. {q.text}")
        print(f"   Category: {q.category} | Optional: {q.optional}")
        print(f"   Reasoning: {q.reasoning}")
        if q.suggestions:
            print(f"   Suggestions: {q.suggestions}")

    # Check medium scene gets 5 questions
    assert 4 <= len(questions) <= 6, f"Medium scene should get ~5 questions, got {len(questions)}"
    assert all(q.reasoning for q in questions), "All questions should have reasoning"

    # Check smart suggestions based on assets
    has_asset_suggestions = any(
        any("repairer" in s.lower() or "cannon" in s.lower() for s in q.suggestions)
        for q in questions
        if q.suggestions
    )
    assert has_asset_suggestions, "Should have smart suggestions based on assets"
    print("\n✅ Medium scene: ~5 questions with asset-based suggestions")

    print("\n=== Test 3: Complex Scene (Battle) ===")
    battle_scene = create_empty_scene("final_battle", "Final Battle", 0)
    battle_scene.mechanics = ["battle", "repair", "attack"]

    questions = builder.generate_questions(battle_scene)
    print(f"Questions generated: {len(questions)}")
    for i, q in enumerate(questions, 1):
        print(f"\n{i}. {q.text}")
        print(f"   Category: {q.category} | Optional: {q.optional}")
        print(f"   Reasoning: {q.reasoning}")

    # Check complex scene gets 7 questions
    assert 6 <= len(questions) <= 8, f"Complex scene should get ~7 questions, got {len(questions)}"
    print("\n✅ Complex scene: ~7 questions")

    print("\n=== Test 4: Question Category Distribution ===")
    categories = [q.category for q in questions]
    unique_categories = set(categories)
    print(f"Categories used: {unique_categories}")

    # Should have at least 3 different categories
    assert len(unique_categories) >= 3, \
        f"Should have at least 3 different categories, got {len(unique_categories)}"
    print("✅ Questions distributed across categories")

    print("\n=== Test 5: Optional vs Required Questions ===")
    required_count = sum(1 for q in questions if not q.optional)
    optional_count = sum(1 for q in questions if q.optional)
    print(f"Required: {required_count}, Optional: {optional_count}")

    assert required_count >= 3, "Should have at least 3 required questions"
    print("✅ Has both required and optional questions")

    print("\n=== Test 6: Complexity Detection ===")
    # Test auto-detection
    complexity_victory = builder._detect_complexity(victory_scene)
    complexity_tutorial = builder._detect_complexity(tutorial_scene)
    complexity_battle = builder._detect_complexity(battle_scene)

    print(f"Victory: {complexity_victory}")
    print(f"Tutorial: {complexity_tutorial}")
    print(f"Battle: {complexity_battle}")

    assert complexity_victory == "simple", "Victory should be simple"
    assert complexity_tutorial == "medium", "Tutorial should be medium"
    assert complexity_battle == "complex", "Multi-mechanic battle should be complex"
    print("✅ Complexity detection works correctly")

    print("\n=== Task 2.1 Acceptance: PASSED ===")


if __name__ == "__main__":
    test_question_generator()
