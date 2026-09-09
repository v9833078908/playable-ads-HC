"""
Orchestrator V2 — LLM-Agent with Tools for Playable Ad Generation

The orchestrator is an autonomous Claude agent that:
1. Analyzes specs and generates assets via sub-agents
2. Generates HTML and SEES its output through Playwright screenshots
3. Evaluates quality via Gemini Vision with numerical scoring
4. Iteratively patches or regenerates to hit score >= 7
5. Saves successful patterns to generation memory

Uses Anthropic Python SDK: @beta_async_tool, @beta_tool, tool_runner
Sub-agents (scenario, generator, asset_generator) remain on OpenAI Agents SDK.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Optional

import anthropic
from anthropic import beta_async_tool

from .html_file_manager import HTMLFileManager
from .memory_manager import MemoryManager
from .error_classifier import classify_error, ErrorType, get_backoff_delay

logger = logging.getLogger('OrchestratorV2')

# Safety limits for tool outputs
MAX_TOOL_OUTPUT_CHARS = 30_000  # ~7.5K tokens max per tool result (cost optimization)
MAX_READ_LINES = 200  # Max lines per read_html_section call


def _truncate_output(text: str, label: str = "output") -> str:
    """Truncate tool output if it exceeds safety limit."""
    if len(text) > MAX_TOOL_OUTPUT_CHARS:
        truncated = text[:MAX_TOOL_OUTPUT_CHARS]
        logger.warning(f"Tool {label} truncated: {len(text)} → {MAX_TOOL_OUTPUT_CHARS} chars")
        return truncated + f"\n\n... [TRUNCATED: {len(text) - MAX_TOOL_OUTPUT_CHARS} chars removed. Use smaller ranges.]"
    return text


# Load prompts
PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_prompt(name: str) -> str:
    prompt_path = PROMPTS_DIR / f"{name}.md"
    if prompt_path.exists():
        return prompt_path.read_text()
    return ""


# Shared state accessible by tools via closure
class OrchestratorContext:
    """Shared state for orchestrator tools."""

    def __init__(self):
        from .memory_store import MemoryStore
        self.memory_store = MemoryStore()
        self.html_manager = HTMLFileManager(output_dir="output")
        self.memory_manager = MemoryManager(memory_dir="memory")
        self.iteration = 0
        self.max_iterations = 7
        self.baseline_score = None
        self.best_score = None
        self.best_version = None
        self.improvement_log = []
        self.successful_patterns = []
        self.failed_approaches = []


# ═══════════════════════════════════════════════════════════════════
# TOOL FACTORY: Creates tools bound to OrchestratorContext via closure
# ═══════════════════════════════════════════════════════════════════

def _create_tools(orch_ctx: OrchestratorContext):
    """Create tool closures bound to the given orchestrator context."""

    # ─── Group 1: Pipeline tools (sub-agent calls) ───

    @beta_async_tool
    async def analyze_spec(spec_text: str, references: str = "") -> str:
        """Analyze spec to create scene_spec and asset_list.

        Args:
            spec_text: The technical specification text to analyze
            references: Optional JSON string of style references
        """
        from .scenario_agent import scenario_agent
        from agents import Runner

        orch_ctx.memory_store.set("spec_text", spec_text)
        if references:
            orch_ctx.memory_store.set(
                "style_references",
                json.loads(references) if references.startswith("{") else {},
            )

        agent_ctx = {"memory_store": orch_ctx.memory_store}

        try:
            await Runner.run(
                scenario_agent,
                input="Analyze the specification. Call analyze_spec() and create_asset_list().",
                context=agent_ctx,
            )

            scene_spec = orch_ctx.memory_store.get("scene_spec")
            asset_list = orch_ctx.memory_store.get("asset_list")

            summary = f"Spec analyzed: genre={scene_spec.get('genre', '?')}, "
            summary += f"mechanics={scene_spec.get('mechanics', [])}, "
            summary += f"scenes={len(scene_spec.get('scenes', []))}, "
            summary += f"assets={len(asset_list or [])}"
            return summary

        except Exception as e:
            return f"Error analyzing spec: {e}"

    @beta_async_tool
    async def generate_assets() -> str:
        """Generate visual assets using FAL API."""
        from .asset_generator_agent import asset_generator_agent
        from agents import Runner

        agent_ctx = {"memory_store": orch_ctx.memory_store}

        try:
            await Runner.run(
                asset_generator_agent,
                input="Map reference assets and generate missing ones. Call use_reference_assets() then generate_missing_assets().",
                context=agent_ctx,
            )

            manifest = orch_ctx.memory_store.get("asset_manifest") or {}
            return f"Assets ready: {len(manifest)} total"

        except Exception as e:
            return f"Error generating assets: {e}"

    @beta_async_tool
    async def generate_html(instructions: str = "", memory_hints: str = "") -> str:
        """Generate HTML using Generator Agent (Claude).

        Args:
            instructions: Additional generation instructions
            memory_hints: Best practices from generation memory
        """
        from .generator_agent import generator_agent
        from agents import Runner

        if memory_hints:
            orch_ctx.memory_store.set("memory_hints", memory_hints)
        if instructions:
            orch_ctx.memory_store.set("generation_instructions", instructions)

        agent_ctx = {"memory_store": orch_ctx.memory_store}

        try:
            gen_input = "Generate the HTML playable ad. Call generate_html()."
            if instructions:
                gen_input += f"\n\nAdditional instructions: {instructions}"

            await Runner.run(
                generator_agent,
                input=gen_input,
                context=agent_ctx,
            )

            html = orch_ctx.memory_store.get_latest_html()
            if html:
                version_info = orch_ctx.html_manager.save_html(html)
                size_kb = version_info["size_kb"]
                version = version_info["version"]
                return f"HTML generated: v{version}, {size_kb:.1f}KB, {orch_ctx.html_manager.get_total_lines()} lines"
            else:
                return "Error: Generator produced no HTML"

        except Exception as e:
            error_info = classify_error(e)
            return f"Error generating HTML ({error_info['type'].value}): {e}"

    # ─── Group 2: Visual feedback tools ───

    @beta_async_tool
    async def take_screenshots() -> str:
        """Take Playwright screenshots of the current HTML in all game states."""
        from .screenshot_tool import take_screenshots as _take_screenshots

        html_path = orch_ctx.html_manager.current_path

        if not html_path:
            return "Error: No HTML file to screenshot"

        scene_spec = orch_ctx.memory_store.get("scene_spec") or {}

        try:
            screenshots = await _take_screenshots(str(html_path), scene_spec)

            orch_ctx.memory_store.set("latest_screenshots", screenshots)

            valid = [s for s in screenshots if s.get("screenshot_base64")]
            errors = [s for s in screenshots if s.get("error")]

            summary = f"Screenshots taken: {len(valid)} successful"
            if errors:
                summary += f", {len(errors)} failed"
            summary += f"\nStates: {', '.join(s['state_name'] for s in valid)}"
            return summary

        except Exception as e:
            error_info = classify_error(e)
            return f"Screenshot error ({error_info['type'].value}): {e}"

    @beta_async_tool
    async def evaluate_visual() -> str:
        """Evaluate screenshots with Gemini Vision, returns scores and suggested action."""
        from services.gemini_client import gemini_client
        import PIL.Image
        import io
        import base64

        screenshots = orch_ctx.memory_store.get("latest_screenshots") or []

        if not screenshots:
            return '{"error": "No screenshots. Call take_screenshots first."}'

        valid_screenshots = [s for s in screenshots if s.get("screenshot_base64")]
        if not valid_screenshots:
            return '{"error": "All screenshots failed. Check HTML for JS errors."}'

        visual_qa_prompt = _load_prompt("visual_qa")
        quality_rubric = _load_prompt("quality_rubric")

        scene_spec = orch_ctx.memory_store.get("scene_spec") or {}

        prompt = f"""{visual_qa_prompt}

## Quality Rubric
{quality_rubric}

## Scene Specification
```json
{json.dumps(scene_spec, indent=2)}
```

## Screenshots
You are evaluating {len(valid_screenshots)} screenshots of the playable ad:
{', '.join(s['state_name'] for s in valid_screenshots)}

Analyze ALL screenshots and return scores as specified in the output format.
Return ONLY valid JSON."""

        try:
            contents = [prompt]

            for s in valid_screenshots:
                b64 = s["screenshot_base64"]
                img_bytes = base64.b64decode(b64)
                image = PIL.Image.open(io.BytesIO(img_bytes))
                contents.append(image)

            response = gemini_client.client.models.generate_content(
                model=gemini_client.model_name,
                contents=contents,
            )

            result = gemini_client._parse_json(response.text)

            overall = result.get("overall", 0)
            orch_ctx.iteration += 1

            if orch_ctx.html_manager.versions:
                current_version = orch_ctx.html_manager.versions[-1]["version"]
                orch_ctx.html_manager.update_scores(current_version, result.get("scores", {}))
                orch_ctx.html_manager.versions[-1]["scores"]["overall"] = overall

            if orch_ctx.baseline_score is None:
                orch_ctx.baseline_score = overall
            if orch_ctx.best_score is None or overall > orch_ctx.best_score:
                orch_ctx.best_score = overall
                orch_ctx.best_version = orch_ctx.html_manager.version_count

            orch_ctx.improvement_log.append({
                "iteration": orch_ctx.iteration,
                "score": overall,
                "action": "evaluate",
            })

            scores = result.get("scores", {})
            improvements = result.get("priority_improvements") or result.get("improvements") or []
            top_improvements = improvements[:3] if improvements else []

            if overall >= 7:
                action = "DONE - score is sufficient, call save_to_memory"
            elif orch_ctx.iteration >= 7:
                action = "MAX_ITERATIONS - stop and save_to_memory"
            elif overall < (orch_ctx.baseline_score or 0):
                action = "ROLLBACK - score dropped, call rollback_html and try different approach"
            else:
                action = "PATCH - use read_html_section + replace_html_section to fix top issues"

            summary = {
                "overall": overall,
                "scores": scores,
                "baseline": orch_ctx.baseline_score,
                "iteration": orch_ctx.iteration,
                "suggested_action": action,
                "top_improvements": [
                    {
                        "category": imp.get("category", "unknown"),
                        "issue": (imp.get("issue") or imp.get("description", ""))[:100]
                    }
                    for imp in top_improvements
                ],
            }

            return json.dumps(summary, indent=2)

        except Exception as e:
            error_info = classify_error(e)
            return json.dumps({"error": f"Vision evaluation failed ({error_info['type'].value}): {e}"})

    @beta_async_tool
    async def run_technical_qa() -> str:
        """Run technical QA checks on current HTML."""
        from .technical_qa_agent import _check_size, _check_touch_events, _check_mraid, _check_viewport, _check_game_loop

        html = orch_ctx.html_manager.read_current()

        if not html:
            return '{"passed": false, "issues": [{"description": "No HTML to check"}]}'

        scene_spec = orch_ctx.memory_store.get("scene_spec") or {}

        size = _check_size(html)
        touch = _check_touch_events(html)
        mraid = _check_mraid(html, scene_spec)
        viewport = _check_viewport(html)
        game_loop = _check_game_loop(html)

        all_issues = []
        for check_name, result in [("size", size), ("touch", touch), ("mraid", mraid), ("viewport", viewport), ("game_loop", game_loop)]:
            for issue in result.get("issues", []):
                all_issues.append({"category": check_name, "description": issue})
            if result.get("issue"):
                all_issues.append({"category": check_name, "description": result["issue"]})

        passed = all(r.get("passed", False) for r in [size, touch, mraid, viewport, game_loop])

        return json.dumps({
            "passed": passed,
            "issues": all_issues,
            "size_kb": size.get("size_kb"),
        }, indent=2)

    # ─── Group 3: HTML surgery tools ───

    @beta_async_tool
    async def read_html_section(start_line: int, end_line: int) -> str:
        """Read a section of current HTML by line range (1-based, inclusive). Max 500 lines per call.

        Args:
            start_line: First line to read (1-based)
            end_line: Last line to read (1-based, inclusive). Capped at start_line + 499.
        """
        # Enforce max range
        if end_line - start_line + 1 > MAX_READ_LINES:
            end_line = start_line + MAX_READ_LINES - 1
            logger.info(f"read_html_section: capped range to {start_line}-{end_line}")

        section = orch_ctx.html_manager.read_section(start_line, end_line)
        if section is None:
            return "Error: No HTML file or invalid line range"

        total = orch_ctx.html_manager.get_total_lines()
        result = f"Lines {start_line}-{end_line} of {total}:\n\n{section}"
        return _truncate_output(result, "read_html_section")

    @beta_async_tool
    async def replace_html_section(start_line: int, end_line: int, new_code: str) -> str:
        """Replace lines start_line..end_line with new_code. Creates new version.

        Args:
            start_line: First line to replace (1-based)
            end_line: Last line to replace (1-based, inclusive)
            new_code: The replacement code
        """
        result = orch_ctx.html_manager.replace_section(start_line, end_line, new_code)

        if "error" in result:
            return f"Error: {result['error']}"

        html = orch_ctx.html_manager.read_current()
        if html:
            orch_ctx.memory_store.append_html_version(html)

        validation = orch_ctx.html_manager.validate_syntax()
        if not validation["valid"]:
            issues = "; ".join(validation["issues"][:3])
            return f"Replaced lines {start_line}-{end_line} → v{result['version']} ({result['size_kb']:.1f}KB). WARNING: Syntax issues: {issues}"

        return f"Replaced lines {start_line}-{end_line} → v{result['version']} ({result['size_kb']:.1f}KB). Syntax OK."

    @beta_async_tool
    async def search_html(query: str) -> str:
        """Search for text in current HTML, returns matching lines.

        Args:
            query: Text to search for
        """
        results = orch_ctx.html_manager.search_in_html(query)

        if not results:
            return f"No matches found for '{query}'"

        lines = [f"Found {len(results)} matches for '{query}':"]
        for r in results[:15]:
            lines.append(f"  Line {r['line']}: {r['content'][:200]}")
        if len(results) > 15:
            lines.append(f"  ... and {len(results) - 15} more")

        return _truncate_output("\n".join(lines), "search_html")

    @beta_async_tool
    async def validate_syntax() -> str:
        """Validate HTML syntax of current file."""
        result = orch_ctx.html_manager.validate_syntax()

        if result["valid"]:
            return "Syntax validation: PASSED"

        return f"Syntax validation: FAILED\nIssues:\n" + "\n".join(f"- {i}" for i in result["issues"])

    @beta_async_tool
    async def rollback_html(version: int = 0) -> str:
        """Rollback to a previous HTML version. Pass 0 for best version.

        Args:
            version: Version number to rollback to, or 0 for best version
        """
        result = orch_ctx.html_manager.rollback(version if version > 0 else None)

        if "error" in result:
            return f"Rollback error: {result['error']}"

        return f"Rolled back → v{result['version']} ({result['size_kb']:.1f}KB)"

    @beta_async_tool
    async def get_version_history() -> str:
        """Get version history with scores for tracking progress."""
        history = orch_ctx.html_manager.get_version_history()

        if not history:
            return "No versions yet."

        lines = ["Version History:"]
        for v in history:
            score_str = f"score={v['overall']}" if v.get('overall') else "no score"
            lines.append(f"  v{v['version']}: {v['size_kb']:.0f}KB, {score_str}")

        lines.append(f"\nBaseline: {orch_ctx.baseline_score}, Best: {orch_ctx.best_score} (v{orch_ctx.best_version})")
        lines.append(f"Iteration: {orch_ctx.iteration}/{orch_ctx.max_iterations}")

        return "\n".join(lines)

    # ─── Group 4: Memory & utility tools ───

    @beta_async_tool
    async def search_memory(query: str) -> str:
        """Search generation memory for best practices from past runs.

        Args:
            query: Search query for generation memory
        """
        genre = (orch_ctx.memory_store.get("scene_spec") or {}).get("genre", "")

        results = orch_ctx.memory_manager.search_memory(query, genre=genre)

        if not results:
            practices = orch_ctx.memory_manager.get_best_practices(genre)
            if practices:
                return f"No exact matches, but found genre best practices:\n{practices}"
            return "No generation memory found. This will be the first run for this genre."

        lines = [f"Found {len(results)} relevant memories:"]
        for r in results:
            lines.append(f"\n--- Score {r['score']} ---")
            for section in r.get("sections", [])[:2]:
                lines.append(section[:300])

        return "\n".join(lines)

    @beta_async_tool
    async def save_to_memory(successful_patterns: str, failed_approaches: str) -> str:
        """Save generation experience to memory for future runs. Call after achieving score >= 7.

        Args:
            successful_patterns: JSON array of pattern strings that worked
            failed_approaches: JSON array of approach strings that failed
        """
        genre = (orch_ctx.memory_store.get("scene_spec") or {}).get("genre", "unknown")

        try:
            patterns = json.loads(successful_patterns) if successful_patterns.startswith("[") else [successful_patterns]
        except json.JSONDecodeError:
            patterns = [successful_patterns]

        try:
            failed = json.loads(failed_approaches) if failed_approaches.startswith("[") else [failed_approaches]
        except json.JSONDecodeError:
            failed = [failed_approaches]

        best = orch_ctx.html_manager.get_best_version()
        scores = best.get("scores", {}) if best else {}

        filepath = orch_ctx.memory_manager.save_memory(
            genre=genre,
            scores=scores,
            successful_patterns=patterns,
            failed_approaches=failed,
            improvement_log=orch_ctx.improvement_log,
            iterations=orch_ctx.iteration,
        )

        return f"Memory saved: {filepath}"

    @beta_async_tool
    async def get_status() -> str:
        """Get current orchestrator status: iteration, scores, version info."""
        lines = [
            f"Iteration: {orch_ctx.iteration}/{orch_ctx.max_iterations}",
            f"Baseline score: {orch_ctx.baseline_score}",
            f"Best score: {orch_ctx.best_score} (v{orch_ctx.best_version})",
            f"Versions: {orch_ctx.html_manager.version_count}",
        ]

        if orch_ctx.html_manager.current_path:
            lines.append(f"Current file: {orch_ctx.html_manager.current_path}")
            lines.append(f"Total lines: {orch_ctx.html_manager.get_total_lines()}")

        return "\n".join(lines)

    # Return all tools
    return [
        # Group 1: Pipeline
        analyze_spec,
        generate_assets,
        generate_html,
        # Group 2: Visual feedback
        take_screenshots,
        evaluate_visual,
        run_technical_qa,
        # Group 3: HTML surgery
        read_html_section,
        replace_html_section,
        search_html,
        validate_syntax,
        rollback_html,
        get_version_history,
        # Group 4: Memory & utility
        search_memory,
        save_to_memory,
        get_status,
    ]


# ═══════════════════════════════════════════════════════════════════
# CONVENIENCE: run_orchestrator() for simple invocation
# ═══════════════════════════════════════════════════════════════════

async def run_orchestrator(
    spec_text: str,
    reference_assets: Optional[dict] = None,
    output_dir: str = "output",
    memory_dir: str = "memory",
    resume: bool = False,
) -> dict:
    """
    Run the orchestrator V2 pipeline end-to-end.

    Args:
        spec_text: Technical specification text
        reference_assets: Optional dict {name: base64_data_uri}
        output_dir: Directory for HTML output files
        memory_dir: Directory for generation memory
        resume: If True, skip generation if HTML v1 already exists

    Returns:
        {success, html, html_path, scores, iterations, version_history}
    """
    # Create context
    orch_ctx = OrchestratorContext()
    orch_ctx.html_manager = HTMLFileManager(output_dir=output_dir)
    orch_ctx.memory_manager = MemoryManager(memory_dir=memory_dir)

    # Pre-populate memory store
    orch_ctx.memory_store.set("spec_text", spec_text)
    if reference_assets:
        orch_ctx.memory_store.set("reference_assets", reference_assets)

    # Check for resume mode — reuse existing HTML
    existing_html = None
    if resume:
        v1_path = Path(output_dir) / "output_v1.html"
        if v1_path.exists():
            existing_html = v1_path.read_text(encoding='utf-8')
            size_kb = len(existing_html.encode('utf-8')) / 1024
            orch_ctx.html_manager.save_html(existing_html)
            logger.info(f"Resuming from existing HTML v1: {size_kb:.1f}KB")

    # Create tools bound to this context
    tools = _create_tools(orch_ctx)

    # Build system prompt
    orchestrator_prompt = _load_prompt("orchestrator")
    quality_rubric = _load_prompt("quality_rubric")
    system_prompt = f"""{orchestrator_prompt}

## Quality Rubric Reference
{quality_rubric}
"""

    # Build input message
    if existing_html:
        input_msg = f"""Resume improving a playable ad. HTML v1 already exists ({len(existing_html)//1024}KB).

Skip analyze_spec, generate_assets, and generate_html — they are already done.

Start directly with the improvement loop:
1. Call take_screenshots to see current state
2. Call evaluate_visual to score it
3. Based on scores, use read_html_section + replace_html_section to improve weak areas
4. LOOP: take_screenshots → evaluate_visual → patch until score >= 7 or 5 iterations
5. Call save_to_memory with what worked

Specification (for context):
{spec_text[:2000]}"""
    else:
        input_msg = f"""Generate a high-quality playable ad from this specification.

Follow the workflow:
1. Call analyze_spec with the spec text
2. Call generate_assets
3. Call search_memory for best practices
4. Call generate_html
5. LOOP: take_screenshots → evaluate_visual → patch/regenerate until score >= 7 or max iterations
6. Call save_to_memory with what worked

Specification:
{spec_text[:3000]}"""

    # Run with Anthropic tool_runner (high retries for 30K/min rate limit)
    client = anthropic.AsyncAnthropic(max_retries=10)

    try:
        runner = client.beta.messages.tool_runner(
            model="claude-sonnet-4-5-20250929",
            max_tokens=8192,
            system=system_prompt,
            tools=tools,
            messages=[{"role": "user", "content": input_msg}],
            # Server-side context editing: clear old tool results when context grows
            betas=["context-management-2025-06-27"],
            context_management={
                "edits": [
                    {
                        "type": "clear_tool_uses_20250919",
                        "trigger": {
                            "type": "input_tokens",
                            "value": 40000,  # Trigger early — HTML sections are large
                        },
                        "keep": {
                            "type": "tool_uses",
                            "value": 3,
                        },
                        "clear_at_least": {
                            "type": "input_tokens",
                            "value": 15000,
                        },
                    }
                ]
            },
            # Client-side compaction disabled — SDK bug with parsed_output in BetaAsyncFunctionTool
            # Rely on server-side context_management + tool output truncation instead
            # compaction_control={"enabled": True, ...},
            max_iterations=60,
        )

        # Iterate through the tool runner with rate-limit pacing
        final_message = None
        turn_count = 0
        async for message in runner:
            turn_count += 1
            # Log token usage
            usage = message.usage
            cache_read = getattr(usage, 'cache_read_input_tokens', 0) or 0
            cache_create = getattr(usage, 'cache_creation_input_tokens', 0) or 0
            logger.info(
                f"Turn {turn_count}: input={usage.input_tokens}, output={usage.output_tokens}, "
                f"cache_read={cache_read}, cache_create={cache_create}"
            )
            # Log tool calls for debugging
            for block in message.content:
                if hasattr(block, 'type') and block.type == 'tool_use':
                    logger.info(f"  Tool call: {block.name}")
            final_message = message

        # Get best HTML
        best = orch_ctx.html_manager.get_best_version()
        html_path = best["path"] if best else None

        html = None
        if html_path:
            html = Path(html_path).read_text(encoding='utf-8')

        # Extract final text from Claude's last message
        agent_output = ""
        if final_message:
            for block in final_message.content:
                if hasattr(block, 'text'):
                    agent_output += block.text

        return {
            "success": True,
            "html": html,
            "html_path": html_path,
            "scores": best.get("scores", {}) if best else {},
            "iterations": orch_ctx.iteration,
            "version_history": orch_ctx.html_manager.get_version_history(),
            "agent_output": agent_output,
        }

    except Exception as e:
        logger.error(f"Orchestrator failed: {e}", exc_info=True)

        # Try to return best version even on failure
        best = orch_ctx.html_manager.get_best_version()
        html = None
        if best:
            html_path = best["path"]
            html = Path(html_path).read_text(encoding='utf-8')

        return {
            "success": False,
            "error": str(e),
            "html": html,
            "html_path": best.get("path") if best else None,
            "iterations": orch_ctx.iteration,
            "version_history": orch_ctx.html_manager.get_version_history(),
        }
