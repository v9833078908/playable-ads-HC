from pydantic import BaseModel


class MechanicConfig(BaseModel):
    """Configuration for a game mechanic"""
    type: str  # GridPlacement | BattleLoop | CTAOpenStore
    config: dict = {}


class SceneSpec(BaseModel):
    """Scene specification for rendering"""
    id: str
    type: str  # tutorial | battle | victory
    background: str | None = None
    ui: dict = {}
    mechanics: list[MechanicConfig] = []


class PlayableSpec(BaseModel):
    """Complete playable specification (DSL)"""
    meta: dict = {}
    mraid: dict = {}
    layout: dict = {}
    assets: dict = {}
    scenes: list[SceneSpec] = []
    mechanics: list[str] = []
