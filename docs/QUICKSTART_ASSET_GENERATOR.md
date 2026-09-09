# Asset Generator - Quick Start Guide

## 🚀 Быстрый старт

### 1. Проверка API ключей

```bash
# Проверьте .env файл
cat .env

# Должны быть:
OPENAI_API_KEY=sk-proj-...
FAL_KEY=...
```

### 2. Запуск тестов

```bash
# Unit тесты (с моками)
PYTHONPATH=. python tests/test_asset_generator.py

# Реальный API тест
PYTHONPATH=. python scripts/test_asset_generation.py
```

### 3. Использование в коде

```python
from playable_agents.asset_generator import generate_assets
from models import DraftBrief
from playable_agents.scene_card import SceneCard

# Создайте brief
brief = DraftBrief(
    title="Car Wash Game",
    scenes=[],
    networks=["facebook"],
    languages=["en"],
    copy_texts={"title": "Clean the car!"}
)

# Создайте scene cards
scene_cards = [
    SceneCard(
        id="scene_1",
        title="Wash Car",
        mechanics=["drag_drop"],
        ui_elements={"progress": "0% Clean"},
        user_actions=["drag sponge over dirty_car"],
        technical={}
    )
]

# Генерируйте ассеты
manifest = generate_assets(
    brief=brief,
    scene_cards=scene_cards,
    reference_images=[]  # Опционально
)

# Результат
print(f"Generated {len(manifest['assets'])} assets")
print(f"Total size: {manifest['total_size_bytes']/1024:.1f}KB")

# Используйте ассеты
for asset in manifest['assets']:
    print(f"  {asset['name']}: {asset['role']}")
```

---

## 📋 Asset Manifest Structure

```python
{
    "assets": [
        {
            "name": "hero_character",
            "role": "character",  # character | tool | background | ui | decoration | overlay
            "z_index": 10,        # Render order (0=back, 25=front)
            "data": "data:image/png;base64,...",
            "size": {"width": 512, "height": 512},
            "critical": True      # Retry 3x if generation fails
        }
    ],
    "total_size_bytes": 220089,
    "metadata": {
        "generation_time": "2026-02-01T12:00:00",
        "optimized": True,      # Auto-optimization applied
        "brief_style": "cartoon flat colors mobile game style",
        "duration_seconds": 49.5
    }
}
```

---

## 🎨 Asset Roles

| Role | Description | Size | z_index | Format |
|------|-------------|------|---------|--------|
| `background` | Фоны, окружение | 960x540 | 0 | JPEG |
| `decoration` | Декорации | 128x128 | 5 | PNG |
| `character` | Персонажи, машины | 512x512 | 10 | PNG |
| `tool` | Инструменты, объекты | 256x256 | 15 | PNG |
| `overlay` | Наложения, эффекты | 512x512 | 20 | PNG |
| `ui` | UI элементы, кнопки | 256x256 | 25 | PNG |

---

## ⚙️ Configuration

### Настройка промпта

Редактируйте `Prompts/asset_planner.txt`:

```
Ты — asset planner для playable ads.

Вход:
- ТЗ (бриф): {brief}
- Scene cards: {scene_cards}
- Референсные изображения: {references}

Задача: составь полный список ассетов для генерации.

[... ваши инструкции ...]
```

### Настройка retry logic

В `playable_agents/asset_generator.py`:

```python
# Количество попыток для критических ассетов
RETRY_ATTEMPTS = 3

# Максимальный размер
MAX_SIZE_BYTES = 2 * 1024 * 1024  # 2MB
```

### Настройка роли

В `ROLE_TEMPLATES`:

```python
"character": {
    "suffix": "centered, single object, transparent background",
    "size": (512, 512),
    "z_index": 10,
    "aspect_ratio": "1:1"
}
```

---

## 🐛 Troubleshooting

### Problem: "OPENAI_API_KEY not set"

```bash
# Убедитесь что .env загружается
cat .env | grep OPENAI_API_KEY

# В скрипте добавьте:
import os
from pathlib import Path

env_path = Path(".env")
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            if line.strip() and "=" in line:
                key, value = line.strip().split("=", 1)
                os.environ[key] = value
```

### Problem: "Total size > 2MB"

Auto-optimization автоматически сработает. Если нужно больше контроля:

```python
# В _auto_optimize() измените quality
image.save(output, format="JPEG", quality=50)  # Уменьшите с 60
```

### Problem: "Generation failed for critical asset"

```python
# Увеличьте количество попыток
RETRY_ATTEMPTS = 5  # Вместо 3
```

### Problem: "Structured output validation failed"

OpenAI иногда возвращает невалидный JSON. Логи покажут ошибку:

```python
# Проверьте промпт в Prompts/asset_planner.txt
# Убедитесь что инструкции четкие
```

---

## 📊 Monitoring

### Логи

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('asset_generator')

# Логи покажут:
# - OpenAI API calls
# - FAL API calls
# - Retry attempts
# - Optimization steps
```

### Metrics

```python
manifest = generate_assets(...)

# Время генерации
duration = manifest['metadata']['duration_seconds']

# Размер
total_kb = manifest['total_size_bytes'] / 1024

# Оптимизация
optimized = manifest['metadata']['optimized']

print(f"Generated in {duration:.1f}s, size {total_kb:.1f}KB, optimized={optimized}")
```

---

## 🎯 Best Practices

### 1. Детальные описания в brief

Хорошо:
```
"Car Wash Game - помойте грязную красную машину желтой губкой в гараже"
```

Плохо:
```
"Car Game"
```

### 2. Упоминайте объекты в user_actions

```python
SceneCard(
    user_actions=["drag sponge over dirty_car"],  # Упоминает sponge и dirty_car
    ...
)
```

→ Эти ассеты будут помечены как `critical=True`

### 3. Используйте reference images (future)

```python
reference_images = [
    "/path/to/style_reference.png",
    "/path/to/character_example.png"
]

manifest = generate_assets(brief, scene_cards, reference_images)
```

---

## 📚 API Reference

### `generate_assets()`

```python
def generate_assets(
    brief: DraftBrief,
    scene_cards: List[SceneCard],
    reference_images: List[str]
) -> Dict[str, Any]:
    """
    Generate visual assets for playable ad.

    Returns:
        AssetManifest dict with assets, total_size_bytes, metadata

    Raises:
        AssetGenerationError: If critical asset fails after retries
    """
```

### Internal Functions

- `_plan_assets()` - OpenAI GPT-4o asset planning
- `_build_prompt()` - Prompt construction
- `_call_fal_imagen()` - FAL API wrapper
- `_generate_images()` - Image generation loop
- `_postprocess_and_optimize()` - Compression + base64
- `_auto_optimize()` - Size reduction

---

## ✅ Checklist

Before using in production:

- [ ] API keys set in .env
- [ ] Unit tests passing (9/9)
- [ ] Real API test successful
- [ ] Prompts customized
- [ ] Retry logic configured
- [ ] Logging enabled
- [ ] Error handling tested

---

**Ready to generate assets! 🎨**
