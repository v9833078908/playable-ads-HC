"""ScenarioBuilder Agent - Interactive scenario building through adaptive questioning

DEPRECATED: This module is deprecated and will be removed in a future version.
Use scenario_agent.py instead for the new multi-agent architecture.
"""

import warnings
warnings.warn(
    "scenario_builder.py is deprecated. Use scenario_agent.py instead.",
    DeprecationWarning,
    stacklevel=2
)

from typing import Any, Optional, Literal
from pydantic import BaseModel, Field

from models import DraftBrief, AssetMapping
from playable_agents.scene_card import (
    SceneCard,
    SceneState,
    create_empty_scene,
    all_scenes_complete,
    total_warnings,
)


class Question(BaseModel):
    """Question to ask user about a scene"""
    text: str
    reasoning: str
    category: Literal["mechanics", "ui", "timing", "technical"]
    optional: bool = False
    suggestions: list[str] = Field(default_factory=list)
    default_value: Optional[Any] = None


class DetectedScene(BaseModel):
    """Scene detected from PDF analysis"""
    id: str
    title: str
    confidence: str  # "clear" | "inferred" | "unclear"
    source: str  # Description from PDF
    detected_mechanics: list[str] = []
    detected_type: Optional[str] = None  # tutorial | battle | victory | hook


class SceneDetectionResult(BaseModel):
    """Result of scene detection from PDF + assets"""
    detected: list[DetectedScene] = []  # Clear scenes from PDF
    inferred: list[DetectedScene] = []  # Scenes inferred from context
    missing_info: list[str] = []  # What's unclear or missing


class ScenarioBuilder:
    """
    Interactive agent that builds complete game flow through adaptive questioning.

    Workflow:
    1. detect_scenes() - Analyze PDF + assets, create empty scene cards
    2. generate_questions() - Ask 3-7 questions per scene
    3. process_answer() - Update scene card with answer
    4. detect_patterns() - Find cross-scene patterns
    5. interpret_feedback() - Parse regeneration comments
    """

    def __init__(self, brief: DraftBrief, assets: AssetMapping):
        self.brief = brief
        self.assets = assets
        self.scene_cards: list[SceneCard] = []

    def detect_scenes(self) -> SceneDetectionResult:
        """
        Detect scenes from PDF analysis and available assets.

        Returns categorized scenes:
        - detected: Clear scenes from PDF with high confidence
        - inferred: Scenes suggested by context/assets
        - missing_info: Unclear or ambiguous elements

        Creates empty SceneCards for all detected + inferred scenes.
        """
        result = SceneDetectionResult()

        # Process scenes from PDF
        for idx, scene_desc in enumerate(self.brief.scenes):
            # Analyze confidence based on description quality
            confidence = self._assess_scene_confidence(scene_desc)

            # Detect mechanics from description
            mechanics = self._detect_mechanics_from_description(scene_desc.description)

            detected_scene = DetectedScene(
                id=scene_desc.id or f"scene_{idx + 1}",
                title=self._extract_scene_title(scene_desc),
                confidence=confidence,
                source=scene_desc.description,
                detected_mechanics=mechanics,
                detected_type=scene_desc.type,
            )

            # Categorize by confidence
            if confidence == "clear":
                result.detected.append(detected_scene)
            elif confidence == "inferred":
                result.inferred.append(detected_scene)
            else:  # unclear
                result.missing_info.append(
                    f"Scene {idx + 1}: {scene_desc.description[:50]}... (unclear structure)"
                )

        # Check for common missing elements
        self._check_missing_elements(result)

        # Create empty scene cards for all detected + inferred scenes
        self._create_scene_cards(result.detected + result.inferred)

        return result

    def _assess_scene_confidence(self, scene_desc: Any) -> str:
        """
        Assess confidence level for a scene based on description quality.

        Returns:
        - "clear": Well-defined scene with mechanics and structure
        - "inferred": Scene mentioned but lacks detail
        - "unclear": Ambiguous or missing critical info
        """
        desc = scene_desc.description.lower()

        # Clear indicators: has type, has description, mentions mechanics
        has_type = scene_desc.type is not None
        has_mechanics = any(
            keyword in desc
            for keyword in [
                "drag",
                "tap",
                "battle",
                "merge",
                "place",
                "tutorial",
                "victory",
                "cta",
            ]
        )
        has_ui_text = scene_desc.ui_text is not None
        is_detailed = len(desc) > 20

        if has_type and has_mechanics and is_detailed:
            return "clear"
        elif has_type or has_mechanics:
            return "inferred"
        else:
            return "unclear"

    def _detect_mechanics_from_description(self, description: str) -> list[str]:
        """
        Extract mechanics keywords from scene description.

        Detects: drag-drop, merge, battle, tutorial, etc.
        """
        desc_lower = description.lower()
        mechanics = []

        mechanic_keywords = {
            "drag": "drag-drop",
            "place": "grid-placement",
            "merge": "merge",
            "battle": "battle",
            "fight": "battle",
            "attack": "battle",
            "repair": "repair",
            "tutorial": "tutorial",
            "victory": "victory",
            "cta": "cta",
            "tap": "tap",
            "click": "tap",
        }

        for keyword, mechanic in mechanic_keywords.items():
            if keyword in desc_lower and mechanic not in mechanics:
                mechanics.append(mechanic)

        return mechanics

    def _extract_scene_title(self, scene_desc: Any) -> str:
        """
        Extract a human-readable title from scene description.

        Falls back to scene ID if no clear title found.
        """
        # Check if scene has explicit UI text
        if scene_desc.ui_text:
            return scene_desc.ui_text[:30]  # Limit length

        # Check scene type
        if scene_desc.type:
            type_titles = {
                "tutorial": "Tutorial",
                "battle": "Battle",
                "victory": "Victory Screen",
                "hook": "Hook",
            }
            title = type_titles.get(scene_desc.type, scene_desc.type.title())

            # Add detail from description if available
            desc = scene_desc.description
            if "repair" in desc.lower():
                return f"{title}: Repair"
            elif "weapon" in desc.lower():
                return f"{title}: Weapons"
            elif "merge" in desc.lower():
                return f"{title}: Merge"
            elif "shield" in desc.lower():
                return f"{title}: Shield"

            return title

        # Fallback: use first 30 chars of description
        desc = scene_desc.description.strip()
        if len(desc) > 30:
            return desc[:27] + "..."
        return desc or "Untitled Scene"

    def _check_missing_elements(self, result: SceneDetectionResult) -> None:
        """
        Check for common missing or unclear elements in the scenario.

        Adds warnings to missing_info list.
        """
        # Check if we have any scenes at all
        if not result.detected and not result.inferred:
            result.missing_info.append("No scenes detected from PDF")

        # Check for victory/CTA scene
        has_victory = any(
            s.detected_type == "victory" for s in result.detected + result.inferred
        )
        if not has_victory:
            result.missing_info.append("No victory/CTA scene detected")

        # Check for hook scene
        has_hook = any(
            s.detected_type == "hook" or "hook" in s.title.lower()
            for s in result.detected + result.inferred
        )
        if not has_hook:
            result.missing_info.append(
                "No hook scene detected (optional but recommended)"
            )

        # Check if we have enough assets for detected mechanics
        if not self.assets.characters and any(
            "drag-drop" in s.detected_mechanics or "grid-placement" in s.detected_mechanics
            for s in result.detected + result.inferred
        ):
            result.missing_info.append(
                "Drag-drop mechanics detected but no character/object assets found"
            )

    def _create_scene_cards(self, detected_scenes: list[DetectedScene]) -> None:
        """
        Create empty SceneCards for all detected scenes.

        Cards are stored in self.scene_cards and returned with state=EMPTY.
        """
        self.scene_cards = []

        for idx, detected_scene in enumerate(detected_scenes):
            # Create empty card
            card = create_empty_scene(
                scene_id=detected_scene.id,
                title=detected_scene.title,
                order=idx,
                pdf_source=detected_scene.source,
            )

            # Pre-fill detected mechanics (if any)
            if detected_scene.detected_mechanics:
                card.mechanics = detected_scene.detected_mechanics

            self.scene_cards.append(card)

    def get_scene_cards(self) -> list[SceneCard]:
        """Get current scene cards"""
        return self.scene_cards

    def get_scene_by_id(self, scene_id: str) -> Optional[SceneCard]:
        """Get scene card by ID"""
        for card in self.scene_cards:
            if card.id == scene_id:
                return card
        return None

    def generate_questions(
        self, scene_card: SceneCard, complexity: Optional[str] = None
    ) -> list[Question]:
        """
        Generate adaptive questions for a scene.

        Args:
            scene_card: Scene to generate questions for
            complexity: Override complexity ("simple" | "medium" | "complex")
                       If None, auto-detected from scene

        Returns:
            List of 3-7 questions based on complexity

        Question distribution by complexity:
        - Simple (3 questions): Core mechanic, UI text, CTA
        - Medium (5 questions): + Timing, User feedback
        - Complex (7 questions): + Animations, Edge cases
        """
        # Auto-detect complexity if not provided
        if complexity is None:
            complexity = self._detect_complexity(scene_card)

        questions = []

        # Core questions (always asked)
        questions.extend(self._generate_core_questions(scene_card))

        # Additional questions based on complexity
        if complexity in ("medium", "complex"):
            questions.extend(self._generate_medium_questions(scene_card))

        if complexity == "complex":
            questions.extend(self._generate_complex_questions(scene_card))

        return questions

    def _detect_complexity(self, scene_card: SceneCard) -> str:
        """
        Detect scene complexity based on mechanics and type.

        Returns: "simple" | "medium" | "complex"
        """
        mechanics_count = len(scene_card.mechanics)
        title_lower = scene_card.title.lower()

        # Simple scenes: Victory, hook, single mechanic
        if "victory" in title_lower or "cta" in scene_card.mechanics:
            return "simple"

        if mechanics_count <= 1:
            return "simple"

        # Complex scenes: Multiple mechanics, battle with other mechanics
        if mechanics_count >= 3:
            return "complex"

        if "battle" in scene_card.mechanics and mechanics_count >= 2:
            return "complex"

        # Default: medium
        return "medium"

    def _generate_core_questions(self, scene_card: SceneCard) -> list[Question]:
        """
        Generate core questions (always asked, ~2-3 questions).

        Categories: mechanics, ui
        """
        questions = []
        title = scene_card.title

        # Question 1: Core mechanic behavior
        if "battle" in scene_card.mechanics:
            questions.append(
                Question(
                    text=f"In '{title}', what happens during the battle?",
                    reasoning="This defines the battle loop logic and determines DPS, HP changes, and win/lose conditions.",
                    category="mechanics",
                    suggestions=[
                        "Auto-battle with damage over time",
                        "Player deals damage, enemy responds",
                        "Health decreases until one side wins",
                    ],
                )
            )
        elif "drag-drop" in scene_card.mechanics or "grid-placement" in scene_card.mechanics:
            # Get available assets for suggestions
            asset_suggestions = self._get_asset_suggestions()
            questions.append(
                Question(
                    text=f"In '{title}', what should the player drag and where?",
                    reasoning="This defines the drag-drop interaction and grid placement requirements.",
                    category="mechanics",
                    suggestions=asset_suggestions or [
                        "Drag character/unit to grid slot",
                        "Place item in specific position",
                        "Fill slots in sequence",
                    ],
                )
            )
        elif "merge" in scene_card.mechanics:
            questions.append(
                Question(
                    text=f"In '{title}', what items should merge and into what?",
                    reasoning="This defines the merge mechanic and result assets.",
                    category="mechanics",
                    suggestions=[
                        "Two same items merge into upgraded version",
                        "Specific items combine into new item",
                        "Drag one item onto another to merge",
                    ],
                )
            )
        elif "victory" in title.lower() or "cta" in scene_card.mechanics:
            # Victory screen questions
            questions.append(
                Question(
                    text=f"What should the victory screen title say?",
                    reasoning="This is the main celebratory text that creates excitement.",
                    category="ui",
                    suggestions=[
                        "VICTORY!",
                        "YOU WIN!",
                        "LEVEL COMPLETE!",
                        "GREAT JOB!",
                    ],
                    default_value="VICTORY!",
                )
            )
            questions.append(
                Question(
                    text=f"What rewards should be displayed?",
                    reasoning="This shows what the player can unlock in the full game.",
                    category="ui",
                    suggestions=[
                        "New weapons and characters",
                        "Upgraded ships and items",
                        "Special abilities",
                    ],
                    default_value="3 reward cards",
                )
            )
            questions.append(
                Question(
                    text=f"What should the CTA button text be?",
                    reasoning="This is the final call-to-action text that drives installs.",
                    category="ui",
                    suggestions=[
                        "TAKE REWARD",
                        "PLAY NOW",
                        "DOWNLOAD NOW",
                        "GET REWARDS",
                    ],
                    default_value="TAKE REWARD",
                )
            )
            return questions  # Victory has all questions defined, return early
        else:
            # Generic mechanic question
            questions.append(
                Question(
                    text=f"What is the main action in '{title}'?",
                    reasoning="This defines the core player interaction in this scene.",
                    category="mechanics",
                )
            )

        # Question 2: UI text/copy
        if "victory" not in title.lower():  # Victory has CTA question already
            questions.append(
                Question(
                    text=f"What text should appear on screen in '{title}'?",
                    reasoning="This is the primary instructional or feedback text shown to the player.",
                    category="ui",
                    suggestions=self._get_ui_text_suggestions(scene_card),
                )
            )

        return questions

    def _generate_medium_questions(self, scene_card: SceneCard) -> list[Question]:
        """
        Generate medium complexity questions (~2 questions).

        Categories: timing, ui (feedback)
        """
        questions = []
        title = scene_card.title

        # Question: Timing/Duration
        if "battle" in scene_card.mechanics:
            questions.append(
                Question(
                    text=f"How long should '{title}' last?",
                    reasoning="This determines the battle duration and pacing.",
                    category="timing",
                    suggestions=["3 seconds (fast)", "5 seconds (medium)", "7 seconds (long)"],
                    default_value=5.0,
                )
            )
        elif "tutorial" in title.lower() or "tutorial" in scene_card.mechanics:
            questions.append(
                Question(
                    text=f"What happens when the player completes the action in '{title}'?",
                    reasoning="This defines tutorial completion feedback and transition.",
                    category="ui",
                    suggestions=[
                        "Show checkmark and auto-advance",
                        "Highlight next step",
                        "Display success message",
                    ],
                    default_value="Auto-advance to next scene",
                )
            )

        # Question: Error handling / User feedback
        if "drag-drop" in scene_card.mechanics or "grid-placement" in scene_card.mechanics:
            questions.append(
                Question(
                    text=f"What happens when player drags to wrong location in '{title}'?",
                    reasoning="This affects tutorial clarity and user experience.",
                    category="ui",
                    suggestions=[
                        "Item snaps back to original position",
                        "Show red highlight/shake",
                        "Play error sound",
                        "Do nothing (allow wrong placement)",
                    ],
                    default_value="Item snaps back",
                    optional=True,
                )
            )

        return questions

    def _generate_complex_questions(self, scene_card: SceneCard) -> list[Question]:
        """
        Generate complex scene questions (~2-3 questions).

        Categories: technical, timing (animations)
        """
        questions = []
        title = scene_card.title

        # Question: Animations/VFX
        if "battle" in scene_card.mechanics:
            questions.append(
                Question(
                    text=f"What visual effects should appear during '{title}'?",
                    reasoning="This enhances battle feel and provides feedback.",
                    category="technical",
                    suggestions=[
                        "Damage numbers",
                        "Fire/explosion effects",
                        "Screen shake on hit",
                        "HP bar animations",
                    ],
                    optional=True,
                )
            )
            # Additional battle-specific question
            questions.append(
                Question(
                    text=f"What happens when player's HP reaches zero in '{title}'?",
                    reasoning="This defines the lose condition and game over behavior.",
                    category="mechanics",
                    suggestions=[
                        "Game over with retry button",
                        "Auto-repair and continue",
                        "Transition to defeat screen",
                        "Restart scene",
                    ],
                    default_value="Auto-advance (scripted win)",
                    optional=True,
                )
            )
        elif "merge" in scene_card.mechanics:
            questions.append(
                Question(
                    text=f"How should the merge animation look in '{title}'?",
                    reasoning="This defines the merge visual feedback and timing.",
                    category="technical",
                    suggestions=[
                        "Flash effect + particle burst",
                        "Items slide together smoothly",
                        "Scale up with glow",
                    ],
                    default_value="Flash + particles",
                    optional=True,
                )
            )

        # Question: Performance/Edge cases
        questions.append(
            Question(
                text=f"Should '{title}' be skippable or auto-advance?",
                reasoning="This affects pacing and user control.",
                category="timing",
                suggestions=[
                    "Auto-advance after completion",
                    "Require tap to continue",
                    "Skippable with button",
                ],
                default_value="Auto-advance",
                optional=True,
            )
        )

        return questions

    def _get_asset_suggestions(self) -> list[str]:
        """Get suggestions based on available assets"""
        suggestions = []

        if self.assets.characters:
            char = self.assets.characters[0]
            suggestions.append(f"Drag {char.description or 'character'}")

        if self.assets.tools:
            tool = self.assets.tools[0]
            suggestions.append(f"Place {tool.description or 'tool'}")

        if self.assets.icons:
            icon = self.assets.icons[0]
            suggestions.append(f"Use {icon.description or 'icon'}")

        return suggestions

    def _get_ui_text_suggestions(self, scene_card: SceneCard) -> list[str]:
        """Get UI text suggestions based on scene type"""
        title_lower = scene_card.title.lower()

        if "repair" in title_lower:
            return ["REPAIR YOUR SHIP", "FIX THE DAMAGE", "RESTORE HEALTH"]
        elif "weapon" in title_lower:
            return ["SETUP WEAPONS", "ARM YOUR SHIP", "PREPARE FOR BATTLE"]
        elif "merge" in title_lower:
            return ["MERGE WEAPONS", "COMBINE UNITS", "UPGRADE POWER"]
        elif "battle" in title_lower:
            return ["FIGHT!", "BATTLE TIME", "DEFEAT THE ENEMY"]
        else:
            return ["TAP TO CONTINUE", "DRAG TO PLACE", "COMPLETE OBJECTIVE"]

    def process_answer(
        self, question: Question, answer: str, scene_card: SceneCard
    ) -> SceneCard:
        """
        Process user answer and update scene card.

        Args:
            question: The question that was asked
            answer: User's answer (text)
            scene_card: Scene card to update

        Returns:
            Updated scene card

        Logic:
        - Parse answer (free text, selections, numbers)
        - Update appropriate card field based on question category
        - Apply defaults if skipped ("skip", empty, etc.)
        - Track which fields use defaults
        """
        # Handle skip/empty answers
        if not answer or answer.lower().strip() in ["skip", "default", ""]:
            if question.default_value is not None:
                self._apply_default(question, scene_card)
            return scene_card

        # Update card based on question category
        if question.category == "mechanics":
            self._process_mechanics_answer(question, answer, scene_card)
        elif question.category == "ui":
            self._process_ui_answer(question, answer, scene_card)
        elif question.category == "timing":
            self._process_timing_answer(question, answer, scene_card)
        elif question.category == "technical":
            self._process_technical_answer(question, answer, scene_card)

        # Update scene state
        if scene_card.state == SceneState.EMPTY:
            scene_card.start_progress()

        return scene_card

    def _apply_default(self, question: Question, scene_card: SceneCard) -> None:
        """Apply default value and track it"""
        default = question.default_value

        if question.category == "ui":
            # Extract field name from question
            if "cta" in question.text.lower() or "button" in question.text.lower():
                scene_card.ui_elements["cta_text"] = default
                scene_card.track_default("ui_elements.cta_text", default)
            elif "title" in question.text.lower() or "text" in question.text.lower():
                scene_card.ui_elements["title"] = default
                scene_card.track_default("ui_elements.title", default)
            elif "reward" in question.text.lower():
                scene_card.ui_elements["rewards"] = default
                scene_card.track_default("ui_elements.rewards", default)

        elif question.category == "timing":
            if "duration" in question.text.lower() or "long" in question.text.lower():
                scene_card.timing["duration"] = float(default) if not isinstance(default, float) else default
                scene_card.track_default("timing.duration", default)
            elif "skip" in question.text.lower() or "advance" in question.text.lower():
                scene_card.timing["auto_advance"] = True
                scene_card.track_default("timing.auto_advance", True)

        elif question.category == "mechanics":
            if "hp" in question.text.lower() or "zero" in question.text.lower():
                scene_card.technical["lose_condition"] = default
                scene_card.track_default("technical.lose_condition", default)

        elif question.category == "technical":
            if "animation" in question.text.lower() or "merge" in question.text.lower():
                scene_card.technical["merge_animation"] = default
                scene_card.track_default("technical.merge_animation", default)

    def _process_mechanics_answer(
        self, question: Question, answer: str, scene_card: SceneCard
    ) -> None:
        """Process mechanics-related answer"""
        answer_lower = answer.lower()

        # Parse answer for mechanic details
        if "battle" in question.text.lower():
            # Battle mechanic details
            scene_card.technical["battle_logic"] = answer

            # Extract specifics if mentioned
            if "dps" in answer_lower or "damage" in answer_lower:
                scene_card.technical["has_damage"] = True
            if "hp" in answer_lower or "health" in answer_lower:
                scene_card.technical["tracks_hp"] = True

        elif "drag" in question.text.lower():
            # Drag-drop mechanic
            if "drag-drop" not in scene_card.mechanics:
                scene_card.mechanics.append("drag-drop")
            scene_card.user_actions.append(f"Drag: {answer}")

        elif "merge" in question.text.lower():
            # Merge mechanic
            scene_card.technical["merge_config"] = answer
            scene_card.user_actions.append(f"Merge: {answer}")

        elif "action" in question.text.lower():
            # Generic action
            scene_card.user_actions.append(answer)

    def _process_ui_answer(
        self, question: Question, answer: str, scene_card: SceneCard
    ) -> None:
        """Process UI-related answer"""
        # Determine which UI field to update
        if "cta" in question.text.lower() or "button" in question.text.lower():
            scene_card.ui_elements["cta_text"] = answer
        elif "title" in question.text.lower() or ("text" in question.text.lower() and "screen" in question.text.lower()):
            scene_card.ui_elements["title"] = answer
        elif "reward" in question.text.lower():
            scene_card.ui_elements["rewards"] = answer
        elif "wrong" in question.text.lower() or "error" in question.text.lower():
            # Error handling
            scene_card.technical["error_handling"] = answer
            scene_card.user_actions.append(f"On error: {answer}")
        elif "complete" in question.text.lower():
            # Completion feedback
            scene_card.technical["completion_feedback"] = answer
        else:
            # Generic UI text
            scene_card.ui_elements["text"] = answer

    def _process_timing_answer(
        self, question: Question, answer: str, scene_card: SceneCard
    ) -> None:
        """Process timing-related answer"""
        answer_lower = answer.lower()

        # Parse duration
        if "duration" in question.text.lower() or "long" in question.text.lower():
            # Try to extract number
            duration = self._extract_number(answer)
            if duration:
                scene_card.timing["duration"] = duration
            else:
                # Parse qualitative answers
                if "fast" in answer_lower or "quick" in answer_lower:
                    scene_card.timing["duration"] = 3.0
                    scene_card.track_default("timing.duration", 3.0)
                elif "long" in answer_lower or "slow" in answer_lower:
                    scene_card.timing["duration"] = 7.0
                    scene_card.track_default("timing.duration", 7.0)
                else:  # medium
                    scene_card.timing["duration"] = 5.0
                    scene_card.track_default("timing.duration", 5.0)

        # Parse skip/auto-advance
        elif "skip" in question.text.lower() or "advance" in question.text.lower():
            if "auto" in answer_lower:
                scene_card.timing["auto_advance"] = True
            elif "skip" in answer_lower:
                scene_card.timing["skippable"] = True
            elif "tap" in answer_lower or "click" in answer_lower:
                scene_card.timing["requires_tap"] = True

    def _process_technical_answer(
        self, question: Question, answer: str, scene_card: SceneCard
    ) -> None:
        """Process technical-related answer"""
        answer_lower = answer.lower()

        # VFX/animations
        if "effect" in question.text.lower() or "visual" in question.text.lower():
            scene_card.technical["vfx"] = answer

            # Parse specific effects
            effects = []
            if "damage" in answer_lower:
                effects.append("damage_numbers")
            if "fire" in answer_lower or "explosion" in answer_lower:
                effects.append("fire_effects")
            if "shake" in answer_lower:
                effects.append("screen_shake")
            if "hp" in answer_lower or "bar" in answer_lower:
                effects.append("hp_animations")

            if effects:
                scene_card.technical["vfx_list"] = effects

        # Animation details
        elif "animation" in question.text.lower():
            scene_card.technical["animation_style"] = answer

        # Performance/other
        else:
            scene_card.technical["notes"] = answer

    def _extract_number(self, text: str) -> Optional[float]:
        """Extract first number from text"""
        import re
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        if match:
            return float(match.group(1))
        return None

    # TODO: Implement remaining methods
    # - detect_patterns(completed_cards)
    # - interpret_feedback(feedback_text, cards)
