from pydantic import BaseModel


class ExtractedComponent(BaseModel):
    """Single extracted component from an image"""
    id: str                         # "teeth_0", "tool_0", "bg_0"
    base64: str                     # PNG with transparency
    role: str                       # "main_gameplay_object" | "interactive_tool" | "decoration" | "icon"
    description: str = ""           # "dirty teeth with debris"
    source_image_index: int = 0     # which source image this came from
    bbox: list[int] | None = None   # [x, y, w, h] if known


class BackgroundInfo(BaseModel):
    """Background information"""
    type: str                       # "solid_color" | "gradient" | "image"
    primary_color: str | None = None  # "#D4B8A0"
    base64: str | None = None       # if background is an image


class AssetMapping(BaseModel):
    """Result of analysis and segmentation"""
    components: list[ExtractedComponent] = []
    background: BackgroundInfo | None = None
    style: str = "cartoon"

    @property
    def characters(self) -> list[ExtractedComponent]:
        """Get main gameplay objects / characters"""
        return [c for c in self.components if c.role in ("main_gameplay_object", "character")]

    @property
    def tools(self) -> list[ExtractedComponent]:
        """Get interactive tools"""
        return [c for c in self.components if c.role == "interactive_tool"]

    @property
    def icons(self) -> list[ExtractedComponent]:
        """Get icons"""
        return [c for c in self.components if c.role == "icon"]

    @property
    def decorations(self) -> list[ExtractedComponent]:
        """Get decorative elements"""
        return [c for c in self.components if c.role == "decoration"]

    @property
    def all_images_base64(self) -> dict[str, str]:
        """Get all assets as id->base64 dict for template rendering"""
        result = {}

        # Background
        if self.background and self.background.base64:
            result["bg_0"] = self.background.base64

        # Components by role
        for i, comp in enumerate(self.characters):
            result[f"char_{i}"] = comp.base64
        for i, comp in enumerate(self.tools):
            result[f"tool_{i}"] = comp.base64
        for i, comp in enumerate(self.icons):
            result[f"icon_{i}"] = comp.base64
        for i, comp in enumerate(self.decorations):
            result[f"deco_{i}"] = comp.base64

        return result


# Keep ExtractedAsset for backward compatibility during migration
class ExtractedAsset(BaseModel):
    """Single analyzed asset (deprecated - use ExtractedComponent)"""
    index: int
    base64: str
    category: str  # background | character | icon | ui_screen
    style: str = "cartoon"
    colors: list[str] = []
    suggested_role: str = "unknown"
