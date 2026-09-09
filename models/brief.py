from pydantic import BaseModel
from typing import Optional


class SceneDescription(BaseModel):
    """Scene extracted from PDF"""
    id: str
    description: str = ""
    ui_text: Optional[str] = None
    type: Optional[str] = None  # tutorial | battle | victory


class DraftBrief(BaseModel):
    """Extracted info from PDF and/or text input"""
    title: str = "Playable Ad"
    networks: list[str] = ["unity"]
    languages: list[str] = ["EN"]
    scenes: list[SceneDescription] = []
    copy_texts: dict[str, str] = {}
    unknowns: list[str] = []
    visual_references: list[dict] = []  # From Gemini PDF analysis

    # Source tracking
    sources: dict[str, str] = {}  # Maps field paths to source ("text", "pdf", "merged")
    confidence_scores: dict[str, float] = {}  # Confidence per field (0.0-1.0)
    merge_notes: list[str] = []  # Human-readable merge decisions
