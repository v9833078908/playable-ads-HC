# Integrate Asset Generator Agent into Pipeline

**Дата:** 2026-02-02

**Goal:** Добавить Asset Generator Agent в пайплайн между Scenario Agent и Generator Agent. Агент должен:
1. Использовать уже загруженные reference ассеты (car_clean, car_dirt, etc.)
2. Генерировать только недостающие ассеты через FAL API
3. Создавать полный `asset_manifest` для Generator Agent

---

## Текущая проблема

```
Scenario Agent → ❌ [ПРОПУЩЕН] ❌ → Generator Agent (неполный asset_manifest)
```

**Результат тестирования:**
- Scenario Agent создает `asset_list` с 14 ассетами
- Но в `asset_manifest` попадают только 6 загруженных reference ассетов
- Generator Agent получает неполные данные → неполный HTML

---

## Целевой пайплайн

```
Scenario Agent → Asset Generator Agent → Generator Agent → QA Agents
    ↓                    ↓                      ↓
scene_spec          asset_manifest          HTML output
asset_list          (reference + generated)
```

---

## Reference Assets Mapping

| Reference файл | asset_list имя |
|----------------|----------------|
| car_clean.png | car_clean |
| car_dirt.png | car_dirt_overlay |
| car_bright.png | car_bright |
| hand.png | hand_hint |
| karcher_one.png | karcher_one |
| karcher@1x.png | water_stream |

**Итого:** 6 reference ассетов замапятся автоматически

---

## Missing Assets to Generate

| Asset | Role | Size | Примечание |
|-------|------|------|------------|
| background_gameplay | background | 960x540 | Минималистичная дорога |
| karcher_hose | tool | 256x256 | Гибкий шланг для физики |
| progress_bar_background | ui_element | 256x64 | Контейнер прогресс бара |
| progress_bar_fill | ui_element | 256x64 | Заполнение прогресс бара |
| progress_text_style | ui_element | 256x64 | Стиль текста "0% clean" |
| drag_wash_hint_text | ui_element | 256x128 | Анимированный текст "Drag & Wash" |
| congratulations_text | ui_element | 512x256 | Праздничный текст |
| next_level_button | ui_element | 256x128 | CTA кнопка |

**Итого:** 8 ассетов нужно сгенерировать через FAL API

---

## Task 1: Add Reference Asset Matching Function

**File:** `playable_agents/asset_generator_agent.py`

```python
@function_tool
async def use_reference_assets(ctx: RunContextWrapper[Any]) -> str:
    """
    Map loaded reference assets to asset_list items.

    Checks reference_assets in memory and maps them to corresponding
    items in asset_list. Already loaded assets skip generation.
    """
    memory = ctx.context.get("memory_store")

    reference_assets = memory.get("reference_assets") or {}  # {name: base64_data}
    asset_list = memory.get("asset_list") or []

    # Mapping rules: reference_filename → asset_list_name
    name_mapping = {
        "car_clean": ["car_clean"],
        "car_dirt": ["car_dirt_overlay"],
        "car_bright": ["car_bright"],
        "hand": ["hand_hint"],
        "karcher_one": ["karcher_one"],
        "karcher_water": ["water_stream"],  # karcher@1x.png
    }

    manifest = memory.get("asset_manifest") or {}
    matched = []

    for ref_name, ref_data in reference_assets.items():
        target_names = name_mapping.get(ref_name, [ref_name])
        for target_name in target_names:
            manifest[target_name] = {
                "data": ref_data,
                "role": _get_role_for_asset(target_name, asset_list),
                "size": _get_image_size(ref_data),
                "source": "reference"
            }
            matched.append(target_name)

    memory.set("asset_manifest", manifest)
    return f"Mapped {len(matched)} reference assets: {', '.join(matched)}"
```

---

## Task 2: Add Generate Missing Assets Function

**File:** `playable_agents/asset_generator_agent.py`

```python
@function_tool
async def generate_missing_assets(ctx: RunContextWrapper[Any]) -> str:
    """
    Generate only assets that are not yet in asset_manifest.

    Uses FAL API to generate assets that weren't provided as references.
    """
    memory = ctx.context.get("memory_store")

    asset_list = memory.get("asset_list") or []
    manifest = memory.get("asset_manifest") or {}
    style_desc = memory.get("style_description") or {}

    # Find missing assets
    missing = [a for a in asset_list if a["name"] not in manifest]

    if not missing:
        return "All assets already present. No generation needed."

    logger.info(f"Generating {len(missing)} missing assets...")

    generated = []
    failed = []

    for asset in missing:
        asset_name = asset.get("name")
        role = asset.get("role", "main_object")
        config = ROLE_CONFIG.get(role, ROLE_CONFIG["main_object"])

        prompt = _build_prompt(asset, style_desc)
        logger.info(f"Generating {asset_name}: {prompt[:80]}...")

        try:
            fal_client = _get_fal_client()
            image_bytes = fal_client.generate_image_bytes(
                prompt=prompt,
                aspect_ratio=config["aspect_ratio"],
                format=config["format"]
            )

            # Convert to base64
            mime_type = f"image/{config['format']}"
            b64_data = base64.b64encode(image_bytes).decode('utf-8')
            data_uri = f"data:{mime_type};base64,{b64_data}"

            # Get dimensions
            img = Image.open(io.BytesIO(image_bytes))

            manifest[asset_name] = {
                "data": data_uri,
                "role": role,
                "size": {"width": img.width, "height": img.height},
                "source": "generated"
            }
            generated.append(asset_name)

        except Exception as e:
            logger.error(f"Failed to generate {asset_name}: {e}")
            failed.append(asset_name)

    memory.set("asset_manifest", manifest)

    result = f"Generated {len(generated)} assets: {', '.join(generated)}"
    if failed:
        result += f"\nFailed: {', '.join(failed)}"
    return result
```

---

## Task 3: Update test_real_pipeline.py

**File:** `test_real_pipeline.py`

### Изменение 1: Сохранять reference_assets

```python
# Load assets as base64 AND store as reference_assets
reference_assets = {}
asset_manifest = {}

for name, filename in asset_files.items():
    file_path = assets_dir / filename
    if file_path.exists():
        img_bytes = file_path.read_bytes()
        b64_data = base64.b64encode(img_bytes).decode()
        data_uri = f"data:image/png;base64,{b64_data}"

        # Store in both places
        reference_assets[name] = data_uri
        asset_manifest[name] = {
            "data": data_uri,
            "role": "main_object" if "car" in name else "tool",
            "size": {"width": 512, "height": 512}
        }
        print(f"✅ Loaded asset: {name}")

memory.set("reference_assets", reference_assets)
memory.set("asset_manifest", asset_manifest)
```

### Изменение 2: Добавить шаг Asset Generator

```python
# Phase 1: Scenario Agent
print("\n[1/4] Running Scenario Agent...")
result = await Runner.run(
    scenario_agent,
    input="Analyze the specification. Call analyze_spec() and create_asset_list().",
    context=context
)

# Phase 2: Asset Generator Agent ← NEW!
print("\n[2/4] Running Asset Generator Agent...")
from playable_agents.asset_generator_agent import asset_generator_agent

result = await Runner.run(
    asset_generator_agent,
    input="Map reference assets and generate missing ones. Call use_reference_assets() then generate_missing_assets().",
    context=context
)
print(f"📋 Asset Generator:\n{result.final_output}")

# Phase 3: Generator Agent
print("\n[3/4] Running Generator Agent...")
result = await Runner.run(
    generator_agent,
    input="Generate the HTML playable ad. Call generate_html().",
    context=context
)

# Phase 4: Technical QA
print("\n[4/4] Running Technical QA...")
result = await Runner.run(
    technical_qa_agent,
    input="Run all technical checks. Call run_all_checks().",
    context=context
)
```

---

## Task 4: Update Agent Instructions

**File:** `playable_agents/asset_generator_agent.py`

```python
asset_generator_agent = Agent(
    name="AssetGeneratorAgent",
    handoff_description="Generates visual assets using FAL API based on asset list from Scenario Agent",
    instructions="""You are an Asset Generator for playable ads.

Your job is to ensure all required assets are available for the Generator Agent.

Workflow:
1. Call use_reference_assets() to map loaded reference images to asset_list
2. Call get_asset_status() to see what's still missing
3. Call generate_missing_assets() to generate only missing assets via FAL API
4. Optionally validate critical assets with validate_asset()

IMPORTANT:
- Always use reference assets when available! They are higher quality than generated ones.
- Only generate what's missing - don't regenerate existing assets.
- Report final status: how many reference vs generated assets.

Role configurations for generation:
- main_object: 512x512 PNG, centered, transparent background
- tool: 256x256 PNG, simple silhouette
- background: 960x540 JPEG, scenic
- ui_element: 256x256 PNG, clean
- effect: 512x512 PNG, overlay
""",
    tools=[use_reference_assets, generate_missing_assets, generate_asset, generate_all_assets, get_asset_status, validate_asset],
)
```

---

## Task 5: Helper Functions

**File:** `playable_agents/asset_generator_agent.py`

```python
def _get_role_for_asset(name: str, asset_list: list) -> str:
    """Get role for asset from asset_list."""
    for a in asset_list:
        if a.get("name") == name:
            return a.get("role", "main_object")
    return "main_object"


def _get_image_size(data_uri: str) -> dict:
    """Extract image dimensions from base64 data URI."""
    from PIL import Image
    import io
    import base64

    if data_uri.startswith("data:"):
        b64_data = data_uri.split(",", 1)[1]
    else:
        b64_data = data_uri

    img_bytes = base64.b64decode(b64_data)
    img = Image.open(io.BytesIO(img_bytes))
    return {"width": img.width, "height": img.height}
```

---

## Verification

После реализации запустить:

```bash
# Test full pipeline
python test_real_pipeline.py
```

**Expected output:**
```
✅ All API keys found
================================================================================

🚀 Testing Full Pipeline with Real Data
--------------------------------------------------------------------------------
✅ Loaded TZ: 1434 chars
✅ Loaded asset: car_bright (38109 bytes)
✅ Loaded asset: car_clean (70417 bytes)
✅ Loaded asset: car_dirt (88581 bytes)
✅ Loaded asset: hand (45774 bytes)
✅ Loaded asset: karcher_one (20888 bytes)
✅ Loaded asset: karcher_water (349107 bytes)

[1/4] Running Scenario Agent...
📋 Scenario Agent:
✅ Scene spec created:
   Genre: car-wash
   Mechanics: 8
   Scenes: 2
✅ Asset List created: 14 assets

[2/4] Running Asset Generator Agent...
📋 Asset Generator:
✅ Mapped 6 reference assets: car_clean, car_dirt_overlay, car_bright, hand_hint, karcher_one, water_stream
✅ Generated 8 missing assets: background_gameplay, karcher_hose, progress_bar_background, progress_bar_fill, drag_wash_hint_text, congratulations_text, next_level_button

[3/4] Running Generator Agent...
📋 Generator Agent:
✅ HTML generated: ~150KB (with all 14 assets embedded)
   Saved to: output_real_pipeline.html

[4/4] Running Technical QA...
📋 Technical QA:
✅ All checks passed

================================================================================
✅ Full Pipeline Completed Successfully!
================================================================================
```

---

## Summary

| Шаг | Файл | Изменение |
|-----|------|-----------|
| 1 | asset_generator_agent.py | Добавить `use_reference_assets()` |
| 2 | asset_generator_agent.py | Добавить `generate_missing_assets()` |
| 3 | test_real_pipeline.py | Добавить шаг Asset Generator |
| 4 | asset_generator_agent.py | Обновить instructions агента |
| 5 | asset_generator_agent.py | Добавить helper функции |

**Результат:**
```
Reference ассеты (6) + Сгенерированные (8) = Полный asset_manifest (14)
```
