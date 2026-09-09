# Migrate Orchestrator from OpenAI Agents SDK to Anthropic Python SDK

## Context

Orchestrator V2 (все 12 задач реализованы) работает, но упирается в архитектурное ограничение OpenAI Agents SDK: на каждый turn отправляется ПОЛНАЯ история + 15 tool definitions. При HTML-surgery (read_html_section, search_html) контекст быстро растёт:
- 624K токенов → оптимизировали до 36K → всё равно > 30K TPM лимит gpt-4.1
- Improvement loop невозможен: оркестратор оценивает скриншоты (score=2.8), начинает патчить HTML, и вылетает по rate limit

**Решение**: Мигрировать оркестратор на Anthropic Python SDK с beta tool_runner:
- 200K контекстное окно (vs 30K TPM OpenAI)
- Server-side `clear_tool_uses_20250919` — автоочистка старых tool results
- Client-side compaction — суммаризация при переполнении
- Claude лучше подходит для многоходовых tool-use задач

Sub-agents (scenario, generator, asset_generator) остаются на OpenAI Agents SDK — у них нет проблемы накопления контекста.

## Files to Modify

| File | Action | Description |
|------|--------|-------------|
| `requirements.txt` | ADD line | `anthropic>=0.52.0` |
| `playable_agents/orchestrator.py` | REWRITE | OpenAI → Anthropic SDK |
| `playable_agents/__init__.py` | EDIT | Remove `orchestrator_agent` export |
| `tests/test_real_pipeline.py` | MINOR | Add anthropic logging |

Files NOT changed: scenario_agent, generator_agent, asset_generator_agent, html_file_manager, memory_manager, screenshot_tool, error_classifier, prompts/*, services/*

## Step 1: Update requirements.txt

Add `anthropic>=0.52.0` to the AI/Agents section. Keep `openai-agents` for sub-agents.

## Step 2: Rewrite orchestrator.py — Imports

**Remove:**
```python
from agents import Agent, function_tool, RunContextWrapper, Runner
```

**Add:**
```python
import anthropic
from anthropic import beta_async_tool, beta_tool
```

Keep all other imports (json, logging, Path, HTMLFileManager, MemoryManager, classify_error).

## Step 3: Keep OrchestratorContext unchanged

`OrchestratorContext` (lines 39-54) has no OpenAI SDK dependency. Keep as-is.

## Step 4: Rewrite tools as closure factory

Replace 15 `@function_tool` functions with a single factory `_create_tools(orch_ctx)`:

```python
def _create_tools(orch_ctx: OrchestratorContext):
    """Create tool closures bound to the given context."""

    @beta_async_tool
    async def analyze_spec(spec_text: str, references: str = "") -> str:
        """Analyze spec to create scene_spec and asset_list.

        Args:
            spec_text: Technical specification text
            references: Optional JSON string of style references
        """
        from .scenario_agent import scenario_agent
        from agents import Runner  # sub-agent still on OpenAI SDK

        orch_ctx.memory_store.set("spec_text", spec_text)
        # ... rest of body, replace ctx.context → orch_ctx ...
        result = await Runner.run(scenario_agent, input="...", context={"memory_store": orch_ctx.memory_store})
        # ...
        return summary

    # ... 14 more tools ...

    return [analyze_spec, generate_assets, generate_html,
            take_screenshots, evaluate_visual, run_technical_qa,
            read_html_section, replace_html_section, search_html,
            validate_syntax, rollback_html, get_version_history,
            search_memory, save_to_memory, get_status]
```

**Key pattern** for each tool:
- Remove `ctx: RunContextWrapper[OrchestratorContext]` parameter
- Replace `orch = ctx.context` with direct `orch_ctx` (captured by closure)
- Async tools → `@beta_async_tool`, sync tools → `@beta_tool`
- Google-style docstring with `Args:` section for parameter descriptions
- Sub-agent calls (`Runner.run()`) stay as-is, import `Runner` locally

**Tool decorators:**
- `@beta_async_tool`: analyze_spec, generate_assets, generate_html, take_screenshots, evaluate_visual, run_technical_qa
- `@beta_tool`: read_html_section, replace_html_section, search_html, validate_syntax, rollback_html, get_version_history, search_memory, save_to_memory, get_status

## Step 5: Remove orchestrator_agent global

Delete the `Agent()` definition (lines 560-599) and the module-level `ALL_TOOLS` list. System prompt loading moves into `run_orchestrator()`.

## Step 6: Rewrite run_orchestrator() — The Core

```python
async def run_orchestrator(
    spec_text: str,
    reference_assets: Optional[dict] = None,
    output_dir: str = "output",
    memory_dir: str = "memory",
    resume: bool = False,
) -> dict:
    # 1. Create context (unchanged)
    orch_ctx = OrchestratorContext()
    orch_ctx.html_manager = HTMLFileManager(output_dir=output_dir)
    orch_ctx.memory_manager = MemoryManager(memory_dir=memory_dir)
    orch_ctx.memory_store.set("spec_text", spec_text)
    if reference_assets:
        orch_ctx.memory_store.set("reference_assets", reference_assets)

    # 2. Resume mode (unchanged)
    existing_html = None
    if resume:
        v1_path = Path(output_dir) / "output_v1.html"
        if v1_path.exists():
            existing_html = v1_path.read_text(encoding='utf-8')
            orch_ctx.html_manager.save_html(existing_html)

    # 3. Create tools via closure factory
    tools = _create_tools(orch_ctx)

    # 4. Build system prompt
    system_prompt = f"{_load_prompt('orchestrator')}\n\n## Quality Rubric\n{_load_prompt('quality_rubric')}"

    # 5. Build input message (same logic for resume vs full)
    input_msg = ...  # same as current

    # 6. Run with Anthropic tool_runner
    client = anthropic.AsyncAnthropic()

    runner = await client.beta.messages.tool_runner(
        model="claude-sonnet-4-5-20250929",
        max_tokens=8192,
        system=system_prompt,
        tools=tools,
        messages=[{"role": "user", "content": input_msg}],
        betas=["context-management-2025-06-27"],
        context_management={
            "edits": [{
                "type": "clear_tool_uses_20250919",
                "trigger": {"type": "input_tokens", "value": 80000},
                "keep": {"type": "tool_uses", "value": 5},
                "clear_at_least": {"type": "input_tokens", "value": 10000},
            }]
        },
        compaction_control={
            "enabled": True,
            "context_token_threshold": 150000,
            "model": "claude-haiku-4-5",
        },
        max_iterations=60,
    )

    final_message = None
    async for message in runner:
        logger.info(f"Turn: in={message.usage.input_tokens}, out={message.usage.output_tokens}")
        final_message = message

    # 7. Extract results (same as current)
    best = orch_ctx.html_manager.get_best_version()
    # ... return dict ...
```

## Step 7: Update __init__.py

```python
# Line 11: Remove orchestrator_agent
from .orchestrator import run_orchestrator, OrchestratorContext

# Line 29: Remove from __all__
# "orchestrator_agent",  ← delete
```

## Step 8: Update test_real_pipeline.py

Add after line 29:
```python
logging.getLogger('anthropic').setLevel(logging.INFO)
```

No other changes — `run_orchestrator()` API is unchanged.

## Context Management Strategy

**Layer 1 — Server-side tool clearing (primary):**
- Trigger at 80K input tokens
- Keep last 5 tool uses
- Clear at least 10K tokens per activation
- Handles the main problem: accumulated read_html_section/search_html outputs

**Layer 2 — Client-side compaction (safety net):**
- Trigger at 150K tokens (if Layer 1 can't keep up)
- Uses claude-haiku-4-5 for cheaper summarization
- Custom summary preserving: scores, iteration, approach history, failures
- Full conversation replaced with structured summary

## Risks & Mitigations

1. **@beta_async_tool + closures**: If decorator breaks on closures, fallback to module-level `_ctx` variable
2. **Nested async (Runner.run inside tool inside tool_runner)**: Should chain correctly in single event loop. If not, wrap in `asyncio.ensure_future()`
3. **Claude vs GPT-4.1 behavior**: System prompt is model-agnostic. May need tuning for Claude's tool-calling patterns
4. **max_iterations semantics**: Set to 60 (each tool call = 2 iterations: call + result), roughly equals max_turns=30

## Verification

1. `pip install anthropic --upgrade` — verify beta_tool, tool_runner available
2. `python tests/test_real_pipeline.py` — full pipeline with resume=True
3. Check orchestrator completes improvement loop (no TPM/context errors)
4. Check >= 2 iterations with increasing scores
5. Check context management kicks in (log messages about cleared tool results)
6. Final score: aim for >= 5 on first migration run (tune later)

## Research Sources

- [Anthropic Tool Use Implementation](https://platform.claude.com/docs/en/agents-and-tools/tool-use/implement-tool-use) — @beta_tool, tool_runner API
- [Context Editing](https://platform.claude.com/docs/en/build-with-claude/context-editing) — clear_tool_uses, compaction
- [Claude Agent SDK](https://platform.claude.com/docs/en/agent-sdk/overview) — alternative higher-level SDK (not used)
- [Anthropic SDK Python](https://github.com/anthropics/anthropic-sdk-python) — source code for tool_runner
