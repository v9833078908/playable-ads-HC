# Pipeline Architecture: Multi-Agent Playable Ad Generation

> Подробная документация input/output каждого агента, используемых промптов и передачи данных между агентами.

**Последнее обновление:** 2026-02-08
**Версия pipeline:** v2 (5-agent architecture)

---

## Содержание

1. [Общая схема](#1-общая-схема)
2. [Memory Store — общая память](#2-memory-store--общая-память)
3. [Agent 1: Scenario Agent](#3-agent-1-scenario-agent)
4. [Agent 2: Asset Generator Agent](#4-agent-2-asset-generator-agent)
5. [Agent 3: Generator Agent](#5-agent-3-generator-agent)
6. [Agent 4: Visual QA Agent](#6-agent-4-visual-qa-agent)
7. [Agent 5: Technical QA Agent](#7-agent-5-technical-qa-agent)
8. [Orchestrator — координатор](#8-orchestrator--координатор)
9. [Data Flow — полная схема передачи данных](#9-data-flow--полная-схема-передачи-данных)
10. [Реальный тест — пример работы](#10-реальный-тест--пример-работы)

---

## 1. Общая схема

```
Input: spec_text + reference_assets (PNG)
         │
         ▼
┌─────────────────────────┐
│   1. Scenario Agent     │  Gemini 3 Pro Vision
│   Анализ ТЗ → scene_spec│
└────────────┬────────────┘
             │ scene_spec, asset_list
             ▼
┌─────────────────────────┐
│ 2. Asset Generator Agent│  FAL Imagen + Haiku 4.5
│   Генерация ассетов     │
└────────────┬────────────┘
             │ asset_manifest (16 assets)
             ▼
┌─────────────────────────┐
│   3. Generator Agent    │  Claude Sonnet 4.5 (streaming)
│   HTML генерация        │
└────────────┬────────────┘
             │ html_versions[0]
             ▼
        ┌────┴────┐
        │ QA Loop │ (max 5 итераций)
        └────┬────┘
             │
     ┌───────┴───────┐
     ▼               ▼
┌──────────┐  ┌──────────────┐
│4. Visual │  │5. Technical  │
│   QA     │  │     QA       │
│(Gemini)  │  │  (Haiku 4.5) │
└────┬─────┘  └──────┬───────┘
     │               │
     └───────┬───────┘
             │ qa_history
             ▼
      Passed? ──YES──▶ Output: final HTML
        │
        NO
        │
        ▼
  Generator Agent
  fix_issues(feedback)
        │
        └──▶ Повтор QA Loop
```

---

## 2. Memory Store — общая память

**Файл:** `playable_agents/memory_store.py`

Все агенты общаются через единый `MemoryStore` — словарь с dot-notation доступом.

### Полная структура данных

```python
MemoryStore._data = {
    # === INPUT (загружается перед стартом) ===
    "spec_text": str,              # Текст ТЗ (TZ_SNB_Car.md)
    "style_references": dict,      # {filename: "data:image/png;base64,..."}
    "reference_assets": dict,      # {name: "data:image/png;base64,..."}

    # === SCENARIO AGENT OUTPUT ===
    "scene_spec": {
        "genre": "car-wash",
        "mechanics": ["drag-to-clean", "reveal-mask", "progress-bar", ...],
        "scenes": [
            {"name": "gameplay", "description": "..."},
            {"name": "victory", "description": "..."}
        ],
        "ui_texts": {
            "hint": "Потри машину!",
            "cta": "ИГРАТЬ"
        },
        "store_urls": {
            "android": "https://play.google.com/store/apps/...",
            "ios": "https://apps.apple.com/..."
        },
        "language": "ru",
        "requirements": [...]
    },
    "style_description": {
        "style": "cartoon",
        "shading": "flat",
        "colors": ["#hex1", "#hex2"],
        "line_style": "thick",
        "target_audience": "casual",
        "key_elements": [...]
    },
    "asset_list": [
        {
            "name": "car_dirty",
            "description": "Cartoon dirty car with mud splashes",
            "role": "main_object",   # main_object|tool|background|ui_element|effect
            "states": ["dirty"],
            "size": "512x512"
        },
        ...
    ],

    # === ASSET GENERATOR OUTPUT ===
    "asset_manifest": {
        "car_clean": {
            "data": "data:image/png;base64,...",
            "role": "main_object",
            "size": {"width": 512, "height": 512},
            "source": "reference"    # reference|generated
        },
        "background_road": {
            "data": "data:image/png;base64,...",
            "role": "background",
            "size": {"width": 960, "height": 540},
            "source": "generated"
        },
        ...  # 16 assets total
    },

    # === GENERATOR OUTPUT ===
    "html_versions": [
        {
            "version": 1,
            "html": "<!DOCTYPE html>...",
            "timestamp": "2026-02-08T15:55:00"
        }
    ],

    # === QA OUTPUT ===
    "qa_history": [
        {
            "iteration": 1,
            "visual_qa": {"passed": bool, "issues": [...]},
            "technical_qa": {"passed": bool, "issues": [...], "metrics": {...}},
            "timestamp": "2026-02-08T15:56:00"
        }
    ]
}
```

### API Memory Store

```python
store = MemoryStore()

store.set("key", value)                    # Записать
store.get("key")                           # Прочитать top-level
store.get("scene_spec.genre")              # Dot-notation для вложенных
store.get_all()                            # Всё содержимое

store.append_html_version(html) -> int     # Добавить HTML версию, вернуть номер
store.get_latest_html() -> str             # Получить последний HTML

store.append_qa_result(iter, visual, tech) # Добавить QA результат
store.reset()                              # Очистить всё
```

---

## 3. Agent 1: Scenario Agent

**Файл:** `playable_agents/scenario_agent.py`
**Промпт:** `playable_agents/prompts/scenario_agent.md`
**Модель:** Google Gemini 3 Pro (vision-capable)

### Назначение
Парсит техническое задание (ТЗ) и стилевые референсы. Создает структурированную спецификацию сцены и список ассетов.

### Input (что читает из Memory Store)

| Ключ | Тип | Описание |
|------|-----|----------|
| `spec_text` | str | Текст ТЗ (например, TZ_SNB_Car.md, 1434 chars) |
| `style_references` | dict | Стилевые референсы как base64 (опционально) |

### Output (что пишет в Memory Store)

| Ключ | Тип | Описание |
|------|-----|----------|
| `scene_spec` | dict | Жанр, механики, сцены, UI тексты, store URLs |
| `style_description` | dict | Стиль, цвета, шейдинг, аудитория |
| `asset_list` | list | Список необходимых ассетов (12-13 штук) |

### Tools (функции агента)

#### `analyze_spec(ctx)` — async
- Читает `spec_text` из memory
- Отправляет в Gemini для извлечения JSON-структуры
- Записывает `scene_spec` в memory

#### `analyze_references(ctx)` — async
- Читает `style_references` (base64 изображения)
- Gemini Vision анализирует стиль
- Записывает `style_description` в memory

#### `create_asset_list(ctx)` — async
- Читает `scene_spec` и `style_description`
- Gemini генерирует список ассетов на основе жанра/механик
- Записывает `asset_list` в memory

#### `confirm_understanding(ctx)` — sync
- Читает все данные, формирует читаемый summary

### System Prompt (scenario_agent.md)

```
You are a Scenario Analyst for playable ad creation.

Tasks:
1. Analyze Style References — visual style, color palette, shading
2. Parse Technical Specification — genre, mechanics, scenes, UI texts, store URLs
3. Create Asset List — name, description, role, states, size per asset
4. Build Scene Specification — structured JSON output
5. Confirm Understanding — summarize and ask for confirmation

Roles: main_object | tool | background | ui_element | effect
```

### Вызов из Orchestrator

```python
result = await Runner.run(
    scenario_agent,
    input="Analyze the specification and create asset list. "
          "Call analyze_spec, then create_asset_list, then confirm_understanding.",
    context={"memory_store": memory}
)
```

### Реальный Output (тест 2026-02-08)

```
Genre: car-wash
Mechanics: ['drag-to-clean', 'reveal-mask', 'progress-bar', 'animated-hint',
            'cta', 'physics-based-animation', 'animated-effect']
Scenes: 2 (gameplay, victory)
Asset list: 13 assets
Time: ~15 seconds
```

---

## 4. Agent 2: Asset Generator Agent

**Файл:** `playable_agents/asset_generator_agent.py`
**Модель:** FAL Gemini Image API (генерация) + Claude Haiku 4.5 (промпт-билдинг)

### Назначение
Маппит референсные изображения на ассет-лист и генерирует недостающие ассеты через FAL API.

### Input (что читает из Memory Store)

| Ключ | Тип | Описание |
|------|-----|----------|
| `reference_assets` | dict | Загруженные PNG как base64 (6 файлов) |
| `asset_list` | list | Список необходимых ассетов от Scenario Agent |
| `style_description` | dict | Описание стиля для prompt-building |

### Output (что пишет в Memory Store)

| Ключ | Тип | Описание |
|------|-----|----------|
| `asset_manifest` | dict | Полный манифест всех ассетов (reference + generated) |

### Tools (функции агента)

#### `use_reference_assets(ctx)` — async
- Читает `reference_assets` и `asset_list`
- Маппит загруженные изображения на элементы asset_list по имени
- Записывает в `asset_manifest` с `source: "reference"`

**Name mapping:**
```python
{
    "car_bright": ["car_bright", "car_clean_bright"],
    "car_clean": ["car_clean"],
    "car_dirt": ["car_dirt_overlay", "car_dirty"],
    "hand": ["hand_hint", "hand_cursor"],
    "karcher_one": ["karcher_one", "karcher_spray_gun"],
    "karcher_water": ["water_stream", "karcher_water"],
}
```

#### `generate_asset(asset_name)` — async
- Генерирует один ассет через FAL API
- Строит промпт через `_build_prompt()` (описание + стиль)
- Применяет role-specific config (размер, формат)
- Оптимизирует (resize, compress) через `_optimize_image()`

#### `generate_missing_assets(ctx)` — async
- Находит ассеты из `asset_list`, которых нет в `asset_manifest`
- Генерирует каждый через FAL API с retry logic (3 попытки)
- Обновляет `asset_manifest`

#### `get_asset_status(ctx)` — sync
- Статус: какие ассеты готовы, какие в ожидании

### Role-Specific Configuration

```python
ROLE_CONFIG = {
    "main_object": {"size": "512x512", "format": "PNG", "bg": "transparent"},
    "tool":        {"size": "256x256", "format": "PNG", "bg": "transparent"},
    "background":  {"size": "960x540", "format": "JPEG", "quality": 85},
    "ui_element":  {"size": "256x256", "format": "PNG", "bg": "transparent"},
    "effect":      {"size": "512x512", "format": "PNG", "bg": "transparent"},
    "decoration":  {"size": "128x128", "format": "PNG", "bg": "transparent"},
}
```

### Вызов из Orchestrator

```python
result = await Runner.run(
    asset_generator_agent,
    input="Map reference assets and generate missing ones. "
          "Call use_reference_assets() then generate_missing_assets().",
    context={"memory_store": memory}
)
```

### Реальный Output (тест 2026-02-08)

```
Reference assets mapped: 6
Generated assets: 10-11
Total in manifest: 16-17
Time: ~60 seconds
```

---

## 5. Agent 3: Generator Agent

**Файл:** `playable_agents/generator_agent.py`
**Промпт:** `playable_agents/prompts/generator_car_wash.md`
**Модель:** Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`) — streaming

### Назначение
Генерирует полный HTML playable ad на основе scene_spec и asset_manifest. Использует streaming API для больших ответов.

### Input (что читает из Memory Store)

| Ключ | Тип | Описание |
|------|-----|----------|
| `scene_spec` | dict | Спецификация сцены (жанр, механики, тексты) |
| `asset_manifest` | dict | Манифест ассетов (role, size — БЕЗ base64 в промпте) |

### Output (что пишет в Memory Store)

| Ключ | Тип | Описание |
|------|-----|----------|
| `html_versions` | list | Массив HTML версий (append при каждой генерации) |

### Tools (функции агента)

#### `generate_html(ctx)` — async, streaming
1. Читает `scene_spec` и `asset_manifest` из memory
2. Строит контекст: metadata ассетов (role, size) **без base64**
3. Загружает жанровый промпт (`generator_car_wash.md`)
4. Вызывает Claude Sonnet 4.5 через **streaming API**:
   ```python
   with client.messages.stream(
       model="claude-sonnet-4-5-20250929",
       max_tokens=64000,
       messages=[{"role": "user", "content": user_prompt}],
       system=system_prompt
   ) as stream:
       for text in stream.text_stream:
           html_chunks.append(text)
   ```
5. Проверяет `stop_reason == "max_tokens"` → auto-continuation
6. Очищает markdown-обертку (```html...```)
7. **Инжектит base64 ассеты** через `_inject_assets()`
8. Сохраняет в `html_versions`

#### `fix_issues(issues)` — async, streaming
- Читает текущий HTML и issues от QA
- Claude исправляет найденные проблемы
- Re-inject assets после фикса
- Сохраняет новую версию

#### `get_html_status(ctx)` — sync
- Количество версий, размер, наличие canvas/touch/mraid/raf

#### `export_html(ctx)` — sync
- Копирует HTML в context["html"] для совместимости

### User Prompt (generate_html)

```
Generate a complete HTML playable ad based on this specification:

## Scene Specification
{json scene_spec}

## Available Assets (use placeholders, actual base64 will be injected later)
{json asset_manifest metadata}

CRITICAL: For assets, use simple placeholders like:
const images = {
  asset_name: 'PLACEHOLDER_asset_name',
  another_asset: 'PLACEHOLDER_another_asset',
};

Do NOT include actual base64 data URIs in the HTML.

Requirements:
1. Single HTML file with all CSS/JS inlined
2. Use PLACEHOLDER_<asset_name> for each asset
3. Touch events with mouse fallback
4. MRAID integration for store redirect
5. Canvas-based rendering
6. Game loop with requestAnimationFrame
7. Progress tracking and victory sequence
8. Animated CTA button with shimmer effect
```

### System Prompt (generator_car_wash.md)

Содержит эталонные реализации для жанра car-wash:

1. **Dirt Mask System** — offscreen canvas + `globalCompositeOperation: 'destination-out'`
2. **Water Particle System** — 4 частицы на touch, life/velocity/gravity
3. **Hose Physics** — Verlet integration, 20 сегментов, damping
4. **Z-Index Layering** — Background(0) → Car(10) → Dirt(15) → Particles(20) → Hose(25) → UI(30) → Victory(40) → CTA(50)
5. **Progress Tracking** — calculateCleanProgress() через imageData
6. **Victory Sequence** — sparkle particles, fade-in, CTA
7. **CTA Animation** — pulse + shimmer (scale + linearGradient)
8. **Touch/Mouse Events** — с passive:false и preventDefault()
9. **MRAID Integration** — mraid.open() с fallback
10. **Game Loop** — requestAnimationFrame + update/render split

### Asset Injection (_inject_assets)

После генерации HTML с placeholder'ами, функция `_inject_assets()` заменяет их на реальные base64:

```python
# Приоритет паттернов:
1. PLACEHOLDER_<name>           # Основной (новый подход)
2. name: 'data:image/...base64' # JS object property с коротким base64
3. name: "data:image..."        # То же с двойными кавычками
4. {{asset:name}}, {asset:name} # Jinja-style
5. ASSET_NAME, "assets/name"    # Fallback
```

### Вызов из Orchestrator

```python
result = await Runner.run(
    generator_agent,
    input="Generate the HTML playable ad using the real assets. Call generate_html().",
    context={"memory_store": memory}
)
```

### Реальный Output (тест 2026-02-08)

```
HTML size: 20.3 KB (622 строки)
Has canvas: Yes
Has touch events: Yes (touchstart, touchmove)
Has MRAID: Yes
Has game loop (RAF): Yes
Streaming: enabled
max_tokens: 64000
Stop reason: end_turn (не обрезан)
Time: ~30 seconds
```

---

## 6. Agent 4: Visual QA Agent

**Файл:** `playable_agents/visual_qa_agent.py`
**Промпт:** `playable_agents/prompts/visual_qa.md`
**Модель:** Google Gemini 3 Flash (Vision)

### Назначение
Визуальная валидация сгенерированного HTML через анализ скриншотов.

### Input

| Ключ | Тип | Описание |
|------|-----|----------|
| `scene_spec` | dict | Спецификация для сравнения |
| `asset_list` | list | Список ожидаемых ассетов |
| `html_versions` | list | HTML для анализа |
| screenshot_base64 | str | Скриншот (передается в функцию) |

### Output

| Ключ | Тип | Описание |
|------|-----|----------|
| `qa_history` | list | Append результатов visual QA |

### Tools

#### `validate_visual(screenshot_base64)` — async
- Принимает скриншот (base64) или берет из context
- Gemini Vision анализирует по чеклисту
- Возвращает JSON:
  ```json
  {
    "passed": false,
    "issues": [
      {
        "severity": "critical|major|minor|warning",
        "category": "asset_presence|positioning|z_index|effects|ui|victory|style",
        "description": "...",
        "suggestion": "..."
      }
    ],
    "notes": "..."
  }
  ```

#### `check_asset_presence(ctx)` — sync
- Быстрая проверка: ищет первые 50 chars base64 каждого ассета в HTML

### Чеклист Visual QA

1. **Asset Presence** — все ассеты видимы, нет broken icons
2. **Asset Positioning** — правильное размещение, не обрезаны
3. **Visual Hierarchy** — правильный z-index layering
4. **Effects & Animation** — частицы, вода, эффекты очистки
5. **UI Elements** — progress bar, hint text, шрифты
6. **Victory Screen** — CTA кнопка, celebration effects
7. **Overall Quality** — consistent style, mobile-ready

> **Примечание:** В текущем тесте Visual QA пропускается (нет screenshots). Для полной работы нужен Playwright.

---

## 7. Agent 5: Technical QA Agent

**Файл:** `playable_agents/technical_qa_agent.py`
**Промпт:** `playable_agents/prompts/technical_qa.md`
**Модель:** Claude Haiku 4.5

### Назначение
Техническая валидация HTML: размер, mobile compatibility, touch events, MRAID, game loop.

### Input

| Ключ | Тип | Описание |
|------|-----|----------|
| `html_versions` | list | HTML для валидации |
| `scene_spec` | dict | Store URLs для проверки |

### Output

| Ключ | Тип | Описание |
|------|-----|----------|
| `qa_history` | list | Append результатов technical QA |

### Tools

#### `run_all_checks(ctx)` — sync, main entry point
Вызывает все проверки и собирает единый отчет:

```json
{
  "passed": true,
  "issues": [...],
  "metrics": {
    "file_size_kb": 20.3,
    "has_touch_events": true,
    "has_mraid": true,
    "uses_raf": true
  }
}
```

**Critical issues = FAIL**, только major/minor/warning = PASS.

#### `check_size(ctx)` — sync
- HTML < 5MB → PASS
- Severity: CRITICAL

#### `check_touch_events(ctx)` — sync
- touchstart, touchmove, touchend
- passive: false
- preventDefault()
- Severity: MAJOR

#### `check_mraid(ctx)` — sync
- mraid reference
- mraid.open()
- Platform detection (userAgent)
- Store URLs (play.google.com, apps.apple.com)
- Severity: CRITICAL (no mraid.open)

#### `check_viewport(ctx)` — sync
- viewport meta
- user-scalable=no
- touch-action: none
- overflow: hidden
- Severity: MAJOR

#### `check_game_loop(ctx)` — sync
- requestAnimationFrame (не setInterval)
- canvas + getContext
- Severity: MAJOR

### Чеклист Technical QA (12 категорий)

| # | Категория | Что проверяет |
|---|-----------|---------------|
| 1 | File Size | < 5MB |
| 2 | HTML Structure | Valid HTML5, head/body, canvas с ID |
| 3 | Viewport & Mobile | viewport meta, user-scalable=no, touch-action:none |
| 4 | Touch Events | touchstart/move/end, passive:false, preventDefault |
| 5 | Mouse Events | mousedown/move/up/leave fallback |
| 6 | Game Loop | requestAnimationFrame (не setTimeout) |
| 7 | MRAID | window.mraid check, mraid.open() |
| 8 | Store URLs | Valid Google Play + App Store URLs |
| 9 | Canvas | Proper dimensions, 2D context, no WebGL |
| 10 | Asset Loading | base64 data URIs, onload handlers |
| 11 | Memory | No infinite arrays, proper scoping |
| 12 | JS Syntax | No errors, all vars declared |

### Вызов из Orchestrator

```python
result = await Runner.run(
    technical_qa_agent,
    input="Run all technical checks. Call run_all_checks().",
    context={"memory_store": memory}
)
```

### Реальный Output (тест 2026-02-08)

```json
{
  "passed": true,
  "issues": [
    {
      "severity": "major",
      "category": "mraid",
      "description": "No platform detection - may open wrong store"
    }
  ],
  "metrics": {
    "file_size_kb": 20.3,
    "has_touch_events": true,
    "has_mraid": true,
    "uses_raf": true
  }
}
```

---

## 8. Orchestrator — координатор

**Файл:** `playable_agents/orchestrator.py`
**Класс:** `PlayableOrchestrator`

### Конфигурация

```python
MAX_QA_ITERATIONS = 5      # Макс. итераций QA loop
STUCK_ISSUE_THRESHOLD = 3  # Если issue появляется 3+ раз → escalation
```

### Метод `run_pipeline()` — основной flow

```python
async def run_pipeline(spec_text, style_references=None) -> dict:
```

**Шаги:**

1. **Reset** memory_store
2. **Set** `spec_text` и `style_references` в memory
3. **Phase 1**: Scenario Agent
   - Input: `"Analyze the specification and create asset list."`
   - Проверка: `scene_spec` создан?
4. **Phase 2**: Asset Generator Agent
   - Input: `"Generate all assets from the asset list."`
5. **Phase 3**: Generator + QA Loop (max 5 итераций)
   - Итерация 1: `"Generate the HTML playable ad."`
   - Итерация 2+: `"Fix these issues: [feedback from QA]"`
   - После каждой генерации → Technical QA
   - Если `passed` → break
   - Если issue повторяется 3+ раз → escalate

**Return:**
```python
{
    "success": True,
    "html": "<!DOCTYPE html>...",
    "iterations": 1,
    "escalated_issues": [],
    "qa_history": [...]
}
```

### Issue Tracking & Escalation

```python
issue_tracker = {}  # {description: count}

# На каждой итерации QA:
for issue in current_issues:
    issue_tracker[desc] = issue_tracker.get(desc, 0) + 1
    if issue_tracker[desc] >= 3:
        self.escalated_issues.append(issue)
        # Эта issue требует ручного вмешательства
```

---

## 9. Data Flow — полная схема передачи данных

### Фаза 1: Анализ ТЗ

```
[User Input]
  spec_text: "TZ_SNB_Car.md" (1434 chars, русский)
  reference_assets: {
    car_bright: PNG 38KB,
    car_clean: PNG 70KB,
    car_dirt: PNG 89KB,
    hand: PNG 46KB,
    karcher_one: PNG 21KB,
    karcher_water: PNG 349KB
  }
      │
      ▼ memory.set("spec_text", ...) + memory.set("reference_assets", ...)
      │
[Scenario Agent] ──Gemini 3 Pro──▶
      │
      ├─▶ memory.set("scene_spec", {
      │       genre: "car-wash",
      │       mechanics: [7 items],
      │       scenes: [2 items],
      │       ui_texts: {hint, cta},
      │       store_urls: {android, ios}
      │   })
      │
      ├─▶ memory.set("style_description", {
      │       style: "cartoon", colors: [...], ...
      │   })
      │
      └─▶ memory.set("asset_list", [13 assets])
```

### Фаза 2: Генерация ассетов

```
[Asset Generator Agent] ──FAL API──▶
      │
      │ Reads: reference_assets, asset_list, style_description
      │
      ├─ use_reference_assets()
      │   Маппит 6 reference → asset_manifest (source: "reference")
      │
      └─ generate_missing_assets()
          Генерирует 10-11 через FAL (source: "generated")
      │
      └─▶ memory.set("asset_manifest", {16 assets with base64 data})
```

### Фаза 3: HTML генерация

```
[Generator Agent] ──Claude Sonnet 4.5 (streaming)──▶
      │
      │ Reads: scene_spec (полностью), asset_manifest (только metadata)
      │
      │ Prompt содержит:
      │   - scene_spec JSON
      │   - asset names + roles + sizes (БЕЗ base64!)
      │   - Инструкцию использовать PLACEHOLDER_<name>
      │
      │ Claude генерирует:
      │   HTML с PLACEHOLDER_car_clean, PLACEHOLDER_background, ...
      │
      │ Post-processing:
      │   _inject_assets() заменяет PLACEHOLDER → base64 из asset_manifest
      │
      └─▶ memory.append_html_version(html)
          html_versions[0] = {version: 1, html: "<!DOCTYPE...>"}
```

### Фаза 4: QA валидация

```
[Technical QA Agent]
      │
      │ Reads: html_versions[-1], scene_spec
      │
      │ Выполняет:
      │   check_size() → OK (20KB < 5MB)
      │   check_touch_events() → OK (touchstart/move/end found)
      │   check_mraid() → ISSUE (no platform detection)
      │   check_viewport() → OK
      │   check_game_loop() → OK (RAF found)
      │
      └─▶ memory qa_history.append({
              technical_qa: {passed: true, issues: [1 major]}
          })
```

### Фаза 5: Итерация (если QA не прошел)

```
[Orchestrator]
      │
      │ qa_history[-1].technical_qa.passed == false?
      │   YES → собирает issues в текст
      │
      ▼
[Generator Agent] ──fix_issues(issues)──▶
      │
      │ Claude получает текущий HTML + список issues
      │ Генерирует исправленную версию
      │
      └─▶ memory.append_html_version(fixed_html)
          html_versions[1] = {version: 2, html: "..."}
      │
      └─▶ Повтор Technical QA → qa_history[1]
```

---

## 10. Реальный тест — пример работы

**Тест:** `test_real_pipeline.py`
**Дата:** 2026-02-08
**Входные данные:** TZ_SNB_Car.md + 6 PNG

### Timeline

| Время | Фаза | Агент | Результат |
|-------|-------|-------|-----------|
| 0:00 | Load | - | 6 reference assets (612KB total) |
| 0:05 | Phase 1 | Scenario Agent | scene_spec + 13 assets + style |
| 0:20 | Phase 2 | Asset Generator | 6 ref + 10 gen = 16 assets |
| 1:20 | Phase 3 | Generator Agent | HTML 20.3KB, 622 lines |
| 1:50 | Phase 4 | Technical QA | PASSED (1 major issue) |
| 2:00 | Done | - | Pipeline complete |

### Итоговый HTML

```
Size: 20.3 KB
Lines: 622
Features:
  ✅ Canvas rendering (1024x768)
  ✅ requestAnimationFrame game loop
  ✅ Touch events (touchstart, touchmove)
  ✅ MRAID integration
  ✅ Dirt mask erasure
  ✅ Water particle system
  ✅ Progress tracking
  ✅ Victory sequence
  ✅ CTA button with animation
  ⚠️ No platform detection (1 QA issue)
```

### QA Result

```
Technical QA: PASSED
Issues: 1
  [major] No platform detection - may open wrong store

Metrics:
  file_size_kb: 20.3
  has_touch_events: true
  has_mraid: true
  uses_raf: true
```

---

## 11. Проблема: HTML пустой при открытии в браузере

**Статус:** ✅ ИСПРАВЛЕНО
**Дата обнаружения:** 2026-02-08
**Дата исправления:** 2026-02-08

### Симптом

HTML файл 20KB, 622 строки, структура полная (`</html>` есть), QA passed — но при открытии в браузере **canvas пустой**, ничего не рисуется.

### Корневая причина

Claude генерирует **dynamic asset loading** через JavaScript template literal вместо статических placeholder'ов.

**Что генерирует Claude (строка 105 output_real_pipeline.html):**
```javascript
const assetNames = [
    'car_bright', 'car_clean', 'car_dirt_overlay', 'hand_hint',
    'karcher_one', 'water_stream', 'background_road'
];

// Dynamic loading — имя ассета подставляется в runtime
assetNames.forEach(name => {
    const img = new Image();
    img.src = `PLACEHOLDER_${name}`;  // ← JavaScript template literal!
    images[name] = img;
});
```

**Что ожидает `_inject_assets()`:**
```javascript
// Статические строки, которые можно найти text-search:
images['car_clean'].src = 'PLACEHOLDER_car_clean';
```

### Почему ничего не заменяется

`_inject_assets()` делает `str.replace('PLACEHOLDER_car_clean', base64_data)` по всему HTML.

Но в HTML нет строки `PLACEHOLDER_car_clean` — есть только JavaScript-выражение `` `PLACEHOLDER_${name}` ``, которое вычисляется в runtime. Python text replace ничего не находит → base64 не инжектируется → все `img.src` указывают на несуществующие URL `PLACEHOLDER_*` → `img.onerror` срабатывает → canvas пустой.

### Цепочка проблемы

```
Prompt говорит: "Use PLACEHOLDER_<asset_name>"
    → Claude интерпретирует как dynamic pattern
    → Генерирует template literal `PLACEHOLDER_${name}`
    → _inject_assets() ищет literal string "PLACEHOLDER_car_clean"
    → Не находит → 0 замен
    → HTML без base64 → пустой canvas
    → QA проверяет только текст (grep), не рендер → PASSED
    → Ложный успех
```

### Варианты решения

**Option A: Исправить `_inject_assets()` — при обнаружении dynamic pattern переписать JS**

Обнаружить паттерн `PLACEHOLDER_${name}` в HTML и заменить весь asset-loading блок на статический словарь:

```python
# Если нашли dynamic pattern, заменяем на static dict
if 'PLACEHOLDER_${' in html:
    asset_dict_js = "const assetData = {\n"
    for name, data in asset_manifest.items():
        data_uri = data.get("data", "")
        asset_dict_js += f"    '{name}': '{data_uri}',\n"
    asset_dict_js += "};"
    # Заменить dynamic loading на static
```

**Option B: Изменить промпт — явно запретить dynamic loading**

```
CRITICAL: Do NOT use template literals or dynamic string construction for asset URLs.
Each asset MUST be a separate variable with literal PLACEHOLDER string:

  const assetData = {
      car_clean: 'PLACEHOLDER_car_clean',
      background_road: 'PLACEHOLDER_background_road',
  };
```

**Option C: Комбинированный (рекомендуется)** ✅ **РЕАЛИЗОВАНО**

Изменить и промпт (для предотвращения), и `_inject_assets()` (для обработки случаев, когда Claude всё равно использует dynamic pattern).

### Реализованное исправление

**1. Улучшен промпт (`generator_agent.py:104-128`):**
```python
CRITICAL: For assets, use a STATIC object with literal PLACEHOLDER strings.
DO NOT use template literals, dynamic string construction, or loops.

✅ CORRECT - Static object with literal strings:
const assetData = {
  car_clean: 'PLACEHOLDER_car_clean',
  background_road: 'PLACEHOLDER_background_road',
};

❌ WRONG - Dynamic template literals will NOT work:
assetNames.forEach(name => {
  img.src = `PLACEHOLDER_${name}`;  // ← WRONG!
});
```

**2. Добавлена обработка dynamic pattern в `_inject_assets()` (`generator_agent.py:353-415`):**

Функция теперь:
1. Обнаруживает паттерн `` `PLACEHOLDER_${...}` `` в HTML
2. Строит статический JavaScript объект `assetData` со всеми base64
3. Заменяет весь блок `assetNames + forEach` на статический словарь
4. Логирует: `"Replaced dynamic pattern with static dict for N assets"`

**Результат:** Даже если Claude проигнорирует промпт и сгенерирует dynamic pattern, `_inject_assets()` автоматически переписывает код на статический словарь с base64.

### Тест после исправления (2026-02-08)

```
Pipeline run: SUCCESS ✅
HTML size: 1.7 MB (1761.3 KB)
PLACEHOLDER count: 0 (все заменены)
base64 data URIs: 16 (все ассеты инжектированы)
assetData: const assetData = { car_bright: 'data:...', ... }

QA result: PASSED (1 major issue - platform detection)
HTML validity: ✅ Full (<!DOCTYPE...></html>)
Canvas rendering: ✅ Works (все изображения загружаются)
```

**Проблема решена полностью.** HTML теперь корректно рендерится в браузере со всеми ассетами.

---

## API Keys Required

| Key | Используется | Агент |
|-----|-------------|-------|
| `GEMINI_API_KEY` | Gemini 3 Pro/Flash | Scenario Agent, Visual QA |
| `ANTHROPIC_API_KEY` | Claude Sonnet 4.5, Haiku 4.5 | Generator Agent, Technical QA |
| `FAL_KEY` | FAL Gemini Image API | Asset Generator |

---

## Файловая структура

```
playable-ads-hackathon/
├── playable_agents/
│   ├── __init__.py                  # Экспорт всех агентов
│   ├── orchestrator.py              # Координатор pipeline
│   ├── memory_store.py              # Shared memory store
│   ├── scenario_agent.py            # Agent 1: Анализ ТЗ
│   ├── asset_generator_agent.py     # Agent 2: Генерация ассетов
│   ├── generator_agent.py           # Agent 3: HTML генерация
│   ├── visual_qa_agent.py           # Agent 4: Visual QA
│   ├── technical_qa_agent.py        # Agent 5: Technical QA
│   └── prompts/
│       ├── scenario_agent.md        # System prompt для Scenario
│       ├── generator_car_wash.md    # Genre prompt для Car Wash
│       ├── visual_qa.md             # System prompt для Visual QA
│       └── technical_qa.md          # System prompt для Technical QA
├── test_real_pipeline.py            # E2E тест с реальными данными
├── output_real_pipeline.html        # Результат последнего теста
└── docs/
    ├── INDEX.md                     # Индекс документации
    ├── PIPELINE_ARCHITECTURE.md     # ← ЭТОТ ДОКУМЕНТ
    ├── KNOWN_ISSUES.md              # Известные проблемы
    └── TODO_FIXES.md                # План исправлений
```
