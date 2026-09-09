# Playable Ads Agent Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** AI-агент, который из PDF ТЗ + картинок генерирует готовый playable ad HTML за 5-10 минут.

**Architecture:** Монолитное Streamlit приложение с OpenAI GPT-4o для анализа документов и изображений. Jinja2 шаблон для рендеринга HTML. Все ассеты inline (base64).

**Tech Stack:** Python 3.11+, Streamlit, OpenAI API, PyMuPDF, Jinja2, Pydantic

---

## Phase 1: Foundation (0-4 часа)

### Task 1: Project Setup

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `app.py` (scaffold)

**Step 1: Create requirements.txt**

```
streamlit>=1.30.0
openai>=1.10.0
PyMuPDF>=1.23.0
Pillow>=10.2.0
Jinja2>=3.1.3
pydantic>=2.5.0
python-dotenv>=1.0.0
```

**Step 2: Create .env.example**

```
OPENAI_API_KEY=sk-your-key-here
```

**Step 3: Create virtual environment and install deps**

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Step 4: Create minimal app.py scaffold**

```python
import streamlit as st

st.set_page_config(page_title="Playable Ads Generator", layout="wide")
st.title("🎮 Playable Ads Generator")

# Upload section
col1, col2 = st.columns(2)
with col1:
    pdf_file = st.file_uploader("Upload PDF ТЗ", type=["pdf"])
with col2:
    images = st.file_uploader("Upload Images", type=["jpg", "png"], accept_multiple_files=True)

st.info("Agent will be implemented here...")
```

**Step 5: Run to verify**

```bash
streamlit run app.py
```

---

### Task 2: Data Models

**Files:**
- Create: `models.py`

**Step 1: Create Pydantic models**

```python
from pydantic import BaseModel
from typing import List, Dict, Optional

class DraftBrief(BaseModel):
    """Extracted info from PDF"""
    title: str = ""
    networks: List[str] = []  # ["applovin", "unity"]
    languages: List[str] = []  # ["RU", "EN"]
    scenes: List[Dict] = []
    copy_texts: Dict[str, str] = {}
    unknowns: List[str] = []

class AssetMapping(BaseModel):
    """Image classification results"""
    backgrounds: List[Dict] = []
    ui_screens: List[Dict] = []
    characters: List[Dict] = []
    icons: List[Dict] = []

class PlayableSpec(BaseModel):
    """Complete playable specification"""
    meta: Dict = {}
    mraid: Dict = {}
    layout: Dict = {}
    assets: Dict = {}
    scenes: List[Dict] = []
    copy: Dict[str, str] = {}
```

---

### Task 3: PDF Extraction Tool

**Files:**
- Create: `tools.py`

**Step 1: Implement extract_brief_from_pdf**

```python
import fitz  # PyMuPDF
import base64
from openai import OpenAI
from models import DraftBrief
import json
import os

client = OpenAI()

def extract_brief_from_pdf(pdf_bytes: bytes) -> DraftBrief:
    """Extract brief from PDF using GPT-4"""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    full_text = ""
    for page in doc:
        full_text += page.get_text()

    prompt = f"""Analyze this playable ad specification document.

TEXT:
{full_text[:8000]}

Extract and return JSON:
{{
    "title": "game title",
    "networks": ["applovin", "unity", "mintegral"],
    "languages": ["RU", "EN"],
    "scenes": [{{"id": "scene1", "description": "..."}}],
    "copy_texts": {{"title": "REPAIR YOUR SHIP"}},
    "unknowns": ["missing info list"]
}}"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )

    data = json.loads(response.choices[0].message.content)
    return DraftBrief(**data)
```

---

### Task 4: Image Analysis Tool

**Files:**
- Modify: `tools.py`

**Step 1: Add analyze_images function**

```python
def analyze_images(image_files: list) -> AssetMapping:
    """Classify images using GPT-4V"""
    images_content = []

    for img_file in image_files:
        b64 = base64.b64encode(img_file.read()).decode()
        img_file.seek(0)  # Reset for later use
        images_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
        })

    prompt = """Classify these game assets. For each image, determine:
- background: Full-screen backgrounds
- ui_screen: Complete UI screens (victory, store)
- character: Character sprites
- icon: Small icons

Return JSON:
{
    "backgrounds": [{"index": 0, "role": "battle_bg"}],
    "ui_screens": [{"index": 1, "role": "victory"}],
    "characters": [{"index": 2, "role": "repairer"}],
    "icons": [{"index": 3, "role": "cannon"}]
}"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": [{"type": "text", "text": prompt}] + images_content
        }],
        response_format={"type": "json_object"}
    )

    data = json.loads(response.choices[0].message.content)
    return AssetMapping(**data)
```

---

## Phase 2: Core Agent Logic (4-8 часов)

### Task 5: Question Generation

**Files:**
- Modify: `tools.py`

**Step 1: Add generate_questions function**

```python
def generate_questions(brief: DraftBrief, assets: AssetMapping) -> List[str]:
    """Generate clarifying questions"""
    questions = []

    # Always ask
    if not brief.networks:
        questions.append("Целевая сеть? (AppLovin / Unity / Mintegral)")

    questions.append("Store URLs:\n- Android: \n- iOS: ")

    if len(brief.languages) != 1:
        questions.append("Язык UI? (RU / EN)")

    # Conditional
    if len(assets.backgrounds) > 2:
        questions.append(f"Какие фоны для каких сцен? Найдено {len(assets.backgrounds)}.")

    return questions
```

---

### Task 6: PlayableSpec Generation

**Files:**
- Modify: `tools.py`

**Step 1: Add generate_playable_spec function**

```python
def generate_playable_spec(
    brief: DraftBrief,
    assets: AssetMapping,
    answers: Dict,
    image_files: list
) -> PlayableSpec:
    """Generate complete PlayableSpec"""

    # Encode images to base64
    encoded_assets = {}
    for i, img_file in enumerate(image_files):
        img_file.seek(0)
        b64 = base64.b64encode(img_file.read()).decode()
        encoded_assets[f"img_{i}"] = f"data:image/png;base64,{b64}"

    spec = PlayableSpec(
        meta={
            "title": brief.title or "Playable Ad",
            "language": answers.get("language", "EN"),
            "network": answers.get("network", "unity"),
        },
        mraid={
            "start_gate": ["ready", "viewableChange"],
            "click_url_android": answers.get("store_android", ""),
            "click_url_ios": answers.get("store_ios", "")
        },
        layout={
            "base_resolution": [1080, 1920],
            "orientation": "both"
        },
        assets={"images": encoded_assets},
        scenes=brief.scenes or [
            {"id": "tutorial", "type": "tutorial"},
            {"id": "battle", "type": "battle"},
            {"id": "victory", "type": "victory"}
        ],
        copy=brief.copy_texts
    )

    return spec
```

---

### Task 7: HTML Template

**Files:**
- Create: `templates/ship_grid_merge_v1/template.html`

**Step 1: Create template directory**

```bash
mkdir -p templates/ship_grid_merge_v1
```

**Step 2: Create Jinja2 HTML template**

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>{{ meta.title }}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        html, body { width: 100%; height: 100%; overflow: hidden; }
        body {
            font-family: Arial, sans-serif;
            background: #1a1a2e;
            color: white;
            touch-action: none;
        }
        #game-container {
            width: 100%;
            height: 100%;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }
        .scene { display: none; width: 100%; height: 100%; position: absolute; }
        .scene.active { display: flex; flex-direction: column; align-items: center; }

        /* Grid styles */
        .grid-container {
            display: grid;
            grid-template-columns: repeat(3, 80px);
            gap: 10px;
            margin: 20px;
        }
        .grid-cell {
            width: 80px;
            height: 80px;
            border: 2px dashed #4CAF50;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .grid-cell.occupied { border-style: solid; background: rgba(76, 175, 80, 0.2); }

        /* Draggable items */
        .inventory { display: flex; gap: 10px; margin: 20px; }
        .draggable-item {
            width: 70px;
            height: 70px;
            cursor: grab;
            transition: transform 0.2s;
        }
        .draggable-item:active { cursor: grabbing; transform: scale(1.1); }
        .draggable-item.used { opacity: 0.3; pointer-events: none; }

        /* HP bars */
        .hp-container { width: 200px; height: 20px; background: #333; border-radius: 10px; overflow: hidden; }
        .hp-bar { height: 100%; background: linear-gradient(90deg, #4CAF50, #8BC34A); transition: width 0.1s; }
        .hp-bar.enemy { background: linear-gradient(90deg, #f44336, #ff5722); }

        /* CTA button */
        .cta-button {
            padding: 20px 60px;
            font-size: 24px;
            font-weight: bold;
            background: linear-gradient(180deg, #FFD700, #FFA500);
            border: none;
            border-radius: 30px;
            color: #333;
            cursor: pointer;
            animation: pulse 1s infinite;
        }
        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.05); }
        }

        /* Title */
        .scene-title {
            font-size: 28px;
            font-weight: bold;
            text-align: center;
            margin: 20px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
        }
    </style>
</head>
<body>
    <div id="game-container">
        <!-- Scene 1: Tutorial -->
        <div class="scene active" id="scene-tutorial">
            <h1 class="scene-title">{{ copy.get('title', 'REPAIR YOUR SHIP') }}</h1>
            <p>{{ copy.get('subtitle', 'DRAG ITEMS TO THE GRID') }}</p>

            <div class="grid-container" id="grid">
                {% for i in range(6) %}
                <div class="grid-cell" data-index="{{ i }}"></div>
                {% endfor %}
            </div>

            <div class="inventory" id="inventory">
                <img class="draggable-item" src="{{ assets.images.get('img_0', '') }}" data-id="item1" draggable="true">
                <img class="draggable-item" src="{{ assets.images.get('img_1', '') }}" data-id="item2" draggable="true">
            </div>
        </div>

        <!-- Scene 2: Battle -->
        <div class="scene" id="scene-battle">
            <h1 class="scene-title">BATTLE!</h1>

            <div style="margin: 20px;">
                <p>Your Ship</p>
                <div class="hp-container">
                    <div class="hp-bar" id="player-hp" style="width: 100%"></div>
                </div>
            </div>

            <div style="margin: 20px;">
                <p>Enemy Ship</p>
                <div class="hp-container">
                    <div class="hp-bar enemy" id="enemy-hp" style="width: 100%"></div>
                </div>
            </div>
        </div>

        <!-- Scene 3: Victory -->
        <div class="scene" id="scene-victory">
            <h1 class="scene-title">VICTORY!</h1>
            <p style="margin: 20px;">{{ copy.get('victory_text', 'You won! Download the game for more!') }}</p>
            <button class="cta-button" onclick="openStore()">
                {{ copy.get('cta_text', 'DOWNLOAD NOW') }}
            </button>
        </div>
    </div>

    <script>
    // Store URLs
    const STORE_URL_IOS = "{{ mraid.click_url_ios }}";
    const STORE_URL_ANDROID = "{{ mraid.click_url_android }}";

    // MRAID Wrapper
    (function() {
        const hasMraid = typeof mraid !== 'undefined';
        let gameStarted = false;

        window.openStore = function() {
            const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
            const url = isIOS ? STORE_URL_IOS : STORE_URL_ANDROID;
            if (hasMraid) {
                mraid.open(url);
            } else {
                window.open(url, '_blank');
            }
        };

        function startGame() {
            if (gameStarted) return;
            gameStarted = true;
            initGame();
        }

        function onMraidReady() {
            if (mraid.isViewable()) {
                startGame();
            } else {
                mraid.addEventListener('viewableChange', function(v) { if (v) startGame(); });
            }
        }

        if (hasMraid) {
            if (mraid.getState() === 'loading') {
                mraid.addEventListener('ready', onMraidReady);
            } else {
                onMraidReady();
            }
        } else {
            startGame();
        }
    })();

    // Game Logic
    let currentScene = 0;
    const scenes = ['scene-tutorial', 'scene-battle', 'scene-victory'];
    let placedItems = 0;

    function showScene(index) {
        scenes.forEach((id, i) => {
            document.getElementById(id).classList.toggle('active', i === index);
        });
        currentScene = index;

        if (index === 1) startBattle();
    }

    function initGame() {
        // Drag & Drop
        const items = document.querySelectorAll('.draggable-item');
        const cells = document.querySelectorAll('.grid-cell');

        items.forEach(item => {
            item.addEventListener('dragstart', e => {
                e.dataTransfer.setData('text', item.dataset.id);
            });

            // Touch support
            item.addEventListener('touchstart', handleTouchStart);
            item.addEventListener('touchmove', handleTouchMove);
            item.addEventListener('touchend', handleTouchEnd);
        });

        cells.forEach(cell => {
            cell.addEventListener('dragover', e => e.preventDefault());
            cell.addEventListener('drop', e => {
                e.preventDefault();
                if (!cell.classList.contains('occupied')) {
                    const id = e.dataTransfer.getData('text');
                    const item = document.querySelector(`[data-id="${id}"]`);
                    placeItem(item, cell);
                }
            });
        });
    }

    let draggedItem = null;
    let touchClone = null;

    function handleTouchStart(e) {
        draggedItem = e.target;
        touchClone = draggedItem.cloneNode(true);
        touchClone.style.position = 'fixed';
        touchClone.style.pointerEvents = 'none';
        touchClone.style.opacity = '0.8';
        touchClone.style.zIndex = '1000';
        document.body.appendChild(touchClone);
    }

    function handleTouchMove(e) {
        if (!touchClone) return;
        e.preventDefault();
        const touch = e.touches[0];
        touchClone.style.left = (touch.clientX - 35) + 'px';
        touchClone.style.top = (touch.clientY - 35) + 'px';
    }

    function handleTouchEnd(e) {
        if (!touchClone) return;
        const touch = e.changedTouches[0];
        const cell = document.elementFromPoint(touch.clientX, touch.clientY);

        if (cell && cell.classList.contains('grid-cell') && !cell.classList.contains('occupied')) {
            placeItem(draggedItem, cell);
        }

        touchClone.remove();
        touchClone = null;
        draggedItem = null;
    }

    function placeItem(item, cell) {
        const img = document.createElement('img');
        img.src = item.src;
        img.style.width = '60px';
        img.style.height = '60px';
        cell.appendChild(img);
        cell.classList.add('occupied');
        item.classList.add('used');

        placedItems++;
        if (placedItems >= 2) {
            setTimeout(() => showScene(1), 500);
        }
    }

    // Battle
    let playerHP = 100;
    let enemyHP = 100;
    let battleInterval;

    function startBattle() {
        playerHP = 100;
        enemyHP = 100;

        battleInterval = setInterval(() => {
            // Enemy attacks
            playerHP = Math.max(0, playerHP - 3);
            // Player repairs + attacks
            playerHP = Math.min(100, playerHP + 2);
            enemyHP = Math.max(0, enemyHP - 5);

            document.getElementById('player-hp').style.width = playerHP + '%';
            document.getElementById('enemy-hp').style.width = enemyHP + '%';

            if (enemyHP <= 0) {
                clearInterval(battleInterval);
                setTimeout(() => showScene(2), 500);
            }
        }, 100);
    }
    </script>
</body>
</html>
```

---

### Task 8: Render Tool

**Files:**
- Modify: `tools.py`

**Step 1: Add render_playable function**

```python
from jinja2 import Environment, FileSystemLoader

def render_playable(spec: PlayableSpec) -> str:
    """Render HTML from PlayableSpec using Jinja2"""
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("ship_grid_merge_v1/template.html")

    html = template.render(
        meta=spec.meta,
        mraid=spec.mraid,
        layout=spec.layout,
        assets=spec.assets,
        scenes=spec.scenes,
        copy=spec.copy
    )

    return html
```

---

### Task 9: Validation Tool

**Files:**
- Modify: `tools.py`

**Step 1: Add validate_playable function**

```python
import re

def validate_playable(html: str) -> Dict:
    """Validate playable HTML"""
    result = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "size_kb": len(html.encode('utf-8')) / 1024
    }

    # Size check
    if result["size_kb"] > 5000:
        result["valid"] = False
        result["errors"].append(f"Size {result['size_kb']:.0f}KB > 5MB")

    # External refs (except store URLs in mraid.open)
    if re.search(r'(src|href)=["\']https?://', html):
        # Check if it's only in mraid.open context
        matches = re.findall(r'(src|href)=["\']https?://[^"\']+', html)
        for m in matches:
            if 'play.google.com' not in m and 'apps.apple.com' not in m:
                result["valid"] = False
                result["errors"].append(f"External ref: {m[:50]}")

    # MRAID checks
    if "mraid.getState" not in html:
        result["warnings"].append("MRAID ready gate may be missing")

    if "viewableChange" not in html:
        result["warnings"].append("viewableChange handler may be missing")

    return result
```

---

## Phase 3: Streamlit Integration (8-12 часов)

### Task 10: Complete Streamlit App

**Files:**
- Modify: `app.py`

**Step 1: Implement full app with agent flow**

```python
import streamlit as st
from dotenv import load_dotenv
import tempfile
import os

load_dotenv()

from tools import (
    extract_brief_from_pdf,
    analyze_images,
    generate_questions,
    generate_playable_spec,
    render_playable,
    validate_playable
)
from models import DraftBrief, AssetMapping

st.set_page_config(page_title="Playable Ads Generator", layout="wide")
st.title("🎮 Playable Ads Generator")

# Session state
if "step" not in st.session_state:
    st.session_state.step = "upload"
if "brief" not in st.session_state:
    st.session_state.brief = None
if "assets" not in st.session_state:
    st.session_state.assets = None
if "html" not in st.session_state:
    st.session_state.html = None

# Step 1: Upload
if st.session_state.step == "upload":
    st.header("1. Upload Files")

    col1, col2 = st.columns(2)
    with col1:
        pdf_file = st.file_uploader("PDF ТЗ", type=["pdf"])
    with col2:
        images = st.file_uploader("Images", type=["jpg", "png"], accept_multiple_files=True)

    if st.button("Analyze", disabled=not (pdf_file and images)):
        with st.spinner("Analyzing PDF..."):
            st.session_state.brief = extract_brief_from_pdf(pdf_file.read())

        with st.spinner("Analyzing images..."):
            st.session_state.assets = analyze_images(images)
            st.session_state.images = images

        st.session_state.questions = generate_questions(
            st.session_state.brief,
            st.session_state.assets
        )
        st.session_state.step = "questions"
        st.rerun()

# Step 2: Questions
elif st.session_state.step == "questions":
    st.header("2. Answer Questions")

    st.json(st.session_state.brief.model_dump())

    answers = {}

    answers["network"] = st.selectbox("Target Network", ["unity", "applovin", "mintegral"])
    answers["language"] = st.selectbox("Language", ["EN", "RU"])
    answers["store_android"] = st.text_input("Android Store URL", "https://play.google.com/store/apps/...")
    answers["store_ios"] = st.text_input("iOS Store URL", "https://apps.apple.com/...")

    if st.button("Generate Playable"):
        with st.spinner("Generating..."):
            spec = generate_playable_spec(
                st.session_state.brief,
                st.session_state.assets,
                answers,
                st.session_state.images
            )
            st.session_state.html = render_playable(spec)
            st.session_state.validation = validate_playable(st.session_state.html)

        st.session_state.step = "preview"
        st.rerun()

# Step 3: Preview & Download
elif st.session_state.step == "preview":
    st.header("3. Preview & Download")

    # Validation results
    val = st.session_state.validation
    if val["valid"]:
        st.success(f"✅ Valid! Size: {val['size_kb']:.1f} KB")
    else:
        st.error("❌ Validation failed:")
        for e in val["errors"]:
            st.error(e)

    for w in val.get("warnings", []):
        st.warning(w)

    # Preview
    st.subheader("Preview")
    st.components.v1.html(st.session_state.html, height=600, scrolling=True)

    # Download
    st.download_button(
        "📥 Download index.html",
        st.session_state.html,
        "index.html",
        "text/html"
    )

    if st.button("Start Over"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
```

---

## Phase 4: Testing & Polish (12-14 часов)

### Task 11: Manual Testing Checklist

**Run through:**

1. Upload sample PDF + images
2. Verify questions appear
3. Fill answers and generate
4. Check preview renders correctly
5. Download HTML
6. Open in browser - verify:
   - Drag & drop works
   - Touch works on mobile
   - Battle animates
   - CTA button opens store
7. Check file size < 5MB
8. Verify no external refs: `grep -E 'src="https?://' index.html`

---

### Task 12: Fix Any Issues

Based on testing, fix bugs. Common issues:
- Touch events not working → check touchstart/touchmove/touchend handlers
- Images not showing → check base64 encoding
- MRAID not working → test without MRAID first (dev mode)

---

## Summary

**Total estimated time: 12-14 hours**

**Files created:**
- `requirements.txt`
- `.env.example`
- `app.py` (main Streamlit app)
- `models.py` (Pydantic models)
- `tools.py` (5 agent tools)
- `templates/ship_grid_merge_v1/template.html`

**Key shortcuts for hackathon:**
- No FastAPI/separate backend - all in Streamlit
- No minification - not critical for MVP
- Single template only
- Minimal error handling
- No tests (manual testing only)

**Run command:**
```bash
source venv/bin/activate
streamlit run app.py
```
