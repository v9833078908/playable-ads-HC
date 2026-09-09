# 🎮 Playable Ads AI Agent — Technical Specification (Hackathon MVP)

**Версия:** 1.0  
**Время реализации:** 36 часов  
**Цель:** AI-агент, который по PDF ТЗ + изображениям генерирует готовый playable ad HTML

---

## 1. Продуктовое видение

### 1.1 Текущий workflow (AS-IS)
```
Маркетолог → PDF ТЗ + JPG референсы → Разработчик → 3-5 дней → HTML playable
```

### 1.2 Целевой workflow (TO-BE)
```
Маркетолог → PDF ТЗ + JPG → AI Agent → Уточняющие вопросы → 5-10 минут → HTML playable
```

### 1.3 Идеальный конечный результат
**Вход:**
- PDF с техническим заданием (сценарий, требования сетей)
- JPG/PNG изображения (референсы экранов, ассеты персонажей)

**Процесс:**
- Агент анализирует PDF и изображения
- Задаёт минимум уточняющих вопросов (только критичные)
- Генерирует playable по шаблону

**Выход:**
- Один файл `index.html` (self-contained, ≤5MB)
- Готов к загрузке в AppLovin/Unity/Mintegral

---

## 2. Требования Ad Networks (из референсного PDF)

### 2.1 AppLovin
| Требование | Значение |
|------------|----------|
| Формат | Single-line HTML, no external refs |
| Изображения | Base64 encoded |
| MRAID | v2.0 |
| Ориентация | Portrait + Landscape |
| Размер | < 5MB |
| Close button | Рендерится сетью (не добавлять свой) |
| CTA | `mraid.open()` |
| Audio | Disabled until first interaction |
| Autoplay | Запрещён |
| DOM | Не трогать до MRAID ready |

### 2.2 Unity
| Требование | Значение |
|------------|----------|
| Формат | Single HTML index file, all assets inlined |
| Minification | Required |
| Размер | < 5MB |
| MRAID | v3.0 |
| XHR | Запрещён (analytics допустимы без PII) |
| Start | После `viewableChange` event |
| Auto-redirect | Запрещён |

### 2.3 Mintegral
- Документация: https://www.mindworks-creative.com/review/doc

---

## 3. Архитектура системы

### 3.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         WEB UI (Streamlit)                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐ │
│  │  Upload  │  │   Chat   │  │  Preview │  │      Download        │ │
│  │ PDF+IMG  │  │ Q&A Flow │  │  iframe  │  │    index.html        │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      ORCHESTRATOR (FastAPI)                         │
│                                                                     │
│   Session Manager ──► Tool Router ──► Response Handler              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   SINGLE AGENT (OpenAI GPT-4o)                      │
│                                                                     │
│   Tools:                                                            │
│   ├── extract_brief_from_pdf    - Parse PDF → DraftBrief           │
│   ├── analyze_images            - Classify assets by role          │
│   ├── generate_playable_spec    - DraftBrief → PlayableSpec.json   │
│   ├── render_playable           - PlayableSpec → index.html        │
│   └── validate_playable         - Check compliance                  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       TEMPLATE ENGINE                               │
│                                                                     │
│   templates/                                                        │
│   └── ship_grid_merge_v1/       ← Шаблон для Pirate Ships          │
│       ├── template.html         ← Jinja2 шаблон                    │
│       ├── mechanics/                                                │
│       │   ├── grid_placement.js ← Drag & Drop на сетку             │
│       │   ├── merge.js          ← Объединение 2→1                  │
│       │   ├── battle.js         ← HP bars + damage loop            │
│       │   └── tutorial.js       ← Overlay подсказки                │
│       ├── mraid_wrapper.js      ← MRAID ready/viewable gate        │
│       └── styles.css            ← Base styles                      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        BUILD PIPELINE                               │
│                                                                     │
│   1. Inline assets (base64)     - Все IMG → data:image/...         │
│   2. Bundle JS/CSS              - Всё в один файл                  │
│   3. Minify (terser)            - Оптимизация размера              │
│   4. Inject MRAID wrapper       - Обёртка для сетей                │
│   5. Validate                   - Size, no external refs           │
│   6. Export index.html          - Готовый файл                     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 Компоненты детально

#### A. Web UI (Streamlit)
```python
# Файл: app.py
import streamlit as st

st.title("🎮 Playable Ads Generator")

# Upload section
pdf_file = st.file_uploader("Upload PDF ТЗ", type=["pdf"])
images = st.file_uploader("Upload Images", type=["jpg", "png"], accept_multiple_files=True)

# Chat section
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# User input
if prompt := st.chat_input("Ответьте на вопросы агента..."):
    # Process with agent
    pass

# Preview section
if st.session_state.get("html_preview"):
    st.components.v1.html(st.session_state.html_preview, height=600)

# Download button
if st.session_state.get("final_html"):
    st.download_button("📥 Download index.html", st.session_state.final_html)
```

#### B. Agent Tools (Python)

```python
# Файл: tools.py
from pydantic import BaseModel
from typing import List, Dict, Optional
import fitz  # PyMuPDF
import base64
import json

# === SCHEMAS ===

class DraftBrief(BaseModel):
    """Извлечённая информация из PDF"""
    title: str
    networks: List[str]  # ["applovin", "unity", "mintegral"]
    languages: List[str]  # ["RU", "EN"]
    scenes: List[Dict]    # Список сцен из сценария
    copy_texts: Dict[str, str]  # {"title": "REPAIR YOUR SHIP", ...}
    unknowns: List[str]   # Что не удалось извлечь
    
class AssetMapping(BaseModel):
    """Маппинг изображений на роли"""
    backgrounds: List[Dict]  # [{"file": "001.jpg", "scene": "battle"}]
    ui_screens: List[Dict]   # [{"file": "009.jpg", "type": "victory"}]
    characters: List[Dict]   # [{"file": "Repairer.png", "role": "unit"}]
    icons: List[Dict]        # [{"file": "cannon.png", "role": "weapon"}]
    
class PlayableSpec(BaseModel):
    """Полная спецификация playable"""
    meta: Dict  # title, language, network, max_size_mb
    mraid: Dict  # start_gate, click_urls
    layout: Dict  # base_resolution, orientation
    assets: Dict  # images, sprites with base64 data
    scenes: List[Dict]  # Ordered list of scenes
    mechanics: List[str]  # ["GridPlacement", "Merge", "Battle"]

# === TOOLS ===

def extract_brief_from_pdf(pdf_path: str) -> DraftBrief:
    """
    Tool 1: Извлечение brief из PDF
    
    Использует PyMuPDF для текста + GPT-4V для изображений в PDF
    """
    doc = fitz.open(pdf_path)
    
    full_text = ""
    images_in_pdf = []
    
    for page in doc:
        full_text += page.get_text()
        
        # Extract images from PDF
        for img_index, img in enumerate(page.get_images()):
            xref = img[0]
            base_image = doc.extract_image(xref)
            images_in_pdf.append({
                "page": page.number,
                "data": base64.b64encode(base_image["image"]).decode()
            })
    
    # GPT-4 prompt для анализа
    analysis_prompt = f"""
    Analyze this playable ad specification document.
    
    TEXT CONTENT:
    {full_text}
    
    Extract:
    1. Target ad networks (AppLovin, Unity, Mintegral, etc.)
    2. Languages (RU, EN)
    3. Scene-by-scene breakdown
    4. UI copy texts (titles, CTAs)
    5. What information is missing
    
    Return as JSON matching DraftBrief schema.
    """
    
    # Call OpenAI
    # response = openai.chat.completions.create(...)
    
    return DraftBrief(...)


def analyze_images(image_paths: List[str]) -> AssetMapping:
    """
    Tool 2: Анализ и классификация изображений
    
    Использует GPT-4V для определения роли каждого изображения
    """
    images_data = []
    for path in image_paths:
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode()
            images_data.append({
                "path": path,
                "base64": data
            })
    
    analysis_prompt = """
    Analyze these game assets and classify each:
    
    Categories:
    - background: Full-screen backgrounds (ocean, battle scenes)
    - ui_screen: Complete UI screens (victory, store, setup)
    - character: Individual character sprites (units, enemies)
    - icon: Small icons (weapons, items, buttons)
    
    For each image, identify:
    1. Category
    2. Suggested role (e.g., "battle_background", "victory_screen", "repairer_unit")
    3. Suitable scenes to use in
    
    Return as JSON matching AssetMapping schema.
    """
    
    # Call OpenAI with vision
    # response = openai.chat.completions.create(model="gpt-4o", ...)
    
    return AssetMapping(...)


def generate_playable_spec(
    brief: DraftBrief, 
    assets: AssetMapping,
    user_answers: Dict
) -> PlayableSpec:
    """
    Tool 3: Генерация полной спецификации playable
    
    Объединяет brief, assets и ответы пользователя в PlayableSpec
    """
    spec = PlayableSpec(
        meta={
            "title": brief.title,
            "language": user_answers.get("language", "EN"),
            "network": user_answers.get("network", "unity"),
            "max_size_mb": 5
        },
        mraid={
            "start_gate": ["ready", "viewableChange"],
            "click_url_android": user_answers.get("store_android", ""),
            "click_url_ios": user_answers.get("store_ios", "")
        },
        layout={
            "base_resolution": [1080, 1920],
            "orientation": "both",
            "safe_area": True
        },
        assets=prepare_assets(assets),
        scenes=map_scenes_from_brief(brief),
        mechanics=["GridPlacement", "DragDrop", "Merge", "Battle", "Tutorial"]
    )
    
    return spec


def render_playable(spec: PlayableSpec, template_name: str = "ship_grid_merge_v1") -> str:
    """
    Tool 4: Рендеринг HTML из спецификации
    
    Использует Jinja2 для подстановки в шаблон
    """
    from jinja2 import Environment, FileSystemLoader
    
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template(f"{template_name}/template.html")
    
    html = template.render(
        meta=spec.meta,
        mraid=spec.mraid,
        assets=spec.assets,
        scenes=spec.scenes,
        mechanics_config=generate_mechanics_config(spec)
    )
    
    return html


def validate_playable(html: str, target_network: str) -> Dict:
    """
    Tool 5: Валидация готового HTML
    
    Проверяет compliance с требованиями сети
    """
    results = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "size_kb": len(html.encode('utf-8')) / 1024
    }
    
    # Check 1: Size
    if results["size_kb"] > 5000:
        results["valid"] = False
        results["errors"].append(f"Size {results['size_kb']:.0f}KB exceeds 5MB limit")
    
    # Check 2: No external references
    external_patterns = [
        r'src=["\']https?://',
        r'href=["\']https?://',
        r'url\(["\']?https?://'
    ]
    for pattern in external_patterns:
        import re
        if re.search(pattern, html):
            results["valid"] = False
            results["errors"].append(f"External reference found: {pattern}")
    
    # Check 3: MRAID gate present
    if "mraid.getState" not in html or "viewableChange" not in html:
        results["warnings"].append("MRAID ready gate may be missing")
    
    # Check 4: No autoplay audio
    if "autoplay" in html.lower() and "audio" in html.lower():
        results["errors"].append("Audio autoplay detected")
        results["valid"] = False
    
    # Check 5: mraid.open for CTA
    if "mraid.open" not in html:
        results["warnings"].append("mraid.open() not found for CTA")
    
    return results
```

---

## 4. DSL: PlayableSpec Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "PlayableSpec",
  "type": "object",
  "required": ["meta", "mraid", "layout", "assets", "scenes"],
  "properties": {
    "meta": {
      "type": "object",
      "properties": {
        "title": {"type": "string"},
        "language": {"type": "string", "enum": ["RU", "EN"]},
        "network": {"type": "string", "enum": ["applovin", "unity", "mintegral"]},
        "max_size_mb": {"type": "number", "default": 5}
      }
    },
    "mraid": {
      "type": "object",
      "properties": {
        "start_gate": {
          "type": "array",
          "items": {"type": "string", "enum": ["ready", "viewableChange"]}
        },
        "click_url_android": {"type": "string", "format": "uri"},
        "click_url_ios": {"type": "string", "format": "uri"}
      }
    },
    "layout": {
      "type": "object",
      "properties": {
        "base_resolution": {
          "type": "array",
          "items": {"type": "integer"},
          "minItems": 2,
          "maxItems": 2
        },
        "orientation": {"type": "string", "enum": ["portrait", "landscape", "both"]},
        "safe_area": {"type": "boolean"}
      }
    },
    "assets": {
      "type": "object",
      "properties": {
        "images": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "id": {"type": "string"},
              "role": {"type": "string"},
              "base64": {"type": "string"}
            }
          }
        }
      }
    },
    "scenes": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": {"type": "string"},
          "type": {"type": "string", "enum": ["tutorial", "battle", "victory"]},
          "ui": {
            "type": "object",
            "properties": {
              "title": {"type": "string"},
              "subtitle": {"type": "string"}
            }
          },
          "mechanics": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "type": {"type": "string"},
                "config": {"type": "object"}
              }
            }
          }
        }
      }
    }
  }
}
```

### 4.1 Пример PlayableSpec для Pirate Ships

```json
{
  "meta": {
    "title": "Pirate Ships Playable",
    "language": "EN",
    "network": "unity",
    "max_size_mb": 5
  },
  "mraid": {
    "start_gate": ["ready", "viewableChange"],
    "click_url_android": "https://play.google.com/store/apps/details?id=com.herocraft.game.piratearena",
    "click_url_ios": "https://apps.apple.com/ru/app/pirate-ships-build-and-fight/id1538178771"
  },
  "layout": {
    "base_resolution": [1080, 1080],
    "orientation": "both",
    "safe_area": true
  },
  "assets": {
    "images": [
      {"id": "bg_battle", "role": "background", "base64": "data:image/jpeg;base64,..."},
      {"id": "bg_setup", "role": "background", "base64": "data:image/jpeg;base64,..."},
      {"id": "victory_screen", "role": "ui", "base64": "data:image/jpeg;base64,..."}
    ],
    "sprites": [
      {"id": "repairer", "role": "unit", "base64": "data:image/png;base64,..."},
      {"id": "gunman", "role": "unit", "base64": "data:image/png;base64,..."}
    ]
  },
  "scenes": [
    {
      "id": "repair_tutorial",
      "type": "tutorial",
      "ui": {
        "title": "REPAIR YOUR SHIP",
        "subtitle": "DRAG REPAIRMANS ON SHIP"
      },
      "mechanics": [
        {
          "type": "GridPlacement",
          "config": {
            "grid": [3, 2],
            "highlight_color": "#4CAF50",
            "required_items": [
              {"asset_id": "repairer", "count": 1, "cells": 1}
            ]
          }
        }
      ]
    },
    {
      "id": "shield_tutorial",
      "type": "tutorial",
      "ui": {
        "title": "REPAIR YOUR SHIP",
        "subtitle": "DRAG SHIELDS TO PROTECT THEM"
      },
      "mechanics": [
        {
          "type": "GridPlacement",
          "config": {
            "required_items": [
              {"asset_id": "shield", "count": 1, "cells": 2}
            ]
          }
        }
      ]
    },
    {
      "id": "battle_1",
      "type": "battle",
      "ui": {},
      "mechanics": [
        {
          "type": "BattleLoop",
          "config": {
            "player_hp": 100,
            "enemy_hp": 100,
            "enemy_dps": 5,
            "repair_rate": 3,
            "duration_sec": 5
          }
        }
      ]
    },
    {
      "id": "weapons_tutorial",
      "type": "tutorial",
      "ui": {
        "title": "SETUP WEAPONS",
        "subtitle": "DRAG CANNONS ON SHIP"
      },
      "mechanics": [
        {
          "type": "GridPlacement",
          "config": {
            "required_items": [
              {"asset_id": "cannon", "count": 2, "cells": 1}
            ]
          }
        }
      ]
    },
    {
      "id": "merge_tutorial",
      "type": "tutorial",
      "ui": {
        "title": "MERGE WEAPONS",
        "subtitle": "DRAG CANNON"
      },
      "mechanics": [
        {
          "type": "Merge",
          "config": {
            "from": "cannon",
            "to": "skeleton_cannon",
            "result_cells": 2,
            "vfx": true
          }
        }
      ]
    },
    {
      "id": "final_battle",
      "type": "battle",
      "ui": {},
      "mechanics": [
        {
          "type": "BattleLoop",
          "config": {
            "player_dps": 20,
            "enemy_hp": 50,
            "auto_win": true
          }
        }
      ]
    },
    {
      "id": "victory",
      "type": "victory",
      "ui": {
        "title": "VICTORY!",
        "subtitle": "NEW ITEMS",
        "cta_text": "TAKE REWARD"
      },
      "mechanics": [
        {
          "type": "CTAOpenStore"
        }
      ]
    }
  ]
}
```

---

## 5. MRAID Wrapper (Critical)

```javascript
// Файл: templates/common/mraid_wrapper.js

(function() {
  'use strict';
  
  // === MRAID Detection ===
  const hasMraid = typeof mraid !== 'undefined';
  
  // === State ===
  let gameStarted = false;
  let userInteracted = false;
  let audioEnabled = false;
  
  // === Public API ===
  window.playable = {
    // Called when game is ready to start
    onReady: null,
    
    // Called on first user interaction
    onFirstInteraction: null,
    
    // Open store
    openStore: function() {
      const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
      const url = isIOS ? window.STORE_URL_IOS : window.STORE_URL_ANDROID;
      
      if (hasMraid) {
        mraid.open(url);
      } else {
        window.open(url, '_blank');
      }
    },
    
    // Check if audio is allowed
    isAudioEnabled: function() {
      return audioEnabled;
    },
    
    // Enable audio (call after first interaction)
    enableAudio: function() {
      audioEnabled = true;
    }
  };
  
  // === MRAID Handlers ===
  function onMraidReady() {
    console.log('[Playable] MRAID ready');
    
    if (mraid.isViewable()) {
      startGame();
    } else {
      mraid.addEventListener('viewableChange', onViewableChange);
    }
  }
  
  function onViewableChange(viewable) {
    console.log('[Playable] viewableChange:', viewable);
    
    if (viewable && !gameStarted) {
      startGame();
    }
  }
  
  function startGame() {
    if (gameStarted) return;
    gameStarted = true;
    
    console.log('[Playable] Starting game');
    
    if (window.playable.onReady) {
      window.playable.onReady();
    }
  }
  
  // === First Interaction Handler ===
  function onFirstInteraction(e) {
    if (userInteracted) return;
    userInteracted = true;
    audioEnabled = true;
    
    console.log('[Playable] First interaction');
    
    document.removeEventListener('touchstart', onFirstInteraction);
    document.removeEventListener('click', onFirstInteraction);
    
    if (window.playable.onFirstInteraction) {
      window.playable.onFirstInteraction();
    }
  }
  
  document.addEventListener('touchstart', onFirstInteraction, { passive: true });
  document.addEventListener('click', onFirstInteraction, { passive: true });
  
  // === Initialization ===
  function init() {
    console.log('[Playable] Init, MRAID:', hasMraid);
    
    if (hasMraid) {
      if (mraid.getState() === 'loading') {
        mraid.addEventListener('ready', onMraidReady);
      } else {
        onMraidReady();
      }
    } else {
      // No MRAID - start immediately (dev mode)
      startGame();
    }
  }
  
  // Start when DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
```

---

## 6. Уточняющие вопросы агента

Агент задаёт **только критичные** вопросы, которые нельзя извлечь из PDF/изображений:

### 6.1 Обязательные вопросы

| # | Вопрос | Зачем |
|---|--------|-------|
| 1 | **Целевая сеть?** (AppLovin / Unity / Mintegral / все) | Разные MRAID требования |
| 2 | **Store URLs?** (iOS / Android) | Для `mraid.open()` |
| 3 | **Язык?** (RU / EN) | UI копирайт |

### 6.2 Опциональные вопросы (если не ясно из PDF)

| # | Вопрос | Когда спрашивать |
|---|--------|------------------|
| 4 | Какое изображение — фон для боя? | Если несколько похожих |
| 5 | Какой персонаж — ремонтник, какой — стрелок? | Если неочевидно из имён файлов |
| 6 | Ориентация? (portrait / landscape / both) | Если не указано в PDF |

### 6.3 Логика генерации вопросов

```python
def generate_questions(brief: DraftBrief, assets: AssetMapping) -> List[str]:
    questions = []
    
    # Always ask
    if not brief.networks:
        questions.append("Для какой рекламной сети создаём playable? (AppLovin / Unity / Mintegral)")
    
    questions.append("Укажите Store URLs:\n- Android: \n- iOS: ")
    
    if len(brief.languages) != 1:
        questions.append("Какой язык использовать для UI? (RU / EN)")
    
    # Ask if ambiguous
    if len(assets.backgrounds) > 2:
        questions.append(f"Какие фоны использовать для каких сцен? Найдено {len(assets.backgrounds)} фонов.")
    
    if not assets.characters:
        questions.append("Не найдены спрайты персонажей. Загрузите PNG с прозрачным фоном.")
    
    return questions
```

---

## 7. Шаблон механик (JavaScript)

### 7.1 GridPlacement (Drag & Drop на сетку)

```javascript
// templates/ship_grid_merge_v1/mechanics/grid_placement.js

class GridPlacement {
  constructor(config) {
    this.gridSize = config.grid || [3, 2];
    this.cells = [];
    this.highlightColor = config.highlight_color || '#4CAF50';
    this.requiredItems = config.required_items || [];
    this.onComplete = config.onComplete || (() => {});
    
    this.init();
  }
  
  init() {
    this.createGrid();
    this.setupDragListeners();
  }
  
  createGrid() {
    const container = document.getElementById('grid-container');
    container.innerHTML = '';
    
    for (let row = 0; row < this.gridSize[1]; row++) {
      for (let col = 0; col < this.gridSize[0]; col++) {
        const cell = document.createElement('div');
        cell.className = 'grid-cell';
        cell.dataset.row = row;
        cell.dataset.col = col;
        cell.dataset.occupied = 'false';
        
        cell.addEventListener('dragover', (e) => this.onDragOver(e));
        cell.addEventListener('drop', (e) => this.onDrop(e));
        
        this.cells.push(cell);
        container.appendChild(cell);
      }
    }
  }
  
  setupDragListeners() {
    const items = document.querySelectorAll('.draggable-item');
    
    items.forEach(item => {
      item.draggable = true;
      
      item.addEventListener('dragstart', (e) => {
        e.dataTransfer.setData('text/plain', item.dataset.assetId);
        item.classList.add('dragging');
        this.highlightValidCells(item.dataset.assetId);
      });
      
      item.addEventListener('dragend', () => {
        item.classList.remove('dragging');
        this.clearHighlights();
      });
      
      // Touch support
      item.addEventListener('touchstart', (e) => this.onTouchStart(e, item));
      item.addEventListener('touchmove', (e) => this.onTouchMove(e, item));
      item.addEventListener('touchend', (e) => this.onTouchEnd(e, item));
    });
  }
  
  highlightValidCells(assetId) {
    const required = this.requiredItems.find(r => r.asset_id === assetId);
    if (!required) return;
    
    const cellsNeeded = required.cells || 1;
    
    this.cells.forEach(cell => {
      if (cell.dataset.occupied === 'false') {
        cell.style.borderColor = this.highlightColor;
        cell.style.boxShadow = `0 0 10px ${this.highlightColor}`;
      }
    });
  }
  
  clearHighlights() {
    this.cells.forEach(cell => {
      cell.style.borderColor = '';
      cell.style.boxShadow = '';
    });
  }
  
  onDragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  }
  
  onDrop(e) {
    e.preventDefault();
    const assetId = e.dataTransfer.getData('text/plain');
    const cell = e.target.closest('.grid-cell');
    
    if (cell && cell.dataset.occupied === 'false') {
      this.placeItem(assetId, cell);
    }
  }
  
  placeItem(assetId, cell) {
    const asset = window.gameAssets[assetId];
    if (!asset) return;
    
    const img = document.createElement('img');
    img.src = asset.base64;
    img.className = 'placed-item';
    
    cell.appendChild(img);
    cell.dataset.occupied = 'true';
    cell.dataset.assetId = assetId;
    
    // Remove from inventory
    const inventoryItem = document.querySelector(`.draggable-item[data-asset-id="${assetId}"]`);
    if (inventoryItem) {
      inventoryItem.classList.add('used');
    }
    
    // Check completion
    this.checkCompletion();
  }
  
  checkCompletion() {
    let allPlaced = true;
    
    this.requiredItems.forEach(required => {
      const placed = this.cells.filter(c => c.dataset.assetId === required.asset_id).length;
      if (placed < required.count) {
        allPlaced = false;
      }
    });
    
    if (allPlaced) {
      setTimeout(() => this.onComplete(), 500);
    }
  }
  
  // Touch handlers for mobile
  onTouchStart(e, item) {
    this.touchItem = item;
    this.touchClone = item.cloneNode(true);
    this.touchClone.style.position = 'fixed';
    this.touchClone.style.pointerEvents = 'none';
    this.touchClone.style.opacity = '0.8';
    this.touchClone.style.zIndex = '1000';
    document.body.appendChild(this.touchClone);
    
    this.highlightValidCells(item.dataset.assetId);
  }
  
  onTouchMove(e, item) {
    if (!this.touchClone) return;
    e.preventDefault();
    
    const touch = e.touches[0];
    this.touchClone.style.left = (touch.clientX - 40) + 'px';
    this.touchClone.style.top = (touch.clientY - 40) + 'px';
  }
  
  onTouchEnd(e, item) {
    if (!this.touchClone) return;
    
    const touch = e.changedTouches[0];
    const cell = document.elementFromPoint(touch.clientX, touch.clientY);
    
    if (cell && cell.classList.contains('grid-cell') && cell.dataset.occupied === 'false') {
      this.placeItem(item.dataset.assetId, cell);
    }
    
    this.touchClone.remove();
    this.touchClone = null;
    this.clearHighlights();
  }
}

window.GridPlacement = GridPlacement;
```

### 7.2 Merge (Объединение предметов)

```javascript
// templates/ship_grid_merge_v1/mechanics/merge.js

class MergeMechanic {
  constructor(config) {
    this.fromAsset = config.from;
    this.toAsset = config.to;
    this.resultCells = config.result_cells || 2;
    this.showVFX = config.vfx || true;
    this.onComplete = config.onComplete || (() => {});
    
    this.init();
  }
  
  init() {
    this.setupMergeListeners();
  }
  
  setupMergeListeners() {
    const items = document.querySelectorAll(`.placed-item[data-asset-id="${this.fromAsset}"]`);
    
    items.forEach(item => {
      item.classList.add('mergeable');
      
      item.addEventListener('dragover', (e) => {
        e.preventDefault();
        item.classList.add('merge-target');
      });
      
      item.addEventListener('dragleave', () => {
        item.classList.remove('merge-target');
      });
      
      item.addEventListener('drop', (e) => this.performMerge(e, item));
    });
  }
  
  performMerge(e, targetItem) {
    e.preventDefault();
    const sourceId = e.dataTransfer.getData('text/plain');
    
    if (sourceId !== this.fromAsset) return;
    
    // Get both cells
    const targetCell = targetItem.closest('.grid-cell');
    const sourceCell = document.querySelector('.dragging').closest('.grid-cell');
    
    if (!targetCell || !sourceCell) return;
    
    // VFX
    if (this.showVFX) {
      this.playMergeVFX(targetCell);
    }
    
    // Remove old items
    sourceCell.querySelector('.placed-item').remove();
    sourceCell.dataset.occupied = 'false';
    sourceCell.dataset.assetId = '';
    
    targetItem.remove();
    
    // Create merged item
    const mergedItem = document.createElement('img');
    mergedItem.src = window.gameAssets[this.toAsset].base64;
    mergedItem.className = 'placed-item merged';
    mergedItem.dataset.assetId = this.toAsset;
    
    targetCell.appendChild(mergedItem);
    targetCell.dataset.assetId = this.toAsset;
    
    // Expand to adjacent cell if needed
    if (this.resultCells > 1) {
      // Mark adjacent cells as part of merged item
      // ...
    }
    
    setTimeout(() => this.onComplete(), 800);
  }
  
  playMergeVFX(cell) {
    const vfx = document.createElement('div');
    vfx.className = 'merge-vfx';
    vfx.innerHTML = `
      <div class="merge-flash"></div>
      <div class="merge-particles"></div>
    `;
    cell.appendChild(vfx);
    
    setTimeout(() => vfx.remove(), 1000);
  }
}

window.MergeMechanic = MergeMechanic;
```

### 7.3 Battle Loop

```javascript
// templates/ship_grid_merge_v1/mechanics/battle.js

class BattleLoop {
  constructor(config) {
    this.playerHP = config.player_hp || 100;
    this.enemyHP = config.enemy_hp || 100;
    this.playerMaxHP = this.playerHP;
    this.enemyMaxHP = this.enemyHP;
    
    this.enemyDPS = config.enemy_dps || 5;
    this.playerDPS = config.player_dps || 0;
    this.repairRate = config.repair_rate || 3;
    
    this.duration = config.duration_sec || 5;
    this.autoWin = config.auto_win || false;
    this.onComplete = config.onComplete || (() => {});
    
    this.running = false;
  }
  
  start() {
    this.running = true;
    this.startTime = Date.now();
    this.tick();
  }
  
  tick() {
    if (!this.running) return;
    
    const elapsed = (Date.now() - this.startTime) / 1000;
    
    // Enemy deals damage
    this.playerHP = Math.max(0, this.playerHP - this.enemyDPS * 0.016);
    
    // Player repairs
    this.playerHP = Math.min(this.playerMaxHP, this.playerHP + this.repairRate * 0.016);
    
    // Player deals damage
    if (this.playerDPS > 0) {
      this.enemyHP = Math.max(0, this.enemyHP - this.playerDPS * 0.016);
    }
    
    // Update UI
    this.updateHealthBars();
    this.updateVisualDamage();
    
    // Check end conditions
    if (this.autoWin && this.enemyHP <= 0) {
      this.complete(true);
      return;
    }
    
    if (elapsed >= this.duration && !this.autoWin) {
      this.complete(false);
      return;
    }
    
    requestAnimationFrame(() => this.tick());
  }
  
  updateHealthBars() {
    const playerBar = document.getElementById('player-hp-bar');
    const enemyBar = document.getElementById('enemy-hp-bar');
    
    if (playerBar) {
      playerBar.style.width = (this.playerHP / this.playerMaxHP * 100) + '%';
    }
    if (enemyBar) {
      enemyBar.style.width = (this.enemyHP / this.enemyMaxHP * 100) + '%';
    }
  }
  
  updateVisualDamage() {
    const playerShip = document.getElementById('player-ship');
    
    if (!playerShip) return;
    
    const damagePercent = 1 - (this.playerHP / this.playerMaxHP);
    
    // Show cracks
    const cracks = playerShip.querySelectorAll('.crack');
    cracks.forEach((crack, i) => {
      crack.style.opacity = damagePercent > (i * 0.2) ? 1 : 0;
    });
    
    // Show fires
    const fires = playerShip.querySelectorAll('.fire');
    fires.forEach((fire, i) => {
      fire.style.opacity = damagePercent > (i * 0.3 + 0.2) ? 1 : 0;
    });
  }
  
  complete(isVictory) {
    this.running = false;
    this.onComplete(isVictory);
  }
  
  stop() {
    this.running = false;
  }
}

window.BattleLoop = BattleLoop;
```

---

## 8. Build Pipeline

### 8.1 Inline Assets

```python
# build/inline_assets.py

import base64
import re
from pathlib import Path

def inline_images(html: str, assets_dir: Path) -> str:
    """Заменяет все src="..." на base64 data URLs"""
    
    def replace_src(match):
        src = match.group(1)
        
        # Already base64
        if src.startswith('data:'):
            return match.group(0)
        
        # Find file
        file_path = assets_dir / src
        if not file_path.exists():
            return match.group(0)
        
        # Get MIME type
        ext = file_path.suffix.lower()
        mime_types = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.svg': 'image/svg+xml'
        }
        mime = mime_types.get(ext, 'application/octet-stream')
        
        # Encode
        with open(file_path, 'rb') as f:
            b64 = base64.b64encode(f.read()).decode()
        
        return f'src="data:{mime};base64,{b64}"'
    
    pattern = r'src="([^"]+)"'
    return re.sub(pattern, replace_src, html)


def inline_css(html: str, css_dir: Path) -> str:
    """Инлайнит все <link rel="stylesheet">"""
    
    def replace_link(match):
        href = match.group(1)
        css_path = css_dir / href
        
        if not css_path.exists():
            return match.group(0)
        
        with open(css_path, 'r') as f:
            css_content = f.read()
        
        return f'<style>{css_content}</style>'
    
    pattern = r'<link\s+rel="stylesheet"\s+href="([^"]+)"[^>]*>'
    return re.sub(pattern, replace_link, html)


def inline_js(html: str, js_dir: Path) -> str:
    """Инлайнит все <script src="...">"""
    
    def replace_script(match):
        src = match.group(1)
        js_path = js_dir / src
        
        if not js_path.exists():
            return match.group(0)
        
        with open(js_path, 'r') as f:
            js_content = f.read()
        
        return f'<script>{js_content}</script>'
    
    pattern = r'<script\s+src="([^"]+)"[^>]*></script>'
    return re.sub(pattern, replace_script, html)
```

### 8.2 Minification

```python
# build/minify.py

import subprocess
import tempfile

def minify_html(html: str) -> str:
    """Минификация HTML через html-minifier"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
        f.write(html)
        input_path = f.name
    
    output_path = input_path + '.min'
    
    subprocess.run([
        'html-minifier',
        '--collapse-whitespace',
        '--remove-comments',
        '--minify-css', 'true',
        '--minify-js', 'true',
        '-o', output_path,
        input_path
    ], check=True)
    
    with open(output_path, 'r') as f:
        return f.read()


def minify_js_inline(html: str) -> str:
    """Минификация inline JS через terser"""
    import re
    
    def minify_script(match):
        js = match.group(1)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write(js)
            input_path = f.name
        
        result = subprocess.run(
            ['terser', input_path, '--compress', '--mangle'],
            capture_output=True,
            text=True
        )
        
        return f'<script>{result.stdout}</script>'
    
    pattern = r'<script>([^<]+)</script>'
    return re.sub(pattern, minify_script, html, flags=re.DOTALL)
```

### 8.3 Full Build

```python
# build/pipeline.py

from pathlib import Path
from .inline_assets import inline_images, inline_css, inline_js
from .minify import minify_html

def build_playable(
    template_dir: Path,
    spec: dict,
    output_path: Path,
    minify: bool = True
) -> dict:
    """
    Полный pipeline сборки playable
    
    Returns:
        {
            "success": bool,
            "size_kb": float,
            "errors": [],
            "warnings": []
        }
    """
    result = {"success": True, "errors": [], "warnings": []}
    
    # 1. Load template
    template_path = template_dir / "template.html"
    with open(template_path, 'r') as f:
        html = f.read()
    
    # 2. Render with Jinja2
    from jinja2 import Template
    template = Template(html)
    html = template.render(**spec)
    
    # 3. Inline CSS
    html = inline_css(html, template_dir)
    
    # 4. Inline JS (mechanics)
    html = inline_js(html, template_dir / "mechanics")
    
    # 5. Inline images
    html = inline_images(html, template_dir / "assets")
    
    # 6. Add MRAID wrapper
    with open(template_dir.parent / "common" / "mraid_wrapper.js", 'r') as f:
        mraid_js = f.read()
    
    html = html.replace('</head>', f'<script>{mraid_js}</script></head>')
    
    # 7. Minify
    if minify:
        try:
            html = minify_html(html)
        except Exception as e:
            result["warnings"].append(f"Minification failed: {e}")
    
    # 8. Validate size
    size_kb = len(html.encode('utf-8')) / 1024
    result["size_kb"] = size_kb
    
    if size_kb > 5000:
        result["errors"].append(f"Size {size_kb:.0f}KB exceeds 5MB limit")
        result["success"] = False
    
    # 9. Validate no external refs
    import re
    if re.search(r'(src|href)=["\']https?://', html):
        result["errors"].append("External references found")
        result["success"] = False
    
    # 10. Write output
    with open(output_path, 'w') as f:
        f.write(html)
    
    return result
```

---

## 9. Структура проекта

```
playable-agent/
├── app.py                      # Streamlit UI entry point
├── requirements.txt
├── .env.example
│
├── agent/
│   ├── __init__.py
│   ├── orchestrator.py         # Main agent loop
│   ├── tools.py                # Tool definitions
│   └── prompts.py              # System prompts
│
├── models/
│   ├── __init__.py
│   ├── brief.py                # DraftBrief model
│   ├── assets.py               # AssetMapping model
│   └── spec.py                 # PlayableSpec model
│
├── build/
│   ├── __init__.py
│   ├── inline_assets.py
│   ├── minify.py
│   └── pipeline.py
│
├── templates/
│   ├── common/
│   │   ├── mraid_wrapper.js
│   │   └── base_styles.css
│   │
│   └── ship_grid_merge_v1/     # Шаблон для Pirate Ships
│       ├── template.html
│       ├── config.json         # Default config for template
│       ├── mechanics/
│       │   ├── grid_placement.js
│       │   ├── merge.js
│       │   ├── battle.js
│       │   └── tutorial.js
│       └── assets/             # Placeholder assets for testing
│           └── .gitkeep
│
├── tests/
│   ├── test_tools.py
│   ├── test_build.py
│   └── fixtures/
│       ├── sample.pdf
│       └── sample_images/
│
└── docs/
    └── api.md
```

---

## 10. План реализации (36 часов)

### День 1 (0-12 часов)

| Час | Задача | Deliverable |
|-----|--------|-------------|
| 0-2 | Setup проекта, зависимости | `requirements.txt`, структура папок |
| 2-4 | Streamlit UI scaffold | Upload + Chat + Preview |
| 4-6 | Tool: `extract_brief_from_pdf` | Парсинг PDF → DraftBrief |
| 6-8 | Tool: `analyze_images` | GPT-4V анализ → AssetMapping |
| 8-10 | Логика уточняющих вопросов | `generate_questions()` |
| 10-12 | Шаблон `ship_grid_merge_v1` base | HTML skeleton + CSS |

### День 2 (12-24 часов)

| Час | Задача | Deliverable |
|-----|--------|-------------|
| 12-14 | Механика: GridPlacement | Drag & Drop на сетку |
| 14-16 | Механика: Merge | Объединение 2→1 |
| 16-18 | Механика: BattleLoop | HP bars + damage |
| 18-20 | Tool: `generate_playable_spec` | DraftBrief → PlayableSpec |
| 20-22 | Tool: `render_playable` | Jinja2 render |
| 22-24 | Build: inline assets | Base64 encoding |

### День 3 (24-36 часов)

| Час | Задача | Deliverable |
|-----|--------|-------------|
| 24-26 | MRAID wrapper integration | ready/viewable gate |
| 26-28 | Tool: `validate_playable` | Compliance checks |
| 28-30 | Build: minification | Size optimization |
| 30-32 | E2E integration | Full pipeline test |
| 32-34 | Bug fixes + polish | Stable version |
| 34-36 | Demo + README | Documentation |

---

## 11. Зависимости

### requirements.txt

```
# Core
streamlit>=1.30.0
fastapi>=0.109.0
uvicorn>=0.27.0
python-dotenv>=1.0.0

# AI
openai>=1.10.0
anthropic>=0.18.0

# PDF Processing
PyMuPDF>=1.23.0

# Image Processing
Pillow>=10.2.0

# Templating
Jinja2>=3.1.3

# Validation
pydantic>=2.5.0

# Build tools (optional, can use npm)
# html-minifier via npm
# terser via npm
```

### npm dependencies (optional)

```json
{
  "devDependencies": {
    "html-minifier": "^4.0.0",
    "terser": "^5.27.0"
  }
}
```

---

## 12. Acceptance Criteria

### 12.1 Must Have (MVP)

- [ ] Upload PDF + images через UI
- [ ] Агент задаёт уточняющие вопросы
- [ ] Генерация PlayableSpec из brief
- [ ] Render HTML из одного шаблона (ship_grid_merge)
- [ ] Работают механики: GridPlacement, Merge, Battle
- [ ] MRAID wrapper (ready/viewable gate)
- [ ] CTA через `mraid.open()`
- [ ] Все ассеты inline (base64)
- [ ] Размер < 5MB
- [ ] Нет внешних запросов
- [ ] Preview в iframe
- [ ] Download готового HTML

### 12.2 Nice to Have (если останется время)

- [ ] Несколько шаблонов
- [ ] Автоматическое сжатие изображений
- [ ] Валидация в разных сетях (AppLovin preview tool)
- [ ] История сессий
- [ ] Export в ZIP для разных сетей

### 12.3 Out of Scope (для MVP)

- Сложные 3D эффекты
- Звук/музыка
- Генерация ассетов (только использование загруженных)
- A/B тестирование
- Analytics интеграция

---

## 13. Тестирование

### 13.1 Manual Testing Checklist

```markdown
## Pre-flight Check

- [ ] Открыть index.html локально в браузере
- [ ] Проверить, что нет ошибок в console
- [ ] Проверить размер файла < 5MB
- [ ] Grep на "http://" и "https://" (должны быть только store URLs)

## Gameplay Flow

- [ ] Сцена 1: Drag repairer → ship grid
- [ ] Сцена 2: Drag shield → ship grid  
- [ ] Battle: HP bars update correctly
- [ ] Сцена 3: Drag cannons → ship grid
- [ ] Сцена 4: Merge 2 cannons → skeleton cannon
- [ ] Final battle: Enemy defeated
- [ ] Victory screen: Items display
- [ ] CTA button: Opens store URL

## MRAID Compliance

- [ ] Не запускается до ready event
- [ ] Не играет звук до interaction
- [ ] mraid.open() вызывается при CTA
- [ ] Работает в portrait
- [ ] Работает в landscape

## Network-specific Testing

### AppLovin
- Загрузить в AppLovin Preview Tool
- Проверить render в симуляторе

### Unity
- Загрузить в Unity Ad Testing app
- Проверить viewableChange handling
```

### 13.2 Automated Tests

```python
# tests/test_build.py

import pytest
from build.pipeline import build_playable
from pathlib import Path

def test_output_is_single_file():
    result = build_playable(...)
    # Проверяем, что output - один файл
    assert result["success"]
    
def test_no_external_references():
    html = open("output/index.html").read()
    assert "src=\"http" not in html
    assert "href=\"http" not in html.replace("mraid.open", "")

def test_size_under_5mb():
    html = open("output/index.html").read()
    size_kb = len(html.encode('utf-8')) / 1024
    assert size_kb < 5000

def test_mraid_wrapper_present():
    html = open("output/index.html").read()
    assert "mraid.getState" in html
    assert "viewableChange" in html
```

---

## 14. Риски и митигация

| Риск | Вероятность | Влияние | Митигация |
|------|-------------|---------|-----------|
| Изображения слишком большие → >5MB | Высокая | Критическая | Автоматическое сжатие, предупреждение при загрузке |
| GPT-4 не понимает PDF layout | Средняя | Высокое | Fallback на ручной ввод, few-shot примеры |
| MRAID не работает в сети | Средняя | Критическая | Тестирование в official preview tools |
| Механики не работают на touch | Средняя | Высокое | Touch handlers с самого начала |
| Не успеваем за 36 часов | Средняя | Критическая | Жёсткий scope, один шаблон, без полировки |

---

## 15. Контакты и ресурсы

### Документация
- MRAID 3.0: https://iabtechlab.com/standards/mraid/
- AppLovin Specs: https://support.applovin.com/
- Unity Specs: https://docs.unity.com/acquire/

### Инструменты тестирования
- AppLovin Preview: https://p.applov.in/playablePreview
- Unity Ad Testing App: iOS/Android
- MRAID Tester: https://nickyrabit.github.io/mraid-tester/

### Референсы
- Luna Playable Examples: https://github.com/LunaCommunity/Playable-Examples
- Playable SDK: https://github.com/smoudjs/playable-sdk
- Playable Scripts: https://github.com/smoudjs/playable-scripts

---

*Документ создан: 2025-01-31*  
*Версия: 1.0 MVP*
