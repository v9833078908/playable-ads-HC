# Legacy code

## `app.py` — Streamlit UI (does not run)

The Streamlit UI was written against the **v1 orchestrator**, a
`PlayableOrchestrator` class with `process_files()`, `chat()`,
`init_scenario_builder()`, `get_next_question()`, `process_answer()`,
`get_scenario_summary()`, `generate()` and `reset()`.

That class was removed when the orchestrator was rewritten as the v2
tool-runner pipeline (`playable_agents/orchestrator.py::run_orchestrator`).
`legacy/app.py` therefore fails at import:

```
ImportError: cannot import name 'PlayableOrchestrator' from 'playable_agents.orchestrator'
```

It is kept as a reference for the interactive scenario-builder UX (scene cards,
per-scene questions, confirmation screen) that still lives in
`playable_agents/scenario_builder.py` and `playable_agents/scene_card.py`.

**Use `run_pipeline.py` instead** — it drives the v2 pipeline end to end.
Porting the UI onto `run_orchestrator` is open work.
