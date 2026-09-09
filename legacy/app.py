import streamlit as st
import asyncio
import logging
import sys
import json
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app_debug.log')
    ]
)
logger = logging.getLogger('PlayableApp')
logger.info("=== App Starting ===")

from playable_agents.orchestrator import PlayableOrchestrator
from tools.validation_tools import validate_html

logger.info("Imports completed")

st.set_page_config(page_title="Playable Ads Generator", page_icon="🎮", layout="wide")

# Load custom CSS
css_path = Path(__file__).parent / "frontend" / ".streamlit" / "custom.css"
if css_path.exists():
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.title("🎮 Playable Ads Generator")
st.caption("AI-агент на OpenAI Agents SDK + Gemini Vision")

# === SESSION STATE ===
if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = PlayableOrchestrator()
if "messages" not in st.session_state:
    st.session_state.messages = []
if "html" not in st.session_state:
    st.session_state.html = None
if "step" not in st.session_state:
    st.session_state.step = "upload"
if "spec" not in st.session_state:
    st.session_state.spec = None
if "spec_text" not in st.session_state:
    st.session_state.spec_text = None
if "edit_mode" not in st.session_state:
    st.session_state.edit_mode = False
if "scene_cards" not in st.session_state:
    st.session_state.scene_cards = []
if "current_scene_idx" not in st.session_state:
    st.session_state.current_scene_idx = 0
if "workflow_stage" not in st.session_state:
    st.session_state.workflow_stage = "upload"
    # States: upload | scenario_building | confirmation | generation
if "scenario_initialized" not in st.session_state:
    st.session_state.scenario_initialized = False
if "active_question" not in st.session_state:
    st.session_state.active_question = None
if "text_specification" not in st.session_state:
    st.session_state.text_specification = ""
if "has_text_input" not in st.session_state:
    st.session_state.has_text_input = False
if "has_pdf_input" not in st.session_state:
    st.session_state.has_pdf_input = False

orch = st.session_state.orchestrator


def run_async(coro):
    """Run async function in sync context"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def format_detection_message(detection_result):
    """Format scene detection result for chat"""
    detected = detection_result.get("detected", [])
    inferred = detection_result.get("inferred", [])
    total = len(detected) + len(inferred)

    msg = f"### 🎬 Detected {total} Scenes\n\n"

    if detected:
        msg += "**From your spec:**\n"
        for scene in detected:
            msg += f"- {scene['title']}\n"

    if inferred:
        msg += f"\n**Additional scenes:**\n"
        for scene in inferred:
            msg += f"- {scene['title']}\n"

    msg += f"\n_Let's configure each scene. I'll ask 3-7 questions per scene._"
    return msg


def format_question_message(question, scene_title):
    """
    Format question for chat display with reasoning and suggestions.

    Returns markdown-formatted message.
    """
    from playable_agents.scenario_builder import Question

    # Build message
    message = f"**Scene: {scene_title}**\n\n"
    message += f"**{question.text}**\n\n"

    # Add reasoning
    message += f"_{question.reasoning}_\n\n"

    # Add suggestions if available
    if question.suggestions:
        message += "💡 **Suggestions:**\n"
        for suggestion in question.suggestions:
            message += f"- {suggestion}\n"
        message += "\n"

    # Add optional indicator
    if question.optional:
        message += "_You can skip this question (type 'skip' or leave empty)_\n\n"

    # Show default if available
    if question.default_value:
        message += f"_Default: {question.default_value}_\n"

    return message


def format_scene_completion_message(scene_title, scene_number, total_scenes):
    """
    Format scene completion message.

    Returns markdown-formatted message.
    """
    message = f"### ✅ Scene {scene_number} Complete: {scene_title}\n\n"

    if scene_number < total_scenes:
        message += f"Moving to Scene {scene_number + 1}...\n\n"
        message += "_Review the card in the sidebar before continuing._"
    else:
        message += "**All scenes complete!** 🎉\n\n"
        message += "Ready to generate the playable HTML."

    return message


def handle_scenario_answer(user_answer: str, orch: PlayableOrchestrator) -> str:
    """Process user answer during scenario building"""
    from playable_agents.scenario_builder import Question

    logger.info(f"handle_scenario_answer: user_answer={user_answer[:100]}...")

    # Process answer
    logger.info("Calling orch.process_answer...")
    answer_result = orch.process_answer(user_answer)
    logger.info(f"process_answer result: {list(answer_result.keys())}")

    # Update scene cards in session
    st.session_state.scene_cards = orch.context["scene_cards"]
    logger.info(f"Updated scene_cards in session: {len(st.session_state.scene_cards)} cards")

    if "question" in answer_result:
        # Next question
        logger.info(f"Next question for scene {answer_result['scene_idx']}: {answer_result['scene_title']}")
        st.session_state.active_question = answer_result
        st.session_state.current_scene_idx = answer_result["scene_idx"]

        question_obj = Question(**answer_result["question"])
        return format_question_message(
            question_obj,
            answer_result["scene_title"]
        )

    elif answer_result.get("complete"):
        # All scenes complete
        logger.info("All scenes complete! Switching to confirmation stage")
        st.session_state.workflow_stage = "confirmation"
        return """### 🎉 Scenario Complete!

All scenes configured. Review the scenario in the sidebar, then generate HTML.

_Switching to confirmation screen..._"""

    else:
        return answer_result.get("error", "Something went wrong. Please try again.")


def render_scene_card(card, idx):
    """
    Render a scene card with inline editing capabilities.

    Visual states:
    - Empty (⚪) → In Progress (🔵) → Complete (✅)
    - Amber warning indicator (⚠️) for issues
    """
    from playable_agents.scene_card import SceneState

    # Check if this is the active scene
    is_active = (
        st.session_state.workflow_stage == "scenario_building" and
        st.session_state.current_scene_idx == idx
    )

    # State icon
    state_icon = {
        SceneState.EMPTY: "⚪",
        SceneState.IN_PROGRESS: "🔵",
        SceneState.COMPLETE: "✅",
    }[card.state]

    # Add active indicator
    active_indicator = " 👉" if is_active else ""
    warning_badge = f" ⚠️ {len(card.warnings)}" if card.warnings else ""

    # Card header with expander
    with st.expander(
        f"{state_icon} Scene {idx + 1}: {card.title}{active_indicator}{warning_badge}",
        expanded=(is_active or card.state == SceneState.IN_PROGRESS)
    ):
        # Mechanics
        st.markdown("**Mechanics:**")
        if card.mechanics:
            st.caption(", ".join(card.mechanics))
        else:
            st.caption("_Not set_")

        # UI Elements (editable)
        st.markdown("**UI Elements:**")
        if card.ui_elements:
            for key, value in card.ui_elements.items():
                # Inline editing with unique key
                new_value = st.text_input(
                    f"{key}",
                    value=value,
                    key=f"ui_{card.id}_{key}",
                    label_visibility="visible"
                )
                if new_value != value:
                    card.ui_elements[key] = new_value
        else:
            st.caption("_Not set_")

        # Timing
        st.markdown("**Timing:**")
        if card.timing:
            for key, value in card.timing.items():
                # Show with default indicator if using default
                default_text = ""
                if card.is_using_default(f"timing.{key}"):
                    default_val = card.get_default_value(f"timing.{key}")
                    default_text = f" _(using default: {default_val})_"

                # Inline editing for duration
                if key == "duration" and isinstance(value, (int, float)):
                    new_value = st.number_input(
                        f"{key}",
                        value=float(value),
                        min_value=0.0,
                        max_value=30.0,
                        step=0.5,
                        key=f"timing_{card.id}_{key}",
                        help=default_text if default_text else None
                    )
                    if new_value != value:
                        card.timing[key] = new_value
                else:
                    st.caption(f"{key}: {value}{default_text}")
        else:
            st.caption("_Not set_")

        # User Actions
        st.markdown("**User Actions:**")
        if card.user_actions:
            for action in card.user_actions:
                st.caption(f"• {action}")
        else:
            st.caption("_Not set_")

        # Technical (collapsed by default)
        if card.technical:
            with st.expander("Technical Details"):
                st.json(card.technical, expanded=False)

        # Warnings (if any)
        if card.warnings:
            with st.expander(f"⚠️ Warnings ({len(card.warnings)})", expanded=False):
                for warning in card.warnings:
                    severity_color = {
                        "low": "🔵",
                        "medium": "🟡",
                        "high": "🔴"
                    }[warning.severity]
                    st.caption(f"{severity_color} {warning.message}")
                    if warning.suggestion:
                        st.caption(f"   💡 {warning.suggestion}")


# === SIDEBAR ===
with st.sidebar:
    st.header("📁 Files")

    pdf_file = st.file_uploader("PDF ТЗ (optional)", type=["pdf"])
    images = st.file_uploader("Images (required)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

    # Update has_pdf_input state
    if pdf_file:
        st.session_state.has_pdf_input = True
    else:
        st.session_state.has_pdf_input = False

    # Validation logic
    has_spec = st.session_state.has_text_input or st.session_state.has_pdf_input
    has_images = images is not None and len(images) > 0
    can_start = has_spec and has_images

    # Show status
    if pdf_file:
        st.success(f"✅ PDF: {pdf_file.name}")
    if images:
        st.success(f"✅ {len(images)} images")

        # Show thumbnails
        cols = st.columns(min(len(images), 4))
        for i, img in enumerate(images[:4]):
            with cols[i]:
                st.image(img, width=60)

    # Show helpful messages
    if not has_spec and not has_images:
        st.info("📝 Enter text specification OR upload PDF, plus images")
    elif not has_spec:
        st.warning("⚠️ Need specification: enter text OR upload PDF")
    elif not has_images:
        st.warning("⚠️ Need images: upload at least one image")

    if st.button("🚀 Start Analysis", type="primary", use_container_width=True, disabled=not can_start):
        st.session_state.step = "chat"
        st.session_state.messages = []

        # Prepare inputs
        pdf_bytes = pdf_file.read() if pdf_file else None
        text_spec = st.session_state.text_specification.strip() if st.session_state.text_specification else None
        img_bytes = [img.read() for img in images]

        # Reset file pointers
        if pdf_file:
            pdf_file.seek(0)
        for img in images:
            img.seek(0)

        # Initial analysis
        with st.spinner("Analyzing files with AI..."):
            try:
                # CRITICAL: Reset orchestrator to clear old scene_cards and prevent data bleeding
                orch.reset()
                logger.info("Orchestrator reset before new upload")

                sources_msg = []
                if pdf_bytes:
                    sources_msg.append(f"PDF={len(pdf_bytes)} bytes")
                if text_spec:
                    sources_msg.append(f"Text={len(text_spec)} chars")
                logger.info(f"Starting analysis: {', '.join(sources_msg)}, Images={len(img_bytes)}")

                result = run_async(orch.process_files(
                    pdf_bytes=pdf_bytes,
                    images_bytes=img_bytes,
                    text_spec=text_spec
                ))
                logger.info(f"Analysis complete: {result.get('response', '')[:100]}...")

                # SKIP extraction summary - user doesn't need to see it
                # st.session_state.messages.append({"role": "assistant", "content": result["response"]})

                # Initialize ScenarioBuilder immediately
                logger.info(f"Checking brief and assets: brief={orch.context.get('brief') is not None}, assets={orch.context.get('assets') is not None}")
                if orch.context.get("brief") and orch.context.get("assets"):
                    logger.info("Initializing ScenarioBuilder...")
                    try:
                        with st.spinner("Analyzing scenario structure..."):
                            detection_result = orch.init_scenario_builder()
                        logger.info(f"ScenarioBuilder initialized: {len(detection_result.get('scene_cards', []))} scene cards")
                    except Exception as e:
                        logger.error(f"ScenarioBuilder initialization failed: {e}", exc_info=True)
                        st.error(f"Failed to initialize scenario builder: {e}")
                        raise

                    # Update state
                    logger.info("Updating session state...")
                    st.session_state.scenario_initialized = True
                    st.session_state.scene_cards = detection_result["scene_cards"]
                    st.session_state.workflow_stage = "scenario_building"
                    logger.info(f"Session state updated: step={st.session_state.step}, workflow_stage={st.session_state.workflow_stage}")

                    # Show scene detection overview (NOT extraction summary)
                    detection_msg = format_detection_message(detection_result)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": detection_msg
                    })

                    # Get and show first question
                    question_result = orch.get_next_question()
                    if "question" in question_result:
                        from playable_agents.scenario_builder import Question
                        question_obj = Question(**question_result["question"])
                        question_msg = format_question_message(
                            question_obj,
                            question_result["scene_title"]
                        )
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": question_msg
                        })
                        st.session_state.active_question = question_result
                        st.session_state.current_scene_idx = question_result["scene_idx"]
                else:
                    # Fallback if extraction failed
                    st.error("Failed to extract brief or assets. Please try again.")

            except Exception as e:
                logger.error(f"Analysis error: {e}", exc_info=True)
                st.error(f"Error: {e}")

        st.rerun()

    st.divider()

    # Scene Cards Display
    if st.session_state.scene_cards:
        st.markdown("### 🎬 Scenario")

        # Progress indicator
        total_scenes = len(st.session_state.scene_cards)
        completed_scenes = sum(1 for c in st.session_state.scene_cards if c.is_complete())
        st.progress(completed_scenes / total_scenes if total_scenes > 0 else 0)
        st.caption(f"{completed_scenes}/{total_scenes} scenes complete")

        # Render each card
        for idx, card in enumerate(st.session_state.scene_cards):
            render_scene_card(card, idx)

    st.divider()

    if st.session_state.html:
        st.success("✅ Playable Ready!")
        val = validate_html(st.session_state.html)
        st.metric("Size", f"{val.size_kb:.1f} KB")

        st.download_button(
            "📥 Download HTML",
            data=st.session_state.html,
            file_name="index.html",
            mime="text/html",
            use_container_width=True,
            type="primary"
        )

        if st.button("🔄 Start Over"):
            st.session_state.orchestrator = PlayableOrchestrator()
            st.session_state.messages = []
            st.session_state.html = None
            st.session_state.step = "upload"
            st.rerun()


# === MAIN AREA ===
if st.session_state.step == "upload":
    st.info("👈 Upload PDF and/or enter text specification in sidebar to start")

    # Text specification input
    st.subheader("📝 Specification Input")

    col_text1, col_text2 = st.columns(2)
    with col_text1:
        st.markdown("**Option 1: Text Specification**")
        st.markdown("Paste your game specification in free-form text")
    with col_text2:
        st.markdown("**Option 2: PDF Upload**")
        st.markdown("Upload a PDF document with game spec")

    st.markdown("_You can use text OR PDF OR both (they'll be merged intelligently)_")

    # Text area for specification
    text_input = st.text_area(
        "Enter game specification",
        value=st.session_state.text_specification,
        height=300,
        placeholder="""Example:

Epic battle game with 3 tutorial scenes and final boss.

Scenes:
1. Tutorial - Player learns to repair ship by dragging repair modules
2. Battle - Enemy shoots while player fixes damage
3. Tutorial - Setup weapons in grid cells
4. Battle - Cannons shoot enemy ships
5. Tutorial - Merge two cannons to upgrade
6. Final Battle - Upgraded weapons defeat boss
7. Victory - Show rewards and CTA button

UI: "REPAIR YOUR SHIP", "SETUP WEAPONS", "MERGE WEAPONS"
CTA: "TAKE REWARD"
""",
        key="text_spec_input",
        help="Enter your playable ad specification in any format. AI will extract scenes, mechanics, and UI text."
    )

    # Update session state
    if text_input != st.session_state.text_specification:
        st.session_state.text_specification = text_input
        st.session_state.has_text_input = len(text_input.strip()) > 0

    # Show character count
    if text_input:
        char_count = len(text_input)
        st.caption(f"✏️ {char_count} characters")

    st.divider()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("### 1️⃣ Upload")
        st.markdown("PDF ТЗ + game assets (backgrounds, characters, icons)")
    with col2:
        st.markdown("### 2️⃣ Chat")
        st.markdown("Answer agent questions (language, store URLs)")
    with col3:
        st.markdown("### 3️⃣ Download")
        st.markdown("Get ready-to-deploy HTML file")

    st.divider()
    st.markdown("""
    **Supported Networks:** Unity (MRAID 3.0)

    **Features:**
    - PDF parsing with GPT-4
    - Image classification with Gemini Vision
    - Configurable game mechanics
    - MRAID wrapper for ad networks
    - Base64 asset inlining
    - Automatic validation
    """)

elif st.session_state.step == "chat":
    logger.info(f"[PAGE] Rendering CHAT page, workflow_stage={st.session_state.workflow_stage}")
    logger.info(f"[PAGE] scene_cards={len(st.session_state.get('scene_cards', []))} cards, messages={len(st.session_state.messages)}")

    # Progress indicators (top)
    if st.session_state.workflow_stage == "scenario_building" and st.session_state.scene_cards:
        col1, col2, col3 = st.columns([1, 1, 2])

        with col1:
            st.caption("🔨 Building Scenario")

        with col2:
            if st.session_state.scene_cards:
                current = st.session_state.current_scene_idx + 1
                total = len(st.session_state.scene_cards)
                st.metric("Scene", f"{current}/{total}")

        with col3:
            if st.session_state.scene_cards:
                total = len(st.session_state.scene_cards)
                completed = sum(1 for c in st.session_state.scene_cards if c.is_complete())
                st.progress(
                    completed / total if total > 0 else 0,
                    text=f"{completed}/{total} complete"
                )

        st.divider()

    # Chat interface
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # User input
    if prompt := st.chat_input("Your answer..."):
        logger.info(f"[CHAT] User input received: {prompt[:100]}...")
        logger.info(f"[CHAT] Current workflow_stage: {st.session_state.workflow_stage}")

        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Processing..."):
                try:
                    # Route based on workflow stage
                    if st.session_state.workflow_stage == "scenario_building":
                        logger.info("[CHAT] Routing to handle_scenario_answer")
                        response = handle_scenario_answer(prompt, orch)
                        logger.info(f"[CHAT] Response generated: {response[:100]}...")
                    else:
                        # Normal chat mode (shouldn't happen in new flow)
                        logger.info(f"[CHAT] Routing to normal chat mode (stage: {st.session_state.workflow_stage})")
                        result = run_async(orch.chat(prompt))
                        response = result["response"]

                        # Check if PlayableSpec was created (but not HTML yet)
                        if orch.context.get("spec") and not orch.context.get("html"):
                            st.session_state.spec = orch.context.get("spec")
                            st.session_state.step = "scenario_approval"
                            st.info("✨ Scenario generated! Please review and approve.")
                        # Check if HTML was generated
                        elif result.get("html"):
                            st.session_state.html = result["html"]
                            st.success("✅ Playable generated! Check sidebar to download.")

                    st.markdown(response)
                except Exception as e:
                    response = f"Error: {e}"
                    st.error(response)
                    logger.error(f"Chat error: {e}", exc_info=True)

        st.session_state.messages.append({"role": "assistant", "content": response})

        # Check for auto-transition to confirmation before rerun
        if st.session_state.workflow_stage == "confirmation":
            logger.info("[CHAT] Workflow complete, transitioning to confirmation")
            st.session_state.step = "scenario_confirmation"

        logger.info("[CHAT] Calling st.rerun()...")
        st.rerun()

    # Quick action buttons
    st.divider()
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🇬🇧 English"):
            user_msg = "Use English language"
            st.session_state.messages.append({"role": "user", "content": user_msg})
            with st.spinner("Processing..."):
                result = run_async(orch.chat(user_msg))
                st.session_state.messages.append({"role": "assistant", "content": result["response"]})
                if orch.context.get("spec") and not orch.context.get("html"):
                    st.session_state.spec = orch.context.get("spec")
                    st.session_state.step = "scenario_approval"
                elif result.get("html"):
                    st.session_state.html = result["html"]
            st.rerun()

    with col2:
        if st.button("🇷🇺 Russian"):
            user_msg = "Use Russian language"
            st.session_state.messages.append({"role": "user", "content": user_msg})
            with st.spinner("Processing..."):
                result = run_async(orch.chat(user_msg))
                st.session_state.messages.append({"role": "assistant", "content": result["response"]})
                if orch.context.get("spec") and not orch.context.get("html"):
                    st.session_state.spec = orch.context.get("spec")
                    st.session_state.step = "scenario_approval"
                elif result.get("html"):
                    st.session_state.html = result["html"]
            st.rerun()

    with col3:
        if st.button("🚀 Generate Scenario"):
            user_msg = "Generate the playable scenario (spec) now with collected information"
            st.session_state.messages.append({"role": "user", "content": user_msg})
            with st.spinner("Generating scenario..."):
                result = run_async(orch.chat(user_msg))
                st.session_state.messages.append({"role": "assistant", "content": result["response"]})
                if orch.context.get("spec") and not orch.context.get("html"):
                    st.session_state.spec = orch.context.get("spec")
                    st.session_state.step = "scenario_approval"
                elif result.get("html"):
                    st.session_state.html = result["html"]
            st.rerun()
elif st.session_state.step == "scenario_confirmation":
    # NEW: Final confirmation screen for ScenarioBuilder
    st.markdown("## 🎯 Scenario Summary")
    st.caption("Review your scenario before generating HTML")

    # Get scenario summary
    if orch.scenario_builder and orch.context.get("scene_cards"):
        summary = orch.get_scenario_summary()

        # Summary header
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Scenes", summary["total_scenes"])
        with col2:
            st.metric("Completed", summary["completed_scenes"])
        with col3:
            warning_color = "🟢" if summary["total_warnings"] == 0 else "🟡" if summary["critical_warnings"] == 0 else "🔴"
            st.metric("Warnings", f"{warning_color} {summary['total_warnings']}")

        st.divider()

        # Scene list
        st.markdown("### 📋 Scenes")
        for idx, (card, title) in enumerate(zip(orch.context["scene_cards"], summary["scene_titles"])):
            # Scene summary
            state_icon = {
                "empty": "⚪",
                "in_progress": "🔵",
                "complete": "✅"
            }[card.state]

            scene_warnings = [w for w in card.warnings if w]
            warning_text = f" ⚠️ {len(scene_warnings)}" if scene_warnings else ""

            with st.expander(f"{state_icon} Scene {idx + 1}: {title}{warning_text}", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Mechanics:**")
                    if card.mechanics:
                        for m in card.mechanics:
                            st.caption(f"• {m}")
                    else:
                        st.caption("_None_")

                    st.markdown("**UI Elements:**")
                    if card.ui_elements:
                        for k, v in card.ui_elements.items():
                            st.caption(f"• {k}: {v}")
                    else:
                        st.caption("_None_")

                with col2:
                    st.markdown("**Timing:**")
                    if card.timing:
                        for k, v in card.timing.items():
                            st.caption(f"• {k}: {v}")
                    else:
                        st.caption("_None_")

                    st.markdown("**User Actions:**")
                    if card.user_actions:
                        for a in card.user_actions:
                            st.caption(f"• {a}")
                    else:
                        st.caption("_None_")

        # Warnings section
        if summary["total_warnings"] > 0:
            st.divider()
            with st.expander(f"⚠️ {summary['total_warnings']} Warnings", expanded=summary["critical_warnings"] > 0):
                for warning in summary["warnings"]:
                    severity_icon = {
                        "low": "🔵",
                        "medium": "🟡",
                        "high": "🔴"
                    }[warning["severity"]]

                    st.markdown(f"{severity_icon} **{warning['message']}**")
                    if warning.get("suggestion"):
                        st.caption(f"   💡 {warning['suggestion']}")

        st.divider()

        # Action buttons
        col1, col2, col3 = st.columns([1, 1, 2])

        with col1:
            if st.button("✏️ Edit Scenario", use_container_width=True):
                st.session_state.step = "chat"
                st.rerun()

        with col2:
            # Check if ready for generation
            if summary["ready_for_generation"]:
                if st.button("🚀 Generate HTML", type="primary", use_container_width=True):
                    with st.spinner("Generating HTML..."):
                        # Trigger generation
                        result = run_async(orch.generate())
                        if result.get("html"):
                            st.session_state.html = result["html"]
                            st.success("✅ Playable generated!")
                        st.rerun()
            else:
                st.button("🚀 Generate HTML", disabled=True, use_container_width=True, help="Complete all required fields first")

        with col3:
            st.caption("Soft validation warnings don't block generation")

    else:
        st.warning("No scenario data found. Please complete the scenario building process.")
        if st.button("← Back to Chat"):
            st.session_state.step = "chat"
            st.rerun()

elif st.session_state.step == "scenario_approval":
    st.markdown("## 📋 Scenario Review & Approval")
    st.caption("Review the generated playable scenario before HTML generation")

    spec = st.session_state.spec

    if spec:
        # Display scenario in beautiful cards
        col1, col2 = st.columns([2, 1])

        with col1:
            # Meta information
            st.markdown("""
            <div class="scenario-card">
                <div class="scenario-header">📌 Playable Information</div>
                <div class="scenario-content">
            """, unsafe_allow_html=True)

            meta = spec.meta
            st.markdown(f"**Title:** {meta.get('title', 'N/A')}")
            st.markdown(f"**Network:** {meta.get('network', 'N/A')}")
            st.markdown(f"**Language:** {meta.get('language', 'N/A')}")

            st.markdown("</div></div>", unsafe_allow_html=True)

            # Scenes
            st.markdown("""
            <div class="scenario-card">
                <div class="scenario-header">🎬 Scenes ({count})</div>
            """.format(count=len(spec.scenes)), unsafe_allow_html=True)

            for i, scene in enumerate(spec.scenes):
                with st.expander(f"**Scene {i+1}:** {scene.id} ({scene.type})"):
                    st.markdown(f"**Type:** `{scene.type}`")
                    st.markdown(f"**Background:** `{scene.background or 'None'}`")
                    st.markdown(f"**Mechanics:** {len(scene.mechanics)} configured")

                    if scene.ui:
                        st.markdown("**UI Elements:**")
                        st.json(scene.ui)

                    if scene.mechanics:
                        st.markdown("**Mechanics:**")
                        for mech in scene.mechanics:
                            st.markdown(f"- `{mech.type}`")
                            if mech.config:
                                st.json(mech.config)

            st.markdown("</div>", unsafe_allow_html=True)

            # Assets
            st.markdown("""
            <div class="scenario-card">
                <div class="scenario-header">🖼️ Assets</div>
                <div class="scenario-content">
            """, unsafe_allow_html=True)

            assets = spec.assets
            if assets.get('images'):
                st.markdown(f"**Images:** {len(assets['images'])} files")
                for name in list(assets['images'].keys())[:5]:
                    st.markdown(f"- `{name}`")
                if len(assets['images']) > 5:
                    st.markdown(f"... and {len(assets['images']) - 5} more")

            st.markdown("</div></div>", unsafe_allow_html=True)

        with col2:
            st.markdown("""
            <div class="scenario-card">
                <div class="scenario-header">⚙️ Actions</div>
                <div class="scenario-content">
                    Choose what to do with this scenario:
                </div>
            """, unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)

            # Approve button
            if st.button("✅ Approve & Generate HTML", type="primary", use_container_width=True):
                with st.spinner("Generating HTML from approved scenario..."):
                    try:
                        user_msg = "The scenario is approved. Please render the HTML now."
                        st.session_state.messages.append({"role": "user", "content": user_msg})
                        result = run_async(orch.chat(user_msg))
                        st.session_state.messages.append({"role": "assistant", "content": result["response"]})

                        if result.get("html"):
                            st.session_state.html = result["html"]
                            st.session_state.step = "chat"
                            st.success("✅ HTML generated successfully!")
                        else:
                            st.error("Failed to generate HTML. Check the logs.")
                    except Exception as e:
                        st.error(f"Error: {e}")
                        logger.error(f"HTML generation error: {e}", exc_info=True)
                st.rerun()

            st.markdown("<br>", unsafe_allow_html=True)

            # Edit mode toggle
            if st.button("✏️ Edit Scenario", use_container_width=True):
                st.session_state.edit_mode = not st.session_state.edit_mode
                st.rerun()

            st.markdown("<br>", unsafe_allow_html=True)

            # Think harder button
            if st.button("🧠 Think Harder", use_container_width=True):
                with st.spinner("Re-thinking the scenario with deeper analysis..."):
                    try:
                        user_msg = "Please re-think and improve the scenario. Consider better mechanics, more engaging flow, and optimal asset usage. Generate an improved scenario."
                        st.session_state.messages.append({"role": "user", "content": user_msg})

                        # Reset spec so it regenerates
                        orch.context["spec"] = None

                        result = run_async(orch.chat(user_msg))
                        st.session_state.messages.append({"role": "assistant", "content": result["response"]})

                        if orch.context.get("spec"):
                            st.session_state.spec = orch.context.get("spec")
                            st.success("✨ Scenario improved!")
                        else:
                            st.info("Agent is still working on improvements. Check the chat.")
                    except Exception as e:
                        st.error(f"Error: {e}")
                        logger.error(f"Think harder error: {e}", exc_info=True)
                st.rerun()

            st.markdown("<br>", unsafe_allow_html=True)

            # Back to chat
            if st.button("💬 Back to Chat", use_container_width=True):
                st.session_state.step = "chat"
                st.rerun()

        # Edit mode
        if st.session_state.edit_mode:
            st.divider()
            st.markdown("### ✏️ Edit Scenario (JSON)")
            st.caption("Advanced: Edit the raw PlayableSpec JSON. Be careful with the structure!")

            # Convert spec to JSON for editing
            if not st.session_state.spec_text:
                st.session_state.spec_text = spec.model_dump_json(indent=2)

            edited_spec = st.text_area(
                "Edit JSON",
                value=st.session_state.spec_text,
                height=400,
                key="spec_editor"
            )

            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("💾 Save Changes", type="primary"):
                    try:
                        from models import PlayableSpec
                        new_spec = PlayableSpec.model_validate_json(edited_spec)
                        st.session_state.spec = new_spec
                        st.session_state.spec_text = edited_spec
                        orch.context["spec"] = new_spec
                        st.success("✅ Changes saved!")
                        st.session_state.edit_mode = False
                        st.rerun()
                    except Exception as e:
                        st.error(f"Invalid JSON: {e}")

            with col_b:
                if st.button("❌ Cancel"):
                    st.session_state.edit_mode = False
                    st.session_state.spec_text = None
                    st.rerun()
    else:
        st.warning("No scenario found. Please go back to chat and generate one.")
        if st.button("💬 Back to Chat"):
            st.session_state.step = "chat"
            st.rerun()


# Preview section (if HTML available)
if st.session_state.html:
    with st.expander("👁️ Preview Playable", expanded=True):
        # Download button in preview section
        st.download_button(
            label="📥 Download HTML",
            data=st.session_state.html,
            file_name="index.html",
            mime="text/html",
            type="primary",
            use_container_width=False
        )

        st.components.v1.html(st.session_state.html, height=600, scrolling=False)

        # Validation info
        val = validate_html(st.session_state.html)
        if val.valid:
            st.success(f"✅ Validation passed ({val.size_kb:.1f} KB)")
        else:
            st.error("❌ Validation issues:")
            for e in val.errors:
                st.error(f"• {e}")

        if val.warnings:
            for w in val.warnings:
                st.warning(f"• {w}")
