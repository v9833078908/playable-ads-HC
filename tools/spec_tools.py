from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from models import PlayableSpec, SceneSpec, MechanicConfig, DraftBrief, AssetMapping


def build_playable_spec(
    brief: DraftBrief,
    assets: AssetMapping,
    answers: dict,
) -> PlayableSpec:
    """Build complete PlayableSpec DSL from brief, assets and user answers"""

    # Prepare assets dict with base64 data URLs
    images_dict = {}

    # Background handling
    if assets.background:
        if assets.background.type == "image" and assets.background.base64:
            images_dict["bg_0"] = f"data:image/png;base64,{assets.background.base64}"
        # For solid_color backgrounds, we use CSS - no image needed

    # Characters / main gameplay objects
    for i, char in enumerate(assets.characters):
        images_dict[f"char_{i}"] = f"data:image/png;base64,{char.base64}"

    # Tools / interactive objects
    for i, tool in enumerate(assets.tools):
        images_dict[f"tool_{i}"] = f"data:image/png;base64,{tool.base64}"

    # Icons
    for i, icon in enumerate(assets.icons):
        images_dict[f"icon_{i}"] = f"data:image/png;base64,{icon.base64}"

    # Decorations
    for i, deco in enumerate(assets.decorations):
        images_dict[f"deco_{i}"] = f"data:image/png;base64,{deco.base64}"

    # Build scenes from brief
    scenes = _build_scenes(brief, assets)

    # Prepare background color for CSS
    bg_color = None
    if assets.background and assets.background.type == "solid_color":
        bg_color = assets.background.primary_color

    return PlayableSpec(
        meta={
            "title": brief.title,
            "language": answers.get("language", "EN"),
            "network": "unity",
            "background_color": bg_color,  # Add background color to meta
        },
        mraid={
            "version": "3.0",
            "start_gate": ["ready", "viewableChange"],
            "click_url_android": answers.get("store_android", "https://play.google.com/store"),
            "click_url_ios": answers.get("store_ios", "https://apps.apple.com"),
        },
        layout={
            "base_resolution": [1080, 1920],
            "orientation": "both",
        },
        assets={"images": images_dict},
        scenes=scenes,
        mechanics=["GridPlacement", "DragDrop", "Battle", "Victory"],
    )


def _build_scenes(brief: DraftBrief, assets: AssetMapping) -> list[SceneSpec]:
    """Convert scene descriptions to SceneSpec with mechanics config"""
    scenes = []

    # Check if we have image-based or solid color background
    has_bg_image = assets.background and assets.background.type == "image"

    for scene in brief.scenes:
        scene_type = scene.type or _infer_type(scene)

        if scene_type == "tutorial":
            scenes.append(
                SceneSpec(
                    id=scene.id,
                    type="tutorial",
                    background="bg_0" if has_bg_image else None,
                    ui={
                        "title": scene.ui_text or brief.copy_texts.get("title", "REPAIR YOUR SHIP"),
                        "subtitle": brief.copy_texts.get("subtitle", "DRAG ITEMS TO THE GRID"),
                    },
                    mechanics=[
                        MechanicConfig(
                            type="GridPlacement",
                            config={
                                "grid": [3, 2],
                                "required_items": min(2, len(assets.characters)),
                            },
                        )
                    ],
                )
            )

        elif scene_type == "battle":
            scenes.append(
                SceneSpec(
                    id=scene.id,
                    type="battle",
                    background="bg_0" if has_bg_image else None,
                    ui={},
                    mechanics=[
                        MechanicConfig(
                            type="BattleLoop",
                            config={
                                "player_hp": 100,
                                "enemy_hp": 100,
                                "duration": 5,
                            },
                        )
                    ],
                )
            )

        elif scene_type == "victory":
            scenes.append(
                SceneSpec(
                    id=scene.id,
                    type="victory",
                    background=None,
                    ui={
                        "title": "VICTORY!",
                        "subtitle": brief.copy_texts.get("victory_text", "Collect your rewards!"),
                        "cta": brief.copy_texts.get("cta", "DOWNLOAD NOW"),
                    },
                    mechanics=[MechanicConfig(type="CTAOpenStore", config={})],
                )
            )

    # Ensure we have at least the basic 3 scenes
    if not scenes:
        scenes = [
            SceneSpec(
                id="tutorial",
                type="tutorial",
                background="bg_0" if has_bg_image else None,
                ui={"title": "REPAIR YOUR SHIP", "subtitle": "DRAG ITEMS"},
                mechanics=[MechanicConfig(type="GridPlacement", config={"grid": [3, 2], "required_items": 2})],
            ),
            SceneSpec(
                id="battle",
                type="battle",
                background="bg_0" if has_bg_image else None,
                mechanics=[MechanicConfig(type="BattleLoop", config={"duration": 5})],
            ),
            SceneSpec(
                id="victory",
                type="victory",
                ui={"title": "VICTORY!", "cta": "DOWNLOAD NOW"},
                mechanics=[MechanicConfig(type="CTAOpenStore", config={})],
            ),
        ]

    return scenes


def _infer_type(scene) -> str:
    """Infer scene type from description"""
    desc = (scene.description or "").lower()
    if "drag" in desc or "tutorial" in desc or "repair" in desc:
        return "tutorial"
    elif "battle" in desc or "fight" in desc or "hp" in desc:
        return "battle"
    elif "victory" in desc or "win" in desc or "reward" in desc or "cta" in desc:
        return "victory"
    return "tutorial"


def render_template(spec: PlayableSpec, template_name: str = "ship_grid_merge_v1") -> str:
    """Render HTML from PlayableSpec using Jinja2 template"""
    templates_dir = Path(__file__).parent.parent / "frontend" / "templates"
    env = Environment(loader=FileSystemLoader(str(templates_dir)))
    template = env.get_template(f"{template_name}/template.html")

    # Convert SceneSpec to dicts for Jinja
    scenes_data = []
    for scene in spec.scenes:
        scene_dict = {
            "id": scene.id,
            "type": scene.type,
            "background": scene.background,
            "ui": scene.ui,
            "mechanics": [{"type": m.type, "config": m.config} for m in scene.mechanics],
        }
        scenes_data.append(scene_dict)

    return template.render(
        meta=spec.meta,
        mraid=spec.mraid,
        layout=spec.layout,
        assets=spec.assets,
        scenes=scenes_data,
        copy=spec.meta,
    )
