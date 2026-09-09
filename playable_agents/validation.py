"""Soft validation logic for scene cards"""

from typing import Any
from playable_agents.scene_card import SceneCard, Warning, WarningSeverity
from models import DraftBrief, AssetMapping


def check_pdf_deviation(card: SceneCard, pdf_data: DraftBrief) -> list[Warning]:
    """
    Check if scene card deviates from PDF specification.

    Returns list of warnings (non-blocking).
    """
    warnings = []

    # Find corresponding scene in PDF
    pdf_scene = next(
        (s for s in pdf_data.scenes if s.id == card.id),
        None
    )

    if not pdf_scene:
        # Scene not in PDF - might be inferred
        warnings.append(
            Warning(
                message=f"Scene '{card.title}' not explicitly defined in PDF",
                severity=WarningSeverity.LOW,
                field="scene",
                suggestion="Verify this scene is needed",
                source="pdf_deviation",
            )
        )
        return warnings

    # Check timing deviations (if PDF has expected duration)
    if "duration" in card.timing:
        duration = card.timing["duration"]
        # Typical durations by type
        expected_durations = {
            "tutorial": (5, 10),
            "battle": (3, 7),
            "victory": (3, 5),
        }
        scene_type = pdf_scene.type
        if scene_type and scene_type in expected_durations:
            min_d, max_d = expected_durations[scene_type]
            if duration < min_d or duration > max_d:
                warnings.append(
                    Warning(
                        message=f"Duration {duration}s outside typical range for {scene_type} ({min_d}-{max_d}s)",
                        severity=WarningSeverity.MEDIUM,
                        field="timing.duration",
                        suggestion=f"Consider {(min_d + max_d) / 2}s",
                        source="pdf_deviation",
                    )
                )

    # Check mechanics match PDF description
    pdf_desc = pdf_scene.description.lower()
    for mechanic in card.mechanics:
        if mechanic not in pdf_desc and mechanic not in ["tutorial", "cta"]:
            # Some mechanics are implied
            pass

    return warnings


def check_asset_availability(card: SceneCard, assets: AssetMapping) -> list[Warning]:
    """
    Check if required assets are available.

    Returns list of warnings about missing assets.
    """
    warnings = []

    # Check if drag-drop mechanics have draggable assets
    if "drag-drop" in card.mechanics or "grid-placement" in card.mechanics:
        if not assets.characters and not assets.tools:
            warnings.append(
                Warning(
                    message="Drag-drop mechanic but no draggable assets (characters/tools) found",
                    severity=WarningSeverity.HIGH,
                    field="mechanics",
                    suggestion="Add character or tool assets",
                    source="asset_check",
                )
            )

    # Check if battle scene has visual assets
    if "battle" in card.mechanics:
        if not assets.background:
            warnings.append(
                Warning(
                    message="Battle scene without background asset",
                    severity=WarningSeverity.MEDIUM,
                    field="technical",
                    suggestion="Add battle background",
                    source="asset_check",
                )
            )

    # Check if victory scene has reward assets
    if "victory" in card.mechanics or "cta" in card.mechanics:
        # Victory scenes typically show rewards
        if len(assets.icons) < 3:
            warnings.append(
                Warning(
                    message=f"Victory screen with only {len(assets.icons)} icons (typical: 3+ rewards)",
                    severity=WarningSeverity.LOW,
                    field="ui_elements",
                    suggestion="Add more reward icons",
                    source="asset_check",
                )
            )

    return warnings


def check_logic_conflicts(cards: list[SceneCard]) -> list[Warning]:
    """
    Check for logical conflicts across scenes.

    Returns list of warnings about flow/logic issues.
    """
    warnings = []

    if not cards:
        return warnings

    # Check: Should have exactly one victory scene
    victory_scenes = [c for c in cards if "victory" in c.mechanics or "cta" in c.mechanics]
    if len(victory_scenes) == 0:
        warnings.append(
            Warning(
                message="No victory/CTA scene found - playable needs an end screen",
                severity=WarningSeverity.HIGH,
                field="scenes",
                suggestion="Add victory scene at the end",
                source="validation",
            )
        )
    elif len(victory_scenes) > 1:
        warnings.append(
            Warning(
                message=f"Multiple victory scenes ({len(victory_scenes)}) - typically only one needed",
                severity=WarningSeverity.MEDIUM,
                field="scenes",
                suggestion="Verify scene flow",
                source="validation",
            )
        )

    # Check: Victory should be last scene
    if victory_scenes and cards[-1] not in victory_scenes:
        warnings.append(
            Warning(
                message="Victory scene not at the end of flow",
                severity=WarningSeverity.MEDIUM,
                field="scenes",
                suggestion="Move victory scene to end",
                source="validation",
            )
        )

    # Check: Tutorial before battle (best practice)
    tutorial_indices = [i for i, c in enumerate(cards) if "tutorial" in c.mechanics]
    battle_indices = [i for i, c in enumerate(cards) if "battle" in c.mechanics]

    if tutorial_indices and battle_indices:
        first_tutorial = min(tutorial_indices)
        first_battle = min(battle_indices)
        if first_battle < first_tutorial:
            warnings.append(
                Warning(
                    message="Battle appears before tutorial - may confuse players",
                    severity=WarningSeverity.LOW,
                    field="scenes",
                    suggestion="Consider tutorial before battle",
                    source="validation",
                )
            )

    # Check: Each scene should have duration
    for card in cards:
        if "duration" not in card.timing or card.timing["duration"] <= 0:
            warnings.append(
                Warning(
                    message=f"Scene '{card.title}' missing duration",
                    severity=WarningSeverity.HIGH,
                    field="timing.duration",
                    suggestion="Set scene duration (3-10s typical)",
                    source="validation",
                )
            )

    return warnings


def get_completeness_status(card: SceneCard) -> dict[str, Any]:
    """
    Get detailed completeness status for a scene card.

    Returns dict with:
    - complete: bool
    - missing_fields: list[str]
    - warnings_count: int
    - field_status: dict
    """
    status = card.get_completeness_status()

    missing = []
    if not status["has_mechanics"]:
        missing.append("mechanics")
    if not status["has_ui_elements"]:
        missing.append("ui_elements")
    if not status["has_user_actions"]:
        missing.append("user_actions")
    if not status["has_duration"]:
        missing.append("timing.duration")

    return {
        "complete": card.is_complete(),
        "missing_fields": missing,
        "warnings_count": len(card.warnings),
        "field_status": status,
    }


def validate_all_scenes(
    cards: list[SceneCard],
    pdf_data: DraftBrief,
    assets: AssetMapping
) -> dict[str, Any]:
    """
    Run all validations on scene cards.

    Returns summary dict with all warnings.
    """
    all_warnings = []

    # Per-card validations
    for card in cards:
        # Check PDF deviation
        pdf_warnings = check_pdf_deviation(card, pdf_data)
        for w in pdf_warnings:
            card.add_warning(w.message, w.severity, w.field, w.suggestion, w.source)
        all_warnings.extend(pdf_warnings)

        # Check asset availability
        asset_warnings = check_asset_availability(card, assets)
        for w in asset_warnings:
            card.add_warning(w.message, w.severity, w.field, w.suggestion, w.source)
        all_warnings.extend(asset_warnings)

    # Cross-scene validations
    logic_warnings = check_logic_conflicts(cards)
    # Logic warnings apply to the scenario, not specific cards
    all_warnings.extend(logic_warnings)

    # Compile summary
    critical_count = sum(1 for w in all_warnings if w.severity == WarningSeverity.HIGH)
    warnings_count = sum(1 for w in all_warnings if w.severity == WarningSeverity.MEDIUM)
    info_count = sum(1 for w in all_warnings if w.severity == WarningSeverity.LOW)

    incomplete_scenes = [c for c in cards if not c.is_complete()]

    return {
        "total_warnings": len(all_warnings),
        "critical": critical_count,
        "warnings": warnings_count,
        "info": info_count,
        "incomplete_scenes": len(incomplete_scenes),
        "all_warnings": all_warnings,
        "ready_for_generation": len(incomplete_scenes) == 0,
    }
