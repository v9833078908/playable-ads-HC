"""
Legacy PlayableGenerator Agent

DEPRECATED: This module is deprecated and will be removed in a future version.
Use generator_agent.py instead for the new multi-agent architecture.
"""

import warnings
warnings.warn(
    "generator.py is deprecated. Use generator_agent.py instead.",
    DeprecationWarning,
    stacklevel=2
)

from agents import Agent, function_tool, RunContextWrapper
from typing import Any

from models import PlayableSpec
from tools.spec_tools import build_playable_spec
from tools.asset_tools import compress_images
from playable_agents.html_generator import generate_html


@function_tool
def build_spec(ctx: RunContextWrapper[Any]) -> str:
    """Build complete PlayableSpec from collected data"""
    brief = ctx.context.get("brief")
    assets = ctx.context.get("assets")
    answers = ctx.context.get("answers", {})

    if not brief or not assets:
        return "Error: Brief or assets not found. Run extraction first."

    spec = build_playable_spec(brief, assets, answers)
    ctx.context["spec"] = spec

    return f"""PlayableSpec created:
- Title: {spec.meta.get('title')}
- Network: {spec.meta.get('network')}
- Language: {spec.meta.get('language')}
- Scenes: {len(spec.scenes)}
- Assets: {len(spec.assets.get('images', {}))} images
- Mechanics: {', '.join(spec.mechanics)}"""


@function_tool
def render_html(ctx: RunContextWrapper[Any]) -> str:
    """Render HTML from PlayableSpec using dynamic generation"""
    spec = ctx.context.get("spec")
    if not spec:
        return "Error: PlayableSpec not found. Build spec first."

    # Use dynamic HTML generation instead of templates
    html = generate_html(spec)

    # Store HTML
    ctx.context["html"] = html

    size_kb = len(html.encode("utf-8")) / 1024
    return f"HTML generated successfully! Size: {size_kb:.1f} KB (dynamic generation)"


@function_tool
def compress_html_images(ctx: RunContextWrapper[Any]) -> str:
    """Compress images in HTML to reduce file size"""
    html = ctx.context.get("html")
    if not html:
        return "Error: No HTML to compress"

    original_size = len(html.encode("utf-8")) / 1024
    compressed = compress_images(html, quality=70)
    new_size = len(compressed.encode("utf-8")) / 1024

    ctx.context["html"] = compressed

    return f"Compressed: {original_size:.1f}KB -> {new_size:.1f}KB (saved {original_size - new_size:.1f}KB)"


generator_agent = Agent(
    name="PlayableGenerator",
    handoff_description="Generates the final HTML playable from collected data",
    instructions="""You generate the final playable HTML using dynamic code generation.

Steps:
1. Call build_spec() to create PlayableSpec from brief + assets + answers
2. Call render_html() to generate HTML dynamically based on mechanics
3. Optionally call compress_html_images() if size is large

The HTML is generated programmatically based on the game mechanics in the spec.
No templates are used - everything is built from scratch for each game type.

After generation, hand off to QA agent for validation.

If any step fails, explain the error clearly.""",
    tools=[build_spec, render_html, compress_html_images],
)
