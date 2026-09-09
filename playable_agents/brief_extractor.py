"""
Brief Extractor Agent

DEPRECATED: This module is deprecated and will be removed in a future version.
Use scenario_agent.py instead for the new multi-agent architecture.
"""

import warnings
warnings.warn(
    "brief_extractor.py is deprecated. Use scenario_agent.py instead.",
    DeprecationWarning,
    stacklevel=2
)

from agents import Agent, function_tool, RunContextWrapper
from typing import Any

from models import DraftBrief, AssetMapping
from tools.pdf_tools import extract_content
from tools.image_tools import analyze_images_with_gemini


@function_tool
async def extract_brief(ctx: RunContextWrapper[Any]) -> str:
    """Extract brief from uploaded PDF and/or text specification"""
    pdf_bytes = ctx.context.get("pdf_bytes")
    text_spec = ctx.context.get("text_spec")

    if not pdf_bytes and not text_spec:
        return "Error: No PDF or text specification provided"

    brief = await extract_content(pdf_bytes=pdf_bytes, text_spec=text_spec)

    # Store in context
    ctx.context["brief"] = brief

    # Build response with source information
    sources = []
    if pdf_bytes:
        sources.append("📄 PDF document")
    if text_spec:
        sources.append("📝 text specification")

    source_info = " and ".join(sources)
    response = f"""Brief extracted from {source_info}:
- Title: {brief.title}
- Languages: {', '.join(brief.languages)}
- Scenes: {len(brief.scenes)} found
- Copy texts: {list(brief.copy_texts.keys())}
- Unknowns: {brief.unknowns if brief.unknowns else 'None'}"""

    # Add merge notes if both sources were used
    if brief.merge_notes:
        response += "\n\nMerge details:\n" + "\n".join(f"  • {note}" for note in brief.merge_notes)

    return response


@function_tool
async def analyze_images(ctx: RunContextWrapper[Any]) -> str:
    """Analyze and segment uploaded images using Gemini Vision + rembg"""
    images_bytes = ctx.context.get("images_bytes", [])
    if not images_bytes:
        return "Error: No images uploaded"

    assets = await analyze_images_with_gemini(images_bytes)

    # Store in context
    ctx.context["assets"] = assets

    # Build response with new component-based structure
    bg_info = "None"
    if assets.background:
        if assets.background.type == "solid_color":
            bg_info = f"Solid color: {assets.background.primary_color}"
        else:
            bg_info = f"Image background"

    return f"""Images analyzed and segmented:
- Background: {bg_info}
- Characters/Objects: {len(assets.characters)}
- Tools: {len(assets.tools)}
- Icons: {len(assets.icons)}
- Decorations: {len(assets.decorations)}
- Style: {assets.style}
Total: {len(assets.components)} extracted components ready"""


brief_extractor_agent = Agent(
    name="BriefExtractor",
    handoff_description="Extracts requirements from PDF/text and classifies images using AI",
    instructions="""You extract playable ad requirements from uploaded files.

Your job:
1. Call extract_brief() to parse the PDF and/or text specification and extract scenes, copy texts, etc.
2. Call analyze_images() to classify all images using Gemini Vision

After both extractions are complete, summarize what was found and what's missing.
Then hand back to Triage agent for next steps.

Always be helpful and explain what was extracted clearly.""",
    tools=[extract_brief, analyze_images],
)
