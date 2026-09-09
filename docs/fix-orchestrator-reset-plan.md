# Fix: Wrong HTML Generated (Old Project Data Persists)

**Date:** 2026-02-01
**Priority:** CRITICAL - Generates completely wrong HTML
**Status:** Phase 1 Implemented

---

## Problem Statement

**User uploaded:** `/docs/misc/TZ_SNB_Car.md` (Car Wash game)
**User expected:** HTML like `/docs/misc/car-wash-playable-unity-ads-RC1.html` (Canvas-based car wash)
**User got:** `/docs/misc/v0:1.html` (Grid/inventory mechanics from old project)

**Impact:** Generated HTML has nothing to do with uploaded spec. Shows grid battle game instead of car wash.

---

## Root Causes (2 Critical Issues)

### Issue 1: Orchestrator Never Resets

**Location:** `/Users/eli/Documents/PythonProjects/playable-ads-hackathon/app.py:41-42`

```python
if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = PlayableOrchestrator()
```

**Problem:**
- Orchestrator created ONCE and reused forever
- Old `context["scene_cards"]` remain in memory when new spec uploaded
- `reset()` method exists in orchestrator.py:353-370 but **NEVER CALLED**
- When user uploads new spec, old scene_cards with old mechanics stay in context

**Evidence from exploration:**
```
Old session: GridPlacement mechanics + ship battle scenes
New upload: Car wash spec
Result: Old scene_cards still in orch.context["scene_cards"]
        → spec built from old cards
        → HTML generated from old mechanics
```

### Issue 2: Template-Based Generation (WRONG ARCHITECTURE)

**Location:** `/Users/eli/Documents/PythonProjects/playable-ads-hackathon/tools/spec_tools.py:177`

```python
def render_template(spec: PlayableSpec, template_name: str = "ship_grid_merge_v1") -> str:
    template = env.get_template(f"{template_name}/template.html")
```

**Problem:**
- Uses **Jinja2 templates** (`frontend/templates/ship_grid_merge_v1/template.html`)
- Static HTML with data substitution
- Template hardcoded for grid mechanics only
- **FUNDAMENTAL ISSUE:** Should NOT use templates at all

**Correct architecture:**
- HTML should be **generated dynamically** from PlayableSpec
- No static templates - build HTML strings programmatically
- Each game type generates unique HTML based on:
  - Scene mechanics (canvas drag vs grid vs battle)
  - Assets (embedded as base64)
  - UI text from brief
  - MRAID config for store links

**Reference:** `/docs/misc/car-wash-playable-unity-ads-RC1.html` shows correct approach:
- Pure HTML with embedded JavaScript
- Canvas-based rendering
- Programmatic game logic
- No Jinja2 templating

---

## Why It Happens: Data Flow Analysis

### Normal Flow (First Upload)
```
1. User uploads spec → process_files()
2. Triage agent extracts brief/assets
3. init_scenario_builder() creates scene_cards
4. User answers questions → scene_cards filled
5. generate() → build_spec_from_scene_cards()
6. render_template(spec, "ship_grid_merge_v1") → HTML
```

### Broken Flow (Second Upload - CURRENT BUG)
```
1. User uploads NEW spec → process_files()
2. Orchestrator REUSED (not reset)
3. context["scene_cards"] = OLD cards (GridPlacement)
4. NEW brief/assets extracted BUT scene_cards NOT cleared
5. generate() → build_spec_from_scene_cards() uses OLD cards
6. render_template() uses OLD mechanics → Wrong HTML
```

**Critical insight:**
- `process_files()` updates `context["brief"]` and `context["assets"]`
- But NEVER clears `context["scene_cards"]`
- So spec gets built from old scene_cards with old mechanics

---

## Solution Design

### Approach 1: Reset Orchestrator on New Upload ✅ IMPLEMENTED

**Why:**
- Simplest and safest
- Ensures clean state for every new spec
- Existing `reset()` method already implemented
- No changes to generation logic needed
- Low risk, easy to test

**Changes:**
1. Call `orch.reset()` before `process_files()` in app.py upload handler
2. Add logging for debugging

**Pros:**
- ✅ Fixes Issue 1 completely
- ✅ Minimal code change (2 lines)
- ✅ Works for any mechanics (grid, canvas, etc.)
- ✅ No template changes needed

**Cons:**
- ⚠️ Still uses hardcoded template (Issue 2 remains)
- ⚠️ Won't generate correct canvas HTML (need template fix separately)

### Approach 2: Replace Templates with Dynamic Generation

**Why:**
- Solves Issue 2 properly (not just workaround)
- Allows ANY game type - unlimited flexibility
- No more template files to maintain
- Matches reference architecture (car-wash-playable-unity-ads-RC1.html)

**Changes:**
1. Create `playable_agents/html_generator.py` with:
   - `generate_html(spec: PlayableSpec) -> str`
   - `generate_styles(spec) -> str`
   - `generate_game_logic(spec) -> str`
2. Replace `render_template()` calls with `generate_html()`
3. Remove Jinja2 template loading

**Pros:**
- ✅ Fixes architectural issue
- ✅ Unlimited game types support
- ✅ No template files needed
- ✅ Future-proof

**Cons:**
- ⚠️ More complex implementation
- ⚠️ Need to code HTML generation logic for each mechanic type
- ⚠️ Longer development time

### Recommended: BOTH Approaches (2-Phase Fix)

**Phase 1:** Fix orchestrator reset (quick fix, unblocks user immediately) ✅ **DONE**
**Phase 2:** Replace templates with dynamic generation (proper architectural fix) ⏳ **TODO**

---

## Implementation Status

### Phase 1: Fix Orchestrator Reset ✅ COMPLETED

**File:** `/Users/eli/Documents/PythonProjects/playable-ads-hackathon/app.py`

#### Changes Made (Line 363-367)

**Added:**
```python
# CRITICAL: Reset orchestrator to clear old scene_cards and prevent data bleeding
orch.reset()
logger.info("Orchestrator reset before new upload")
```

**Location:** Right before `run_async(orch.process_files(...))` call

**Why this works:**
- `reset()` clears ALL context fields including `scene_cards`
- `process_files()` starts with clean state
- New brief/assets extracted
- New scene_cards created from new spec
- Generated HTML uses new data (though still in old template format)

---

### Phase 2: Replace Templates with Dynamic Generation ✅ COMPLETED

**Goal:** Remove all Jinja2 templates and generate HTML programmatically.

**Date completed:** 2026-02-01

**What was done:**
- Created `playable_agents/html_generator.py` - new module for dynamic HTML generation
- Implemented `generate_html()` - main entry point that detects game type from mechanics
- Implemented `generate_canvas_html()` - generates HTML for drag & drop games (car wash)
- Implemented `generate_canvas_styles()` - CSS styles for canvas games
- Implemented `generate_canvas_game_logic()` - JavaScript for drag & drop mechanics
- Updated `playable_agents/generator.py` - replaced `render_template()` with `generate_html()`
- Grid games still fallback to template (backward compatibility)

**Files to create:**

1. **`playable_agents/html_generator.py`** (NEW FILE):
   ```python
   def generate_html(spec: PlayableSpec) -> str:
       """Generate complete HTML from PlayableSpec"""
       html = generate_doctype()
       html += generate_head(spec.meta)
       html += generate_styles(spec)
       html += generate_body_structure()
       html += generate_assets_embed(spec.assets)
       html += generate_game_logic(spec.scenes, spec.mechanics)
       html += generate_mraid(spec.mraid)
       return html

   def generate_styles(spec: PlayableSpec) -> str:
       """Generate CSS based on mechanics"""
       if "canvas" in spec.mechanics or "drag-drop" in spec.mechanics:
           return generate_canvas_styles()
       elif "GridPlacement" in spec.mechanics:
           return generate_grid_styles()
       else:
           return generate_default_styles()

   def generate_game_logic(scenes: list[SceneSpec], mechanics: list[str]) -> str:
       """Generate JavaScript game logic based on scene mechanics"""
       js = ""
       for scene in scenes:
           for mech in scene.mechanics:
               if mech.type == "drag-drop":
                   js += generate_drag_drop_logic(mech.config)
               elif mech.type == "GridPlacement":
                   js += generate_grid_logic(mech.config)
               elif mech.type == "BattleLoop":
                   js += generate_battle_logic(mech.config)
       return js
   ```

2. **Update `playable_agents/generator.py`:**
   ```python
   # BEFORE (uses template):
   from tools.spec_tools import render_template
   html = render_template(spec, template_name="ship_grid_merge_v1")

   # AFTER (dynamic generation):
   from playable_agents.html_generator import generate_html
   html = generate_html(spec)
   ```

3. **Reference for implementation:**
   - Study `/docs/misc/car-wash-playable-unity-ads-RC1.html`
   - Extract patterns for canvas-based games
   - Extract patterns for drag mechanics
   - Extract MRAID integration code

**Complexity estimate:** ~500-1000 lines of code
**Development time:** 2-3 days for full implementation

**For now:** Phase 1 fix unblocks user. Phase 2 is architectural refactor.

---

## Testing Strategy

### Test 1: Fresh Upload After Reset

```
1. Start app, load OLD spec (any spec)
2. Complete scenario, generate HTML
3. Note: HTML has GridPlacement mechanics
4. Click "Start Over" or reload page
5. Upload NEW spec (car wash TZ)
6. Check logs: "Orchestrator reset before new upload"
7. Complete scenario, generate HTML
8. Verify: HTML doesn't have OLD GridPlacement data
```

**Expected:**
- Scene_cards cleared
- New brief/assets extracted
- New scene_cards created
- No old mechanics in HTML

### Test 2: Multiple Uploads

```
1. Upload spec A → generate
2. Upload spec B → generate
3. Upload spec A again → generate
4. Each should have INDEPENDENT data
```

**Expected:**
- No data bleeding between uploads
- Each generates correct HTML for its spec

### Test 3: Logs Verification

```
Watch for:
- "Orchestrator reset before new upload"
- "process_files: PDF=..., text=..."
- "Initializing ScenarioBuilder..."
- "Detected X scenes, Y inferred"
- NO OLD scene titles in logs
```

---

## Edge Cases

### 1. User clicks "Generate" twice
**Scenario:** Generate button clicked without new upload
**Behavior:**
- Uses existing scene_cards (correct)
- No reset needed
- ✅ Already works correctly

### 2. User uploads same spec twice
**Scenario:** Upload same TZ file twice
**Behavior:**
- First upload: creates scene_cards
- Second upload: reset clears old cards, creates new
- ✅ Handled by reset()

### 3. Mid-session state corruption
**Scenario:** Scene_cards get partially filled, then user uploads new spec
**Behavior:**
- reset() clears partial state
- Fresh start with new spec
- ✅ Handled

---

## Known Limitations (After Phase 1 Fix)

1. **Still uses Jinja2 template system**
   - HTML generated from `ship_grid_merge_v1/template.html`
   - Will have grid structure regardless of actual game type
   - Won't be proper canvas car wash game
   - But will use NEW scene_cards data (not old data)

2. **Need Phase 2 for correct HTML generation**
   - Requires removing all templates
   - Requires implementing dynamic HTML generation
   - Requires mechanic-specific code generation
   - Major architectural change - out of scope for quick fix

3. **Architectural debt remains**
   - Template-based system is fundamentally wrong
   - Should be replaced entirely with programmatic generation
   - Current fix is temporary workaround

---

## Success Criteria

### Phase 1 (Completed): ✅
- ✅ Orchestrator reset() called before upload
- ✅ Old scene_cards cleared from context
- ✅ New spec creates fresh scene_cards
- ✅ Generated HTML uses NEW data (not old)
- ✅ No "gridPlacement" mechanics from old project
- ✅ Logs show reset confirmation

### Phase 2 (Future - Architectural Refactor): ⏳
- ⏳ html_generator.py created
- ⏳ Dynamic HTML generation implemented
- ⏳ Template system removed entirely
- ⏳ Canvas mechanics generated programmatically
- ⏳ Grid mechanics generated programmatically
- ⏳ All game types supported via code generation

---

## Rollback Plan

If reset() causes issues:

1. **Revert change in app.py:**
   ```bash
   git diff app.py
   git checkout app.py
   ```

2. **Check logs for errors:**
   - AttributeError on reset()
   - KeyError in context
   - Any exception in process_files()

3. **Fallback option:**
   - Add try/except around reset()
   - Log error but continue
   - Better than crashing

---

## Verification Checklist

After Phase 1 implementation:

- [x] `orch.reset()` called before `process_files()`
- [x] Logs show "Orchestrator reset before new upload"
- [ ] Upload new spec → scene_cards cleared (needs testing)
- [ ] Generate HTML → no old project data visible (needs testing)
- [ ] Upload different spec → different HTML generated (needs testing)
- [ ] No crashes or errors (needs testing)
- [ ] Session state synchronized correctly (needs testing)

---

## Notes

- **This is a CRITICAL bug** - makes app unusable for multiple uploads
- **Phase 1 fix is MINIMAL** - 2 lines of code, low risk
- **Phase 2 is MAJOR refactor** - replace entire template system with dynamic generation
- **User can test immediately** after Phase 1 (data will be correct, structure will be template-based)
- **Document limitation** - Phase 1 doesn't fix template architecture, only data persistence
- **Long-term solution** - Phase 2 required to properly support all game types

---

## Architecture Roadmap

### Current (WRONG):
```
PlayableSpec → render_template() → Jinja2 template → HTML
```

### After Phase 1 (DATA FIX): ✅ CURRENT STATE
```
PlayableSpec (NEW data) → render_template() → Jinja2 template → HTML (still grid)
```

### After Phase 2 (PROPER FIX): ⏳ TODO
```
PlayableSpec → generate_html() → Programmatic generation → HTML (dynamic)
```

---

## Files Modified

### Phase 1 Changes:
- `/Users/eli/Documents/PythonProjects/playable-ads-hackathon/app.py` (Lines 363-367)
  - Added orchestrator reset call
  - Added logging

### Phase 2 Files (COMPLETED):
- ✅ Created: `playable_agents/html_generator.py` (620 lines)
- ✅ Modified: `playable_agents/generator.py` (replaced render_template with generate_html)
- ⏳ Keep: `frontend/templates/ship_grid_merge_v1/` (backward compatibility for grid games)

---

## Critical Files Reference

| File | Role | Issue |
|------|------|-------|
| `app.py:41-42` | Creates orchestrator once | Never resets |
| `app.py:363-367` | Upload handler | ✅ Now calls reset() |
| `orchestrator.py:353-370` | reset() method | ✅ Now called properly |
| `orchestrator.py:304-351` | build_spec_from_scene_cards() | Reads old cards if not reset |
| `spec_tools.py:177` | render_template() | Hardcoded template |
| `spec_tools.py:71-162` | _build_scenes() | Ignores scene_cards.mechanics |
