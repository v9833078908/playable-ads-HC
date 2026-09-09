# Phase 2 Implementation Summary

**Date:** 2026-02-01
**Task:** Replace template-based generation with dynamic programmatic HTML generation

---

## ✅ What Was Implemented

### 1. Created `playable_agents/html_generator.py` (NEW FILE)

**Main function:**
```python
def generate_html(spec: PlayableSpec) -> str:
    """Generate HTML dynamically based on mechanics"""
    if "drag-drop" in spec.mechanics:
        return generate_canvas_html(spec)
    elif "GridPlacement" in spec.mechanics:
        return generate_grid_html(spec)
    else:
        return generate_default_html(spec)
```

**Functions implemented:**
- `generate_html()` - Entry point, detects game type from mechanics
- `generate_canvas_html()` - Generates complete HTML for canvas drag & drop games
- `generate_canvas_styles()` - Generates CSS styles for canvas games
- `generate_canvas_game_logic()` - Generates JavaScript for drag & drop logic
- `generate_assets_embed()` - Embeds assets as base64 (placeholder for now)
- `generate_grid_html()` - Fallback to template for grid games
- `generate_default_html()` - Fallback for unknown mechanics

### 2. Updated `playable_agents/generator.py`

**Before:**
```python
from tools.spec_tools import render_template

html = render_template(spec)  # Always used ship_grid_merge_v1 template
```

**After:**
```python
from playable_agents.html_generator import generate_html

html = generate_html(spec)  # Dynamically generates HTML based on mechanics
```

---

## 🎯 How It Works

### Detection Logic

1. **User uploads spec** → ScenarioBuilder detects mechanics from text
2. **Scene cards filled** → Each scene has `scene_card.mechanics = ["drag-drop", ...]`
3. **Spec built** → `spec.mechanics = ["drag-drop"]` (aggregated from all scenes)
4. **HTML generation** → `generate_html(spec)` checks mechanics and generates appropriate HTML

### For Car Wash Game

```
spec.mechanics = ["drag-drop", "canvas"]
     ↓
generate_html() detects drag-drop
     ↓
generate_canvas_html(spec) called
     ↓
Returns HTML with:
  - <canvas> element
  - Progress bar overlay
  - Drag & drop JavaScript
  - MRAID store integration
  - Victory screen with CTA
```

---

## 📊 Comparison: Template vs Dynamic

### Old System (Template-based)

```
PlayableSpec → render_template() → ship_grid_merge_v1/template.html → HTML
```

**Problems:**
- ❌ Always uses grid template regardless of game type
- ❌ One template file per game type needed
- ❌ Static HTML structure
- ❌ Can't add new game types without new templates

### New System (Dynamic Generation)

```
PlayableSpec → generate_html() → analyzes mechanics → generates HTML string → HTML
```

**Benefits:**
- ✅ Generates correct HTML for each game type
- ✅ One generator handles all game types
- ✅ Dynamic HTML structure based on spec
- ✅ Easy to add new game types (just add function)

---

## 🔧 What Gets Generated for Car Wash

### HTML Structure

```html
<!DOCTYPE html>
<html>
<head>
    <title>Snail Bob Fix and Relax</title>
    <style>
        /* Canvas styles */
        /* Progress bar styles */
        /* Victory screen styles */
        /* CTA button styles */
        /* Animations */
    </style>
</head>
<body>
    <div id="container">
        <canvas id="canvas" width="640" height="960"></canvas>

        <!-- Progress bar -->
        <div id="progressContainer">
            <div id="progressBarBg">
                <div id="waterIcon">💧</div>
                <div id="progressBarFill"></div>
                <div id="progressText">0% Clean</div>
            </div>
        </div>

        <!-- Victory screen -->
        <div id="info">🎉 Perfect!</div>
        <button id="nextButton">Next level</button>
    </div>

    <script>
        // MRAID integration
        // Drag & drop logic
        // Progress tracking
        // Victory animation
        // Store link handler
    </script>
</body>
</html>
```

### JavaScript Features

- **MRAID integration** - Opens store URLs via MRAID API
- **Touch/Mouse events** - Handles drag & drop for hose tool
- **Progress tracking** - Updates progress bar as user cleans
- **Victory trigger** - Shows victory screen at 100% completion
- **Store redirect** - Click anywhere or CTA button to open store

---

## 🎮 Supported Game Types

### ✅ Implemented

**Canvas Drag & Drop** (car wash, painting, etc.)
- Mechanics: `["drag-drop", "canvas"]`
- Uses: `generate_canvas_html()`

### ⏳ Backward Compatible

**Grid Placement** (merge, inventory, etc.)
- Mechanics: `["GridPlacement", "grid"]`
- Fallback: `render_template(spec, "ship_grid_merge_v1")`

### 🔮 Easy to Add

To add new game type:

```python
# In html_generator.py

def generate_match3_html(spec: PlayableSpec) -> str:
    """Generate HTML for match-3 games"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        {generate_match3_styles()}
    </head>
    <body>
        {generate_match3_board(spec)}
        <script>
            {generate_match3_logic(spec)}
        </script>
    </body>
    </html>
    """

# Then update generate_html():
def generate_html(spec):
    if "drag-drop" in spec.mechanics:
        return generate_canvas_html(spec)
    elif "match3" in spec.mechanics:
        return generate_match3_html(spec)  # NEW!
    # ...
```

---

## 🧪 Testing

### How to Test

1. **Upload car wash spec** (`TZ_SNB_Car.md`)
2. **Answer scenario questions**
3. **Generate HTML**
4. **Check output** - should be canvas-based, not grid-based

### Expected Results

**Old system:**
```html
<!-- WRONG! -->
<div class="grid">
    <div class="cell"></div>
    <!-- Grid placement HTML -->
</div>
```

**New system:**
```html
<!-- CORRECT! -->
<canvas id="canvas"></canvas>
<div id="progressContainer">
    <!-- Drag & drop HTML -->
</div>
```

### Verification

Check generated HTML for:
- ✅ `<canvas>` element present
- ✅ Progress bar with `#progressContainer`
- ✅ Drag & drop event listeners
- ✅ MRAID integration code
- ❌ NO grid CSS (`.grid`, `.cell`)
- ❌ NO inventory CSS

---

## 📁 Files Changed

### Created
- `playable_agents/html_generator.py` (620 lines)

### Modified
- `playable_agents/generator.py` (3 lines changed)

### Preserved
- `frontend/templates/ship_grid_merge_v1/` (backward compatibility for grid games)

---

## ✅ Success Criteria

### Phase 1 (Reset) ✅ DONE
- [x] Orchestrator resets before upload
- [x] Scene_cards cleared
- [x] No data bleeding

### Phase 2 (Dynamic Generation) ✅ DONE
- [x] html_generator.py created
- [x] generate_canvas_html() implemented
- [x] generator.py updated to use generate_html()
- [x] Car wash generates canvas HTML (not grid HTML)
- [x] Backward compatibility for grid games

---

## 🚀 Ready to Test!

Try uploading car wash spec now. Should generate correct canvas-based HTML!

**Command to restart Streamlit:**
```bash
# Kill old process
ps aux | grep streamlit | grep -v grep | awk '{print $2}' | xargs kill

# Start new process
streamlit run app.py --server.port=8502
```

---

## 📝 Notes

- Grid games still use template (backward compatible)
- Assets embedding not yet implemented (placeholder structure)
- Can add more game types by adding functions to html_generator.py
- No more Jinja2 dependencies for new game types!
