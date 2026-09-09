# Manual scripts

These scripts call **live APIs** (Anthropic, Gemini, FAL) and cost money. They are
not collected by pytest (`pytest.ini` limits discovery to `tests/`).

Run them from the repository root with the virtualenv active:

```bash
python scripts/manual/test_real_pipeline.py
```

## Input fixtures

Several scripts need a brief and reference art. The original fixtures live in
`docs/misc/`, which is **not published** (client specification and third-party
reference material). Point them at your own inputs:

```bash
export PLAYABLE_SPEC=./my-brief.md
export PLAYABLE_ASSETS=./my-references     # directory of PNG/JPG files
python scripts/manual/show_agent_results.py
```

Without those variables the scripts fall back to the `docs/misc/` paths and exit
with a clear message if they are absent.

| Script | What it does |
|---|---|
| `test_real_pipeline.py` | Full v2 orchestrator run end to end |
| `test_detailed_pipeline.py` | Same, printing every agent's intermediate output |
| `show_agent_results.py` | Scenario + asset-generator agents only |
| `test_real_agents.py` | Individual agent smoke runs |
| `test_real_generation.py` | HTML generation only |
| `test_fixes.py` | Offline checks of asset injection, image optimization, technical QA |
| `test_asset_generation.py`, `test_full_workflow.py` | Legacy v1 asset/HTML helpers |
| `test_fal_imagen.py`, `test_imagen_api.py`, `test_imagen_simple.py`, `test_fal_llm.py`, `test_gemini_multimodal.py` | Provider connectivity probes |
