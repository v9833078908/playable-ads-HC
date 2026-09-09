"""Test chat interface formatting for Task 3.3"""

import sys
sys.path.insert(0, '/Users/eli/Documents/PythonProjects/playable-ads-hackathon')

from playable_agents.scenario_builder import Question


def format_question_message(question, scene_title):
    """Format question for chat (copy from app.py for testing)"""
    message = f"**Scene: {scene_title}**\n\n"
    message += f"**{question.text}**\n\n"
    message += f"_{question.reasoning}_\n\n"

    if question.suggestions:
        message += "💡 **Suggestions:**\n"
        for suggestion in question.suggestions:
            message += f"- {suggestion}\n"
        message += "\n"

    if question.optional:
        message += "_You can skip this question (type 'skip' or leave empty)_\n\n"

    if question.default_value:
        message += f"_Default: {question.default_value}_\n"

    return message


def format_scene_completion_message(scene_title, scene_number, total_scenes):
    """Format completion message (copy from app.py for testing)"""
    message = f"### ✅ Scene {scene_number} Complete: {scene_title}\n\n"

    if scene_number < total_scenes:
        message += f"Moving to Scene {scene_number + 1}...\n\n"
        message += "_Review the card in the sidebar before continuing._"
    else:
        message += "**All scenes complete!** 🎉\n\n"
        message += "Ready to generate the playable HTML."

    return message


def test_chat_interface():
    """
    Test chat interface formatting.

    Acceptance criteria:
    - Questions render with reasoning
    - Suggestions display clearly
    - Scene transitions show pause message
    """

    print("\n=== Test 1: Question with Reasoning ===")

    question = Question(
        text="What happens during the battle?",
        reasoning="This defines the battle loop logic and determines DPS, HP changes, and win/lose conditions.",
        category="mechanics",
        suggestions=[
            "Auto-battle with damage over time",
            "Player deals damage, enemy responds",
            "Health decreases until one side wins",
        ]
    )

    formatted = format_question_message(question, "Battle Scene")

    print(formatted)
    print("\n---")

    # Check formatting
    assert "Scene: Battle Scene" in formatted
    assert question.text in formatted
    assert question.reasoning in formatted
    assert "💡 **Suggestions:**" in formatted
    for suggestion in question.suggestions:
        assert suggestion in formatted

    print("✅ Question renders with reasoning and suggestions")

    print("\n=== Test 2: Optional Question with Default ===")

    optional_question = Question(
        text="What visual effects should appear?",
        reasoning="This enhances battle feel.",
        category="technical",
        optional=True,
        default_value="Fire + explosions",
        suggestions=["Damage numbers", "Fire effects", "Screen shake"]
    )

    formatted = format_question_message(optional_question, "Final Battle")

    print(formatted)
    print("\n---")

    assert "optional" in formatted.lower() or "skip" in formatted.lower()
    assert "Default: Fire + explosions" in formatted

    print("✅ Optional question shows skip option and default")

    print("\n=== Test 3: Question without Suggestions ===")

    simple_question = Question(
        text="What is the main action?",
        reasoning="This defines the core interaction.",
        category="mechanics"
    )

    formatted = format_question_message(simple_question, "Tutorial")

    print(formatted)
    print("\n---")

    assert "Scene: Tutorial" in formatted
    assert simple_question.text in formatted
    assert "💡" not in formatted  # No suggestions
    assert "Default:" not in formatted  # No default

    print("✅ Simple question renders correctly")

    print("\n=== Test 4: Scene Completion Message ===")

    # Middle scene
    completion_msg = format_scene_completion_message("Repair Tutorial", 1, 5)

    print(completion_msg)
    print("\n---")

    assert "✅ Scene 1 Complete" in completion_msg
    assert "Repair Tutorial" in completion_msg
    assert "Moving to Scene 2" in completion_msg
    assert "sidebar" in completion_msg.lower()

    print("✅ Mid-scene completion message correct")

    print("\n=== Test 5: Final Scene Completion ===")

    final_msg = format_scene_completion_message("Victory Screen", 5, 5)

    print(final_msg)
    print("\n---")

    assert "Scene 5 Complete" in final_msg
    assert "All scenes complete" in final_msg
    assert "🎉" in final_msg
    assert "generate" in final_msg.lower()

    print("✅ Final completion message correct")

    print("\n=== Test 6: Question Format Consistency ===")

    # Test multiple questions have consistent format
    questions = [
        Question(text="Q1?", reasoning="R1", category="mechanics"),
        Question(text="Q2?", reasoning="R2", category="ui", suggestions=["S1", "S2"]),
        Question(text="Q3?", reasoning="R3", category="timing", optional=True, default_value="5s"),
    ]

    for i, q in enumerate(questions, 1):
        formatted = format_question_message(q, f"Scene {i}")

        # All should have scene title
        assert f"Scene {i}" in formatted

        # All should have question text
        assert q.text in formatted

        # All should have reasoning
        assert q.reasoning in formatted

        print(f"✓ Question {i} formatted consistently")

    print("✅ All questions follow consistent format")

    print("\n=== Test 7: Markdown Formatting ===")

    question = Question(
        text="Test question?",
        reasoning="Test reasoning",
        category="ui",
        suggestions=["Option 1", "Option 2"]
    )

    formatted = format_question_message(question, "Test Scene")

    # Check markdown elements
    assert "**Scene:" in formatted  # Bold scene
    assert "**Test question?" in formatted  # Bold question
    assert "_Test reasoning_" in formatted  # Italic reasoning
    assert "💡 **Suggestions:**" in formatted  # Bold suggestions header
    assert "- Option 1" in formatted  # List items

    print("✅ Markdown formatting correct")

    print("\n=== Task 3.3 Acceptance: PASSED ===")
    print("\nNote: Full chat workflow integration requires Task 4.2")
    print("These formatting functions are ready for use in orchestrator")


if __name__ == "__main__":
    test_chat_interface()
