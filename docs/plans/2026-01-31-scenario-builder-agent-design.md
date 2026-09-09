# ScenarioBuilder Agent Design

**Date**: 2026-01-31
**Status**: Approved
**Purpose**: Replace ClarifyAgent with interactive, iterative scenario-building through adaptive questioning

---

## 1. Overview & User Flow

### Purpose
Replace ClarifyAgent with an interactive agent that builds complete game flow specifications (mechanics, timing, transitions) through adaptive questioning. Goal: predictable HTML output through comprehensive scenario definition.

### Core Philosophy
User maintains full control while agent guides through necessary decisions. No store link questions. Generation blocked until all required questions answered.

### High-Level Flow
```
1. Upload PDF + images
2. Automated analysis (BriefExtractor, AssetMapper)
3. ScenarioBuilder shows detected scenes as empty cards
4. User adjusts scene structure (add/remove/reorder)
5. Agent asks 3-7 questions per scene (adaptive depth)
6. Cards populate in real-time (always editable)
7. Final confirmation screen with soft validation
8. Generate HTML
9. [Optional] Regenerate with feedback comment
```

### Key Changes
- **Removed**: Google Play/App Store link questions
- **Added**: Interactive scenario-building workflow
- **Changed**: UX blocks generation until scenario complete
- **Replaced**: ClarifyAgent entirely

---

## 2. UX/UI Design

### Layout
- **Left panel (60%)**: Chat interface where agent asks questions
- **Right panel (40%)**: Live scene cards with visual progress
- **Top bar**: Overall progress indicator + scene counter

### Scene Cards

**Visual States**:
- Empty (gray) → In Progress (blue pulse) → Complete (green checkmark)
- Amber warning indicator for PDF deviations
- Always editable (click any field to modify)

**Card Structure**:
```
Scene [N]: [Title]
├─ Mechanics: [drag-drop, merge, battle, etc.]
├─ UI Elements: [title text, buttons, HUD]
├─ Timing: [duration, transitions]
├─ User Actions: [what player does]
└─ Technical: [animations, performance notes]
```

**Default Values**:
- Optional skipped fields show: `(using default: X)`
- Smart defaults based on PDF analysis and common patterns

### Chat Interaction

**Question Format**:
Agent asks with reasoning:
```
"To ensure clear player feedback in Scene 2, I need to know:
what happens when player drags wrong item?
This affects tutorial completion logic."
```

**Smart Suggestions**:
Agent analyzes assets and provides contextual suggestions:
```
"I see 'wrong.png' in assets - use this for error state?"
```

**Between Scenes**:
5-10 second pause with message:
```
"Scene 2 complete ✓ Review the card before continuing..."
```

### Visual Progress
- Progress bar showing overall completion
- Scene counter: "Scene 2 of 5"
- Card states visible in sidebar

---

## 3. Questioning Strategy

### Adaptive Depth (3-7 questions per scene)

**Simple scenes** (e.g., Victory screen): **3 questions**
- Core mechanics
- UI text/copy
- CTA behavior

**Medium scenes** (e.g., Tutorial): **5 questions**
- Add: timing, user feedback, error handling

**Complex scenes** (e.g., Battle with multiple mechanics): **7 questions**
- Add: animations, edge cases, performance considerations

### Question Categories

Questions cover **Mechanics + UI/UX + Technical**:

1. **Core Mechanic**: What player does, win/fail conditions
2. **UI Elements**: Text, buttons, visual feedback, layout
3. **User Actions**: Interactions, gestures, input handling
4. **Timing**: Scene duration, animation speed
5. **Transitions**: How scene starts/ends, flow to next scene
6. **Error Handling**: What happens on wrong actions
7. **Technical**: Performance considerations, animation details (complex scenes only)

### Timing Question Specificity

**Adaptive approach**:
- **Simple scenes**: Qualitative - "Should animation feel: snappy, smooth, or dramatic?"
- **Complex scenes**: Specific - "Should merge animation be: fast (0.5s), medium (1s), or slow (2s)?"

### Cross-Scene Intelligence

Agent detects patterns and asks permission:
```
"I noticed Scene 1-2 use quick 0.5s transitions.
Apply this to remaining scenes, or customize each?"
```

**Rules**:
- Detect patterns across scenes
- Always ask permission before applying
- Maintain consistency unless user explicitly deviates

### Optional Fields

- User can skip non-critical questions
- Card shows default: `(using default: smooth 1s transition)`
- Smart defaults based on PDF + common patterns

---

## 4. Scene Detection & Structure Setup

### Initial Analysis

Before questioning, BriefExtractor + AssetMapper extract:
- Detected scenes with confidence levels
- Identified mechanics per scene
- Available assets mapped to roles (background, icons, characters)
- Missing/ambiguous information

### Hybrid Scene Presentation

Agent shows interactive overview:

```
📊 Analysis Results:

✅ Clearly Detected:
  • Scene 1: Repair Tutorial (drag-drop mechanic)
  • Scene 2: First Battle (auto-battle mechanic)
  • Scene 5: Victory Screen (CTA)

⚠️ Inferred (please confirm):
  • Scene 3: Weapons Tutorial (detected cannon assets)
  • Scene 4: Merge Tutorial (merge mechanic mentioned in text)

❓ Missing/Unclear:
  • Transition between Battle and Weapons
  • Tutorial replay mechanism?
```

### User Actions Before Questioning

User can:
- ✏️ Edit scene titles
- ➕ Add new scene card
- 🗑️ Remove scene
- ↕️ Drag to reorder scenes
- ✓ Confirm structure → Start questioning

### Adding Scenes

**During questioning**: Not allowed (to maintain flow)

**After questioning**: Agent asks:
```
"Scenario complete! Want to add any additional scenes
(e.g., settings screen, loading screen)?"
```

Most likely answer: No (per company/studio pipeline)

---

## 5. Validation & Final Confirmation

### Real-Time Soft Warnings

Amber indicators on cards (don't block generation):

**PDF Deviation**:
```
⚠️ Scene 2 duration is 10s, but PDF specifies 5-7s range
```

**Missing Asset**:
```
⚠️ Scene 3 requires 'cannon_upgraded.png' but not found in uploads
```

**Logic Conflict**:
```
⚠️ Scene 4 merge needs 2 cannons, but Scene 3 only provides 1
```

User can proceed anyway.

### Technical Constraints (Silent)

Agent does NOT mention during questioning, handles automatically:
- 5MB file size limit
- MRAID compliance
- Single-file requirement
- No external requests

### Final Confirmation Screen

```
🎯 Scenario Summary

5 scenes defined | 2 warnings | Ready to generate

Scene 1: Repair Tutorial ✓
Scene 2: First Battle ✓ ⚠️ (duration deviation)
Scene 3: Weapons Tutorial ✓
Scene 4: Merge Tutorial ✓
Scene 5: Victory Screen ✓

⚠️ 2 Warnings (click to review)

[Edit Scenario] [Generate HTML]
```

### Soft Validation Behavior

- Shows incomplete fields: `"Scene 3: transition timing not specified (will use default)"`
- Shows warnings but allows generation
- User can click warning to jump to relevant card
- "Generate" button enabled once all required questions answered

---

## 6. Regeneration with Feedback

### Regeneration UI

After HTML generation:

```
✅ Playable Generated Successfully!

[Preview] [Download] [Regenerate]

💬 Want changes? Describe what to adjust:
[Text input field]

[Regenerate with Changes]
```

### Smart Interpretation

**User input example**:
```
"Make tutorial faster and add particle effects to merge"
```

**Agent response**:
```
🤖 I understand you want to:
  1. Speed up tutorial (affects Scene 1: duration 10s → 5s)
  2. Add particle effects to merge (affects Scene 4: technical details)

Updating Scene 1 and Scene 4 cards...
Regenerating HTML...
```

**Behavior**:
1. Agent interprets feedback comment
2. Updates affected scene cards
3. Shows what changed
4. Regenerates HTML
5. Cards remain editable for further tweaks

---

## 7. Technical Implementation

### Architecture Changes

```
playable_agents/
├── scenario_builder.py          # NEW: Main ScenarioBuilder agent
│   ├── detect_scenes()           # Hybrid scene detection
│   ├── generate_questions()      # Adaptive 3-7 questions per scene
│   ├── build_scene_card()        # Populate card from answers
│   ├── detect_patterns()         # Cross-scene pattern recognition
│   └── interpret_feedback()      # Parse regeneration comments
│
├── scene_card.py                 # NEW: Scene card data structure
│   ├── SceneCard class
│   ├── fields: mechanics, ui, timing, actions, technical
│   └── validation: soft warnings, completeness check
│
└── validation.py                 # NEW: Soft validation logic
    ├── check_pdf_deviation()
    ├── check_asset_availability()
    └── check_logic_conflicts()
```

### app.py Modifications

```python
# REMOVE
- ClarifyAgent workflow
- Store link questions

# ADD
- ScenarioBuilder agent initialization
- Scene card UI components (sidebar)
- Progress bar and scene state indicators
- Regeneration endpoint with feedback text field

# UPDATE
- Block "Generate" button until scenario complete
- Chat interface for question-answer flow
- Final confirmation screen with soft validation
```

### Data Flow

```
1. Upload → BriefExtractor + AssetMapper
2. ScenarioBuilder.detect_scenes() → Interactive card overview
3. User confirms structure
4. For each scene:
   - ScenarioBuilder.generate_questions(scene, complexity)
   - Chat Q&A (3-7 questions)
   - ScenarioBuilder.build_scene_card(answers)
   - Pause for review (5-10s)
5. ScenarioBuilder.detect_patterns() → Ask permission to apply
6. Final confirmation screen → validation.check_*()
7. Generate PlayableSpec.json from cards
8. Render HTML
9. [Optional] interpret_feedback() → Update cards → Regenerate
```

### Scene Card Data Structure

```python
@dataclass
class SceneCard:
    id: str
    title: str
    state: Literal["empty", "in_progress", "complete"]

    # Core data
    mechanics: list[str]
    ui_elements: dict[str, str]
    timing: dict[str, float]
    user_actions: list[str]
    technical: dict[str, Any]

    # Metadata
    warnings: list[Warning]
    defaults_used: dict[str, Any]
    pdf_source: Optional[str]

    def is_complete(self) -> bool:
        """Check if all required fields are filled"""

    def get_warnings(self) -> list[Warning]:
        """Get soft validation warnings"""
```

---

## 8. Acceptance Criteria

### Must Have
- ✅ ClarifyAgent completely replaced
- ✅ Store link questions removed
- ✅ Interactive scene card overview with add/remove/reorder
- ✅ 3-7 adaptive questions per scene
- ✅ Questions include reasoning and smart asset suggestions
- ✅ Chat-based Q&A with real-time card updates
- ✅ Cards always editable
- ✅ Visual progress bar + card states
- ✅ 5-10s pause between scenes for review
- ✅ Pattern detection with permission
- ✅ Final confirmation screen
- ✅ Soft validation warnings (don't block)
- ✅ Generation blocked until required questions answered
- ✅ Regeneration with feedback text field

### Nice to Have
- Export/import scenario templates
- Scene templates library
- Undo/redo for card edits
- Keyboard shortcuts for navigation

### Out of Scope (for MVP)
- Real-time collaboration
- Version history
- A/B testing scenarios
- Analytics on question effectiveness

---

## 9. Success Metrics

**User Experience**:
- Predictable HTML output matching user's mental model
- < 5 minutes to complete scenario for 5-scene playable
- 90%+ user satisfaction with generated HTML (fewer regenerations needed)

**Technical**:
- 100% of generated HTML passes compliance (MRAID, single-file, 5MB)
- Reduced "missing information" errors from 40% to < 10%
- Average 4.5 questions per scene (within 3-7 range)

---

## 10. Next Steps

1. Implement `SceneCard` data structure
2. Build ScenarioBuilder agent with adaptive questioning
3. Update Streamlit UI (chat + sidebar cards)
4. Integrate with existing BriefExtractor/AssetMapper
5. Add soft validation logic
6. Implement regeneration with feedback
7. Testing with real PDF specs
8. Iterate based on feedback

---

**Design approved**: 2026-01-31
**Ready for implementation**: Yes
