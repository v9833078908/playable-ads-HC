# ScenarioBuilder Agent - Implementation Plan

**Date**: 2026-01-31
**Design Doc**: `2026-01-31-scenario-builder-agent-design.md`
**Target**: MVP in 2-3 days

---

## Phase 1: Foundation (Day 1, 4-6 hours)

### Task 1.1: Scene Card Data Structure
**File**: `playable_agents/scene_card.py`
**Priority**: Critical
**Duration**: 2 hours

Create `SceneCard` dataclass with:
- Fields: id, title, state, mechanics, ui_elements, timing, user_actions, technical
- Metadata: warnings, defaults_used, pdf_source
- Methods: `is_complete()`, `get_warnings()`, `to_dict()`, `from_dict()`

**Acceptance**:
- [ ] SceneCard can be instantiated with minimal data
- [ ] Can serialize/deserialize to JSON
- [ ] State transitions work (empty → in_progress → complete)

---

### Task 1.2: Validation Logic
**File**: `playable_agents/validation.py`
**Priority**: High
**Duration**: 2 hours
**Depends on**: Task 1.1

Implement soft validation functions:
- `check_pdf_deviation(card, pdf_data)` → list of warnings
- `check_asset_availability(card, assets)` → list of warnings
- `check_logic_conflicts(cards)` → list of warnings
- `get_completeness_status(card)` → dict of missing fields

**Acceptance**:
- [ ] Returns warnings without blocking
- [ ] Detects common issues (missing assets, duration mismatches, logic conflicts)
- [ ] Works with partial data (doesn't crash on incomplete cards)

---

### Task 1.3: Scene Detection Logic
**File**: `playable_agents/scenario_builder.py` (part 1)
**Priority**: Critical
**Duration**: 2 hours
**Depends on**: Task 1.1

Implement `detect_scenes()` method:
- Input: BriefExtractor output + AssetMapper output
- Output: Dict with "detected", "inferred", "missing"
- Logic: Parse PDF data for scene mentions, mechanics, flow
- Create empty SceneCards for detected scenes

**Acceptance**:
- [ ] Correctly identifies scenes from pirate-ships-playable-spec.json
- [ ] Distinguishes between clear vs. inferred scenes
- [ ] Creates SceneCards with titles and basic metadata

---

## Phase 2: Questioning Engine (Day 1-2, 6-8 hours)

### Task 2.1: Question Generator
**File**: `playable_agents/scenario_builder.py` (part 2)
**Priority**: Critical
**Duration**: 3 hours
**Depends on**: Task 1.3

Implement `generate_questions(scene_card, complexity)` method:
- Input: SceneCard, complexity level (auto-detected)
- Output: List of 3-7 Question objects
- Logic:
  - Detect complexity based on mechanics count, dependencies
  - Generate adaptive questions (mechanics → UI → technical)
  - Include reasoning for each question
  - Add smart suggestions from available assets

**Question Object Structure**:
```python
@dataclass
class Question:
    text: str
    reasoning: str
    category: Literal["mechanics", "ui", "timing", "technical"]
    optional: bool = False
    suggestions: list[str] = field(default_factory=list)
    default_value: Optional[Any] = None
```

**Acceptance**:
- [ ] Simple scenes get 3 questions, complex get 7
- [ ] Questions include reasoning
- [ ] Smart suggestions based on assets work
- [ ] Question categories distributed appropriately

---

### Task 2.2: Answer Processing
**File**: `playable_agents/scenario_builder.py` (part 3)
**Priority**: Critical
**Duration**: 2 hours
**Depends on**: Task 2.1

Implement `process_answer(question, answer, scene_card)` method:
- Input: Question, user answer text, SceneCard
- Output: Updated SceneCard
- Logic:
  - Parse answer (handle free text, selections, numbers)
  - Update appropriate card field
  - Apply defaults if skipped
  - Mark field as user-defined vs. default

**Acceptance**:
- [ ] Correctly updates card fields
- [ ] Handles various answer formats
- [ ] Tracks which fields use defaults
- [ ] Doesn't crash on unexpected input

---

### Task 2.3: Pattern Detection
**File**: `playable_agents/scenario_builder.py` (part 4)
**Priority**: Medium
**Duration**: 2 hours
**Depends on**: Task 2.2

Implement `detect_patterns(completed_cards)` method:
- Input: List of completed SceneCards
- Output: Dict of detected patterns + affected scenes
- Logic:
  - Detect timing patterns (same transition speeds)
  - Detect UI patterns (same button styles)
  - Detect mechanic patterns (same error handling)
- Generate permission question for user

**Acceptance**:
- [ ] Detects common timing patterns
- [ ] Generates clear permission questions
- [ ] Can apply pattern to remaining scenes
- [ ] User can decline and customize

---

### Task 2.4: Feedback Interpretation
**File**: `playable_agents/scenario_builder.py` (part 5)
**Priority**: Medium
**Duration**: 1 hour
**Depends on**: Task 2.2

Implement `interpret_feedback(feedback_text, cards)` method:
- Input: User feedback string, list of SceneCards
- Output: List of card updates + explanation
- Logic:
  - Parse natural language feedback
  - Identify affected scenes
  - Generate card updates
  - Explain changes to user

**Example**:
```python
interpret_feedback(
    "make tutorial faster and add particle effects",
    cards
)
# Returns:
# {
#   "changes": [
#     {"scene_id": "scene1", "field": "timing.duration", "old": 10, "new": 5},
#     {"scene_id": "scene4", "field": "technical.particles", "value": True}
#   ],
#   "explanation": "Speed up tutorial (Scene 1: 10s → 5s), Add particles (Scene 4)"
# }
```

**Acceptance**:
- [ ] Correctly parses common feedback patterns
- [ ] Identifies affected scenes
- [ ] Generates clear explanations
- [ ] Doesn't crash on ambiguous input

---

## Phase 3: UI Integration (Day 2, 4-6 hours)

### Task 3.1: Scene Card UI Components
**File**: `app.py` (Scene Cards section)
**Priority**: Critical
**Duration**: 3 hours
**Depends on**: Task 1.1

Create Streamlit components for scene cards:
- Card display with collapsible sections
- Editable fields (st.text_input, st.number_input inline)
- State indicators (empty/in-progress/complete)
- Warning badges (amber indicator)
- Default value display `(using default: X)`

**Layout** (right sidebar):
```python
with st.sidebar:
    st.markdown("### Scenario")
    for card in st.session_state.scene_cards:
        render_scene_card(card)
```

**Acceptance**:
- [ ] Cards render correctly with all fields
- [ ] Inline editing works
- [ ] State indicators update
- [ ] Warnings display with amber badge
- [ ] Defaults shown correctly

---

### Task 3.2: Progress Indicators
**File**: `app.py` (Progress section)
**Priority**: High
**Duration**: 1 hour
**Depends on**: Task 3.1

Add progress visualization:
- Overall progress bar (top)
- Scene counter: "Scene 2 of 5"
- Card state icons (gray/blue/green)

**Acceptance**:
- [ ] Progress bar updates as questions answered
- [ ] Scene counter shows current position
- [ ] Card states visually clear

---

### Task 3.3: Chat Interface Updates
**File**: `app.py` (Chat section)
**Priority**: Critical
**Duration**: 2 hours
**Depends on**: Task 2.1

Update chat to support ScenarioBuilder:
- Display questions with reasoning formatting
- Show smart suggestions
- Handle answer input
- Show scene completion messages
- Add 5-10s pause between scenes (with skip button)

**Question Format**:
```markdown
**Scene 2: First Battle**

To ensure clear player feedback, I need to know:
**What happens when player's ship HP reaches zero?**

This affects battle end condition logic.

💡 Suggestions:
- Game over with retry button
- Auto-repair and continue
- Transition to defeat screen
```

**Acceptance**:
- [ ] Questions render with reasoning
- [ ] Suggestions display clearly
- [ ] Scene transitions show pause message
- [ ] User can skip pause with button

---

## Phase 4: Workflow Integration (Day 2-3, 4-6 hours)

### Task 4.1: Remove ClarifyAgent
**File**: `playable_agents/orchestrator.py` + `app.py`
**Priority**: Critical
**Duration**: 1 hour
**Depends on**: Tasks 2.1-2.4, 3.1-3.3

Remove ClarifyAgent integration:
- Remove from orchestrator workflow
- Remove store link questions
- Remove old clarification UI

**Acceptance**:
- [ ] ClarifyAgent no longer called
- [ ] No store link questions appear
- [ ] Old UI removed

---

### Task 4.2: Integrate ScenarioBuilder in Workflow
**File**: `playable_agents/orchestrator.py` + `app.py`
**Priority**: Critical
**Duration**: 3 hours
**Depends on**: Task 4.1

Add ScenarioBuilder to workflow:
1. After BriefExtractor + AssetMapper complete
2. Show scene detection overview
3. User confirms/edits scene structure
4. Start questioning workflow
5. Populate cards in real-time
6. Block generation until complete

**New Workflow**:
```python
# In orchestrator
async def run_playable_generation():
    # 1. Analysis (existing)
    brief = await brief_extractor.extract(pdf)
    assets = await asset_mapper.map(images)

    # 2. ScenarioBuilder (NEW)
    scenario_builder = ScenarioBuilder(brief, assets)
    scenes = await scenario_builder.detect_scenes()
    # ... user confirms structure ...
    cards = await scenario_builder.build_scenario_interactive()

    # 3. Generation (existing, now uses cards)
    spec = cards_to_playable_spec(cards)
    html = await template_composer.render(spec)
    return html
```

**Acceptance**:
- [ ] ScenarioBuilder runs after analysis
- [ ] Scene detection shows correctly
- [ ] Questioning workflow completes
- [ ] Cards convert to PlayableSpec.json
- [ ] Generation uses scenario data

---

### Task 4.3: Final Confirmation Screen
**File**: `app.py` (Confirmation section)
**Priority**: High
**Duration**: 2 hours
**Depends on**: Task 4.2

Create confirmation screen before generation:
- Summary of all scenes
- Warning count
- Expandable warnings list
- "Edit Scenario" and "Generate HTML" buttons
- Block "Generate" if required fields missing

**Layout**:
```
🎯 Scenario Summary
─────────────────
5 scenes defined | 2 warnings | Ready to generate

✓ Scene 1: Repair Tutorial
✓ Scene 2: First Battle ⚠️ (duration deviation)
✓ Scene 3: Weapons Tutorial
✓ Scene 4: Merge Tutorial
✓ Scene 5: Victory Screen

⚠️ 2 Warnings
  > Scene 2: Duration 10s exceeds PDF spec (5-7s)
  > Scene 3: Asset 'cannon_upgraded.png' not found

[Edit Scenario]  [Generate HTML]
```

**Acceptance**:
- [ ] Summary displays all scenes correctly
- [ ] Warnings expandable and clear
- [ ] "Edit" returns to scenario editing
- [ ] "Generate" only enabled when ready
- [ ] Soft validation doesn't block generation

---

## Phase 5: Regeneration (Day 3, 2-3 hours)

### Task 5.1: Regeneration UI
**File**: `app.py` (Post-generation section)
**Priority**: Medium
**Duration**: 1 hour
**Depends on**: Task 4.3

Add regeneration interface after HTML generated:
- Text input for feedback
- "Regenerate" button
- Show interpretation before regenerating

**Layout**:
```
✅ Playable Generated Successfully!

[Preview]  [Download]  [Regenerate]

💬 Want changes? Describe what to adjust:
┌─────────────────────────────────────────┐
│ Make tutorial faster and add particles  │
└─────────────────────────────────────────┘

[Regenerate with Changes]
```

**Acceptance**:
- [ ] Text input accepts feedback
- [ ] Regenerate button triggers workflow
- [ ] Original scenario preserved until regeneration complete

---

### Task 5.2: Regeneration Logic
**File**: `app.py` + `playable_agents/scenario_builder.py`
**Priority**: Medium
**Duration**: 2 hours
**Depends on**: Task 5.1, Task 2.4

Implement regeneration workflow:
1. User enters feedback
2. Call `interpret_feedback()`
3. Show interpretation to user
4. Update affected cards
5. Regenerate HTML
6. Show new result

**Acceptance**:
- [ ] Feedback correctly interpreted
- [ ] Changes shown before regeneration
- [ ] Cards update appropriately
- [ ] HTML regenerates with changes
- [ ] Can iterate multiple times

---

## Phase 6: Testing & Polish (Day 3, 2-4 hours)

### Task 6.1: End-to-End Testing
**Priority**: Critical
**Duration**: 2 hours

Test complete workflow:
- Upload pirate-ships PDF + assets
- Scene detection accuracy
- Question flow (3-7 per scene)
- Card population
- Pattern detection
- Final confirmation
- HTML generation
- Regeneration

**Test Cases**:
- [ ] Simple playable (3 scenes)
- [ ] Complex playable (5+ scenes)
- [ ] Ambiguous PDF (missing scenes)
- [ ] User edits cards manually
- [ ] User applies patterns
- [ ] User skips optional questions
- [ ] Regeneration with feedback

---

### Task 6.2: Error Handling
**Priority**: High
**Duration**: 1 hour

Add error handling:
- Invalid user input
- Missing PDF data
- Asset loading failures
- Question generation errors
- Card validation errors

**Acceptance**:
- [ ] Graceful error messages
- [ ] No crashes on bad input
- [ ] User can recover from errors

---

### Task 6.3: UX Polish
**Priority**: Medium
**Duration**: 1 hour

Polish user experience:
- Loading states during analysis
- Smooth transitions between scenes
- Clear empty states
- Helpful tooltips
- Keyboard shortcuts (optional)

**Acceptance**:
- [ ] No jarring transitions
- [ ] Clear what to do next
- [ ] Professional appearance

---

## Implementation Order (Recommended)

### Day 1 (Morning)
1. Task 1.1: Scene Card Data Structure
2. Task 1.3: Scene Detection Logic

### Day 1 (Afternoon)
3. Task 2.1: Question Generator
4. Task 1.2: Validation Logic

### Day 2 (Morning)
5. Task 2.2: Answer Processing
6. Task 3.1: Scene Card UI Components

### Day 2 (Afternoon)
7. Task 3.3: Chat Interface Updates
8. Task 4.1: Remove ClarifyAgent
9. Task 4.2: Integrate ScenarioBuilder

### Day 3 (Morning)
10. Task 4.3: Final Confirmation Screen
11. Task 2.3: Pattern Detection

### Day 3 (Afternoon)
12. Task 2.4: Feedback Interpretation
13. Task 5.1: Regeneration UI
14. Task 5.2: Regeneration Logic
15. Task 6.1-6.3: Testing & Polish

---

## Dependencies Graph

```
Task 1.1 (SceneCard)
  ├─→ Task 1.2 (Validation)
  ├─→ Task 1.3 (Scene Detection)
  │     └─→ Task 2.1 (Question Generator)
  │           ├─→ Task 2.2 (Answer Processing)
  │           │     ├─→ Task 2.3 (Pattern Detection)
  │           │     └─→ Task 2.4 (Feedback Interpretation)
  │           └─→ Task 3.3 (Chat Interface)
  └─→ Task 3.1 (Scene Card UI)
        └─→ Task 3.2 (Progress Indicators)

Task 2.1, 2.2, 3.1, 3.3 → Task 4.1 (Remove ClarifyAgent)
                        → Task 4.2 (Integrate Workflow)
                        → Task 4.3 (Confirmation Screen)
                        → Task 5.1 (Regeneration UI)
                        → Task 5.2 (Regeneration Logic)
                        → Task 6.* (Testing)
```

---

## Risk Mitigation

### Risk 1: Question quality varies
**Mitigation**: Create question templates library, use few-shot prompting

### Risk 2: UI complexity overwhelming
**Mitigation**: Start with minimal UI, iterate based on feedback

### Risk 3: Pattern detection too aggressive
**Mitigation**: Always ask permission, make it easy to decline

### Risk 4: Regeneration interpretation errors
**Mitigation**: Show interpretation before applying, allow manual override

### Risk 5: Integration breaks existing flow
**Mitigation**: Keep existing agents intact, only modify orchestrator

---

## Success Criteria

- [ ] ClarifyAgent completely removed
- [ ] ScenarioBuilder asks 3-7 questions per scene adaptively
- [ ] Cards populate in real-time during chat
- [ ] Cards always editable
- [ ] Soft validation shows warnings without blocking
- [ ] Generation blocked until scenario complete
- [ ] Final confirmation screen works
- [ ] Regeneration with feedback functional
- [ ] No crashes or major bugs
- [ ] End-to-end test with pirate-ships PDF succeeds

---

## Optional Enhancements (Post-MVP)

- Export/import scenario JSON
- Scenario templates library
- Undo/redo for card edits
- Keyboard navigation
- Save progress and resume later
- Multi-language support for questions
- Analytics on question effectiveness
- A/B testing scenarios

---

**Plan Status**: Ready for implementation
**Estimated Total Time**: 16-24 hours (2-3 days)
**Next Step**: Start with Task 1.1 (Scene Card Data Structure)
