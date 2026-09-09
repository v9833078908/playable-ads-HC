from agents import Agent

from .brief_extractor import brief_extractor_agent
from .generator import generator_agent
from .qa_agent import qa_agent


triage_agent = Agent(
    name="TriageAgent",
    instructions="""You orchestrate playable ad generation. Route tasks to specialized agents.

Workflow states:
1. Files uploaded → handoff to BriefExtractor
2. Brief + assets extracted → ScenarioBuilder handles Q&A (managed by app.py UI)
3. Scenario complete (scene_cards complete) → handoff to PlayableGenerator
4. HTML generated → handoff to QAAgent
5. QA validation → confirm or fix

Context fields:
- brief: Extracted DraftBrief
- assets: Extracted AssetMapping
- scene_cards: List of SceneCard (from interactive Q&A in UI)
- spec: PlayableSpec (built from scene_cards)
- html: Generated HTML
- validation: ValidationResult

IMPORTANT: ScenarioBuilder Q&A is handled in the UI layer, not by you.
You are invoked for:
- Initial file analysis (→ BriefExtractor)
- HTML generation (→ PlayableGenerator) when scene_cards complete
- QA validation (→ QAAgent)

When scene_cards are complete and generation requested, handoff to PlayableGenerator.""",
    handoffs=[
        brief_extractor_agent,
        generator_agent,
        qa_agent,
    ],
)
