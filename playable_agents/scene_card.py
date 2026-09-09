"""Scene Card data structure for ScenarioBuilder agent"""

from pydantic import BaseModel, Field
from typing import Any, Literal, Optional, ClassVar
from enum import Enum


class WarningSeverity(str, Enum):
    """Warning severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Warning(BaseModel):
    """Soft validation warning"""
    message: str
    severity: WarningSeverity = WarningSeverity.MEDIUM
    field: Optional[str] = None  # Which field this warning relates to
    suggestion: Optional[str] = None  # Suggested fix
    source: str = "validation"  # "validation" | "pdf_deviation" | "asset_check"

    def __str__(self) -> str:
        prefix = {
            WarningSeverity.LOW: "ℹ️",
            WarningSeverity.MEDIUM: "⚠️",
            WarningSeverity.HIGH: "⚠️",
        }[self.severity]
        field_info = f" ({self.field})" if self.field else ""
        return f"{prefix} {self.message}{field_info}"


class SceneState(str, Enum):
    """Scene card state"""
    EMPTY = "empty"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"


class SceneCard(BaseModel):
    """
    Scene card representing a single scene in the playable ad.

    State transitions: empty → in_progress → complete
    """

    # Identity
    id: str
    title: str = "Untitled Scene"
    state: SceneState = SceneState.EMPTY

    # Core data - what defines this scene
    mechanics: list[str] = Field(default_factory=list)
    ui_elements: dict[str, str] = Field(default_factory=dict)
    timing: dict[str, float] = Field(default_factory=dict)
    user_actions: list[str] = Field(default_factory=list)
    technical: dict[str, Any] = Field(default_factory=dict)

    # Metadata
    warnings: list[Warning] = Field(default_factory=list)
    defaults_used: dict[str, Any] = Field(default_factory=dict)
    pdf_source: Optional[str] = None

    # Tracking
    order: int = 0  # Position in scene sequence

    # Required fields for completeness (class constants)
    REQUIRED_FIELDS: ClassVar[list[str]] = ["mechanics", "ui_elements", "user_actions"]
    REQUIRED_TIMING_KEYS: ClassVar[list[str]] = ["duration"]

    def start_progress(self) -> None:
        """Transition from empty to in_progress"""
        if self.state == SceneState.EMPTY:
            self.state = SceneState.IN_PROGRESS

    def mark_complete(self, force: bool = False) -> bool:
        """
        Transition to complete state.
        Returns True if successful, False if requirements not met.

        Args:
            force: Skip completeness check (for manual override)
        """
        if force or self.is_complete():
            self.state = SceneState.COMPLETE
            return True
        return False

    def is_complete(self) -> bool:
        """
        Check if scene is complete.

        A scene is complete if:
        1. Explicitly marked complete (state == COMPLETE), OR
        2. All required fields are filled

        Required fields:
        - At least one mechanic defined
        - At least one UI element defined
        - Duration in timing
        - At least one user action defined
        """
        # If explicitly marked complete, trust it
        if self.state == SceneState.COMPLETE:
            return True

        # Otherwise check if all fields are filled
        if not self.mechanics:
            return False
        if not self.ui_elements:
            return False
        if not self.user_actions:
            return False

        # Check timing has duration
        if "duration" not in self.timing or self.timing["duration"] <= 0:
            return False

        return True

    def get_completeness_status(self) -> dict[str, bool]:
        """
        Get detailed completeness status for each requirement.
        Useful for UI to show what's missing.
        """
        return {
            "has_mechanics": bool(self.mechanics),
            "has_ui_elements": bool(self.ui_elements),
            "has_user_actions": bool(self.user_actions),
            "has_duration": "duration" in self.timing and self.timing["duration"] > 0,
        }

    def get_warnings(self) -> list[Warning]:
        """Get all current warnings"""
        return self.warnings

    def add_warning(
        self,
        message: str,
        severity: WarningSeverity = WarningSeverity.MEDIUM,
        field: Optional[str] = None,
        suggestion: Optional[str] = None,
        source: str = "validation"
    ) -> None:
        """Add a warning to this scene card"""
        warning = Warning(
            message=message,
            severity=severity,
            field=field,
            suggestion=suggestion,
            source=source
        )
        self.warnings.append(warning)

    def clear_warnings(self, source: Optional[str] = None) -> None:
        """
        Clear warnings.

        Args:
            source: If provided, only clear warnings from this source
        """
        if source:
            self.warnings = [w for w in self.warnings if w.source != source]
        else:
            self.warnings = []

    def track_default(self, field: str, value: Any) -> None:
        """
        Track that a field is using a default value.
        Used for UI to show "(using default: X)"
        """
        self.defaults_used[field] = value

    def is_using_default(self, field: str) -> bool:
        """Check if a field is using a default value"""
        return field in self.defaults_used

    def get_default_value(self, field: str) -> Optional[Any]:
        """Get the default value for a field, if using default"""
        return self.defaults_used.get(field)

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON export"""
        return self.model_dump(mode='python')

    @classmethod
    def from_dict(cls, data: dict) -> "SceneCard":
        """Deserialize from dictionary"""
        return cls(**data)

    def __str__(self) -> str:
        """Human-readable representation"""
        status = {
            SceneState.EMPTY: "⚪",
            SceneState.IN_PROGRESS: "🔵",
            SceneState.COMPLETE: "✅",
        }[self.state]
        warning_count = len(self.warnings)
        warning_text = f" ({warning_count} warnings)" if warning_count > 0 else ""
        return f"{status} Scene {self.order + 1}: {self.title}{warning_text}"


# Helper function for creating empty scene cards
def create_empty_scene(
    scene_id: str,
    title: str,
    order: int = 0,
    pdf_source: Optional[str] = None
) -> SceneCard:
    """
    Create an empty scene card.
    Useful for scene detection phase.
    """
    return SceneCard(
        id=scene_id,
        title=title,
        order=order,
        pdf_source=pdf_source,
        state=SceneState.EMPTY
    )


# Helper function for checking if all scenes are complete
def all_scenes_complete(scenes: list[SceneCard]) -> bool:
    """Check if all scenes in a list are complete"""
    return all(scene.is_complete() for scene in scenes)


# Helper function for getting total warning count
def total_warnings(scenes: list[SceneCard]) -> int:
    """Get total warning count across all scenes"""
    return sum(len(scene.warnings) for scene in scenes)
