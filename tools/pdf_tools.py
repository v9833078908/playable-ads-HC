import fitz  # PyMuPDF
import json
import logging
import base64
import asyncio

from models import DraftBrief, SceneDescription
from services.openai_client import openai_client
from services.gemini_client import gemini_client

logger = logging.getLogger('PDFTools')

GEMINI_TIMEOUT = 15  # seconds


async def extract_pdf_content(pdf_bytes: bytes) -> DraftBrief:
    logger.info(f"extract_pdf_content: {len(pdf_bytes)} bytes")
    """Extract brief from PDF using GPT-4 for text + Gemini for images"""

    logger.info("Opening PDF with fitz...")
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    logger.info(f"PDF opened, {len(doc)} pages")

    # Extract text from all pages
    full_text = ""
    page_images = []

    for i, page in enumerate(doc):
        full_text += page.get_text()
        # Render page as image for Gemini visual analysis
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        page_images.append(pix.tobytes("png"))
        logger.info(f"Page {i+1} extracted")

    doc.close()
    logger.info(f"PDF text extracted: {len(full_text)} chars")

    # GPT-4 for text analysis
    logger.info("Calling GPT-5.2 for text analysis...")
    text_analysis = await openai_client.chat.completions.create(
        model="gpt-5.2",
        messages=[
            {
                "role": "user",
                "content": f"""Analyze this playable ad specification and extract ALL scenes.

IMPORTANT:
- Find ALL numbered scenes (Сцена 1, Сцена 1.1, Сцена 2, Сцена 2.1, etc.)
- Each scene or sub-scene should be a separate entry
- Don't limit to 3 scenes - extract as many as exist
- Look for tutorial phases (Ремонт, Оружие, Слияние) and their battle phases
- CTA text is usually in English even in Russian specs

Specification:
{full_text}

Extract JSON:
{{
    "title": "game title from PDF",
    "languages": ["RU", "EN"],
    "scenes": [
        {{"id": "repair", "description": "Player drags repair module to grid cells", "ui_text": "REPAIR YOUR SHIP", "type": "tutorial"}},
        {{"id": "repair_battle", "description": "Enemy shoots, repairman fixes ship under shield", "type": "battle"}},
        {{"id": "weapons", "description": "Player places cannons in grid cells", "ui_text": "SETUP WEAPONS", "type": "tutorial"}},
        {{"id": "weapons_battle", "description": "Player's cannons shoot enemy, take damage", "type": "battle"}},
        {{"id": "merge", "description": "Player drags one cannon onto another to merge", "ui_text": "MERGE WEAPONS", "type": "tutorial"}},
        {{"id": "merge_battle", "description": "Skeleton cannon appears and shoots powerful volley", "type": "battle"}},
        {{"id": "victory", "description": "Victory screen with rewards and CTA button", "type": "victory"}}
    ],
    "copy_texts": {{"title": "...", "subtitle": "...", "cta": "TAKE REWARD"}},
    "unknowns": ["things not clearly specified in PDF"]
}}

Return ONLY valid JSON with ALL scenes found.""",
            }
        ],
        response_format={"type": "json_object"},
    )

    logger.info("GPT-5.2 response received")
    text_data = json.loads(text_analysis.choices[0].message.content or "{}")
    logger.info(f"Parsed JSON: title={text_data.get('title')}, scenes={len(text_data.get('scenes', []))}")
    logger.info(f"text_data FULL: {json.dumps(text_data, ensure_ascii=False)}")

    # If no text found, use vision to analyze PDF pages
    visual_references = []
    if len(full_text.strip()) < 100 and page_images:
        logger.info("PDF has no/little text, using vision for page analysis...")

        vision_data = None

        # Try Gemini first with timeout
        try:
            logger.info(f"Trying Gemini Vision (timeout={GEMINI_TIMEOUT}s)...")
            vision_data = await asyncio.wait_for(
                gemini_client.extract_from_pdf_page(page_images[0]),
                timeout=GEMINI_TIMEOUT
            )
            logger.info(f"Gemini Vision success: {vision_data.get('title', 'no title')}")
            logger.info(f"Gemini Vision FULL RESPONSE: {json.dumps(vision_data, ensure_ascii=False)}")
        except asyncio.TimeoutError:
            logger.warning(f"Gemini timeout after {GEMINI_TIMEOUT}s, switching to GPT-5.2...")
        except Exception as e:
            logger.warning(f"Gemini failed: {e}, switching to GPT-5.2...")

        # Fallback to GPT-5.2 if Gemini failed
        if vision_data is None:
            try:
                logger.info("Trying GPT-5.2 Vision as fallback...")
                b64_page = base64.b64encode(page_images[0]).decode()
                vision_response = await openai_client.chat.completions.create(
                    model="gpt-5.2",
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": """Analyze this playable ad specification page and extract ALL scenes.

IMPORTANT:
- Find ALL numbered scenes (Сцена 1, 1.1, 2, 2.1, 3, 3.1, 4, etc.)
- Each scene or sub-scene should be separate
- Don't limit to 3 scenes - extract as many as visible
- Look for tutorial phases (Ремонт/Repair, Оружие/Weapons, Слияние/Merge) and their battle phases
- Include the victory/store transition scene

Extract JSON:
{
    "title": "game title from document",
    "scenes": [
        {"id": "repair", "description": "detailed description", "ui_text": "REPAIR YOUR SHIP", "type": "tutorial"},
        {"id": "repair_battle", "description": "...", "type": "battle"},
        {"id": "weapons", "description": "...", "ui_text": "SETUP WEAPONS", "type": "tutorial"},
        {"id": "weapons_battle", "description": "...", "type": "battle"},
        {"id": "merge", "description": "...", "ui_text": "MERGE WEAPONS", "type": "tutorial"},
        {"id": "merge_battle", "description": "...", "type": "battle"},
        {"id": "victory", "description": "...", "type": "victory"}
    ],
    "copy_texts": {"title": "...", "subtitle": "...", "cta": "..."},
    "game_type": "merge|pirate battle|etc"
}

Return ONLY valid JSON with ALL scenes found."""},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_page}"}}
                        ]
                    }],
                    response_format={"type": "json_object"}
                )
                vision_data = json.loads(vision_response.choices[0].message.content or "{}")
                logger.info(f"GPT-5.2 Vision success: {vision_data.get('title', 'no title')}")
                logger.info(f"GPT-5.2 Vision FULL RESPONSE: {json.dumps(vision_data, ensure_ascii=False)}")
            except Exception as e:
                logger.error(f"GPT-5.2 Vision also failed: {e}")

        # Merge vision data if available
        if vision_data:
            logger.info(f"Merging vision_data into text_data...")
            if vision_data.get("title"):
                text_data["title"] = vision_data["title"]
            if vision_data.get("scenes"):
                text_data["scenes"] = vision_data["scenes"]
                logger.info(f"Merged {len(vision_data['scenes'])} scenes from vision_data")
            if vision_data.get("copy_texts"):
                text_data["copy_texts"] = vision_data["copy_texts"]
            visual_references.append(vision_data)
            logger.info(f"text_data AFTER MERGE: {json.dumps(text_data, ensure_ascii=False)}")

    # Build DraftBrief
    scenes = []
    for s in text_data.get("scenes", []):
        scenes.append(
            SceneDescription(
                id=s.get("id", "scene"),
                description=s.get("description", ""),
                ui_text=s.get("ui_text"),
                type=s.get("type"),
            )
        )

    # Default scenes if none found
    if not scenes:
        scenes = [
            SceneDescription(id="tutorial", description="Drag items to grid", type="tutorial"),
            SceneDescription(id="battle", description="Battle with HP bars", type="battle"),
            SceneDescription(id="victory", description="Victory screen with CTA", type="victory"),
        ]

    brief = DraftBrief(
        title=text_data.get("title", "Playable Ad"),
        networks=["unity"],
        languages=text_data.get("languages", ["EN"]),
        scenes=scenes,
        copy_texts=text_data.get("copy_texts", {}),
        unknowns=text_data.get("unknowns", []),
        visual_references=visual_references,
    )

    # Tag all fields with "pdf" source
    brief.sources["title"] = "pdf"
    for i in range(len(brief.scenes)):
        brief.sources[f"scenes.{i}"] = "pdf"
    for key in brief.copy_texts.keys():
        brief.sources[f"copy_texts.{key}"] = "pdf"

    return brief


async def extract_text_content(text_spec: str) -> DraftBrief:
    """Extract brief from free-form text specification using GPT-4"""
    logger.info(f"extract_text_content: {len(text_spec)} chars")

    if not text_spec or len(text_spec.strip()) < 10:
        logger.warning("Text specification too short, returning defaults")
        brief = DraftBrief(
            title="Playable Ad",
            scenes=[
                SceneDescription(id="tutorial", description="Tutorial scene", type="tutorial"),
                SceneDescription(id="battle", description="Battle scene", type="battle"),
                SceneDescription(id="victory", description="Victory scene", type="victory"),
            ]
        )
        brief.sources["title"] = "text"
        for i in range(len(brief.scenes)):
            brief.sources[f"scenes.{i}"] = "text"
        return brief

    # GPT-4 for text analysis
    logger.info("Calling GPT-5.2 for free-form text analysis...")
    try:
        text_analysis = await openai_client.chat.completions.create(
            model="gpt-5.2",
            messages=[
                {
                    "role": "user",
                    "content": f"""Analyze this free-form playable ad specification and extract game information.

IMPORTANT:
- This is free-form text from the user, not a structured document
- Extract as many scenes as mentioned or implied
- Identify scene types: tutorial, battle, victory
- Extract any UI text or CTA mentions
- If information is unclear, use reasonable defaults

Specification:
{text_spec}

Extract JSON:
{{
    "title": "game title or 'Playable Ad' if not specified",
    "languages": ["EN"],
    "scenes": [
        {{"id": "scene_id", "description": "what happens in this scene", "ui_text": "UI text if any", "type": "tutorial|battle|victory"}}
    ],
    "copy_texts": {{"title": "...", "subtitle": "...", "cta": "..."}},
    "unknowns": ["things that need clarification"]
}}

Return ONLY valid JSON.""",
                }
            ],
            response_format={"type": "json_object"},
        )

        logger.info("GPT-5.2 response received")
        text_data = json.loads(text_analysis.choices[0].message.content or "{}")
        logger.info(f"Parsed JSON: title={text_data.get('title')}, scenes={len(text_data.get('scenes', []))}")

    except Exception as e:
        logger.error(f"GPT-5.2 text extraction failed: {e}")
        text_data = {}

    # Build DraftBrief
    scenes = []
    for s in text_data.get("scenes", []):
        scenes.append(
            SceneDescription(
                id=s.get("id", "scene"),
                description=s.get("description", ""),
                ui_text=s.get("ui_text"),
                type=s.get("type"),
            )
        )

    # Default scenes if none found
    if not scenes:
        scenes = [
            SceneDescription(id="tutorial", description="Tutorial scene", type="tutorial"),
            SceneDescription(id="battle", description="Battle scene", type="battle"),
            SceneDescription(id="victory", description="Victory screen with CTA", type="victory"),
        ]

    brief = DraftBrief(
        title=text_data.get("title", "Playable Ad"),
        networks=["unity"],
        languages=text_data.get("languages", ["EN"]),
        scenes=scenes,
        copy_texts=text_data.get("copy_texts", {}),
        unknowns=text_data.get("unknowns", []),
        visual_references=[],
    )

    # Tag all fields with "text" source
    brief.sources["title"] = "text"
    for i in range(len(brief.scenes)):
        brief.sources[f"scenes.{i}"] = "text"
    for key in brief.copy_texts.keys():
        brief.sources[f"copy_texts.{key}"] = "text"

    return brief


def merge_briefs(text_brief: DraftBrief | None, pdf_brief: DraftBrief | None) -> DraftBrief:
    """Intelligently merge DraftBriefs from text and PDF sources"""
    logger.info("merge_briefs called")

    # Handle single-source cases
    if not text_brief and not pdf_brief:
        logger.warning("No briefs to merge, returning defaults")
        return DraftBrief()

    if not text_brief:
        logger.info("Only PDF brief provided, returning it")
        return pdf_brief

    if not pdf_brief:
        logger.info("Only text brief provided, returning it")
        return text_brief

    # Both sources available - merge intelligently
    logger.info("Merging text and PDF briefs")
    merged = DraftBrief()

    # Title: prefer PDF
    if pdf_brief.title != "Playable Ad":
        merged.title = pdf_brief.title
        merged.sources["title"] = "pdf"
        merged.confidence_scores["title"] = 0.95
        if text_brief.title != "Playable Ad" and text_brief.title != pdf_brief.title:
            merged.merge_notes.append(f"Title conflict: used PDF '{pdf_brief.title}' over text '{text_brief.title}'")
    else:
        merged.title = text_brief.title
        merged.sources["title"] = "text"
        merged.confidence_scores["title"] = 0.85

    # Networks: union
    merged.networks = list(set(text_brief.networks + pdf_brief.networks))

    # Languages: union
    merged.languages = list(set(text_brief.languages + pdf_brief.languages))

    # Scenes: merge by ID, prefer PDF for conflicts
    scenes_dict = {}

    # Add text scenes first
    for scene in text_brief.scenes:
        scenes_dict[scene.id] = scene
        merged.sources[f"scenes.{scene.id}"] = "text"

    # Override/merge with PDF scenes
    for scene in pdf_brief.scenes:
        if scene.id in scenes_dict:
            # Conflict - prefer PDF but note it
            existing_desc = scenes_dict[scene.id].description
            if existing_desc != scene.description:
                merged.merge_notes.append(f"Scene '{scene.id}': merged descriptions from both sources")
                # Combine descriptions if they're different
                scenes_dict[scene.id] = scene
                scenes_dict[scene.id].description = f"{scene.description} | {existing_desc}"
                merged.sources[f"scenes.{scene.id}"] = "merged"
                merged.confidence_scores[f"scenes.{scene.id}"] = 0.90
            else:
                scenes_dict[scene.id] = scene
                merged.sources[f"scenes.{scene.id}"] = "pdf"
        else:
            scenes_dict[scene.id] = scene
            merged.sources[f"scenes.{scene.id}"] = "pdf"

    merged.scenes = list(scenes_dict.values())

    # Copy texts: merge dictionaries, prefer PDF for conflicts
    merged.copy_texts = {**text_brief.copy_texts}
    for key, value in pdf_brief.copy_texts.items():
        if key in merged.copy_texts and merged.copy_texts[key] != value:
            merged.merge_notes.append(f"Copy text '{key}': used PDF value over text value")
            merged.sources[f"copy_texts.{key}"] = "pdf"
        else:
            merged.sources[f"copy_texts.{key}"] = "pdf" if key in pdf_brief.copy_texts else "text"
        merged.copy_texts[key] = value

    # Unknowns: combine
    merged.unknowns = list(set(text_brief.unknowns + pdf_brief.unknowns))

    # Visual references: only from PDF
    merged.visual_references = pdf_brief.visual_references

    logger.info(f"Merged brief: {len(merged.scenes)} scenes, {len(merged.merge_notes)} merge notes")

    return merged


async def extract_content(pdf_bytes: bytes | None = None, text_spec: str | None = None) -> DraftBrief:
    """Wrapper function handling all three input modes (text-only, PDF-only, both)"""
    logger.info(f"extract_content called: pdf={pdf_bytes is not None}, text={text_spec is not None}")

    # Validate at least one source
    if not pdf_bytes and not text_spec:
        logger.error("No PDF or text specification provided")
        raise ValueError("At least one of pdf_bytes or text_spec must be provided")

    # Extract from available sources
    pdf_brief = None
    text_brief = None

    if pdf_bytes:
        logger.info("Extracting from PDF...")
        pdf_brief = await extract_pdf_content(pdf_bytes)

    if text_spec and text_spec.strip():
        logger.info("Extracting from text...")
        text_brief = await extract_text_content(text_spec)

    # Merge and return
    return merge_briefs(text_brief, pdf_brief)
