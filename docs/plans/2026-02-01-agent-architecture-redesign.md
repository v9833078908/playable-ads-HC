# Agent Architecture Redesign: Playable Ads Generator

**Дата:** 2026-02-01
**Статус:** Approved
**Цель:** Заменить текущий template-based подход на автономную multi-agent систему для генерации высококачественных playable ads

---

## 1. Проблема

Текущий pipeline генерирует HTML низкого качества:
- `html_generator.py` слишком примитивный — простой инкремент счётчика вместо реальной механики
- Нет эффектов воды, частиц, физики шланга
- Ассеты не правильно сопоставляются с кодом
- Scenario Builder задаёт абстрактные вопросы, не понимая полную картину

**Эталон качества:** `docs/misc/car-wash-playable-unity-ads-RC1.html`

---

## 2. Решение: Multi-Agent Architecture

### 2.1 Общая схема

```
┌─────────────────────────────────────────────────────────────────┐
│                        Streamlit UI                              │
│              Upload: ТЗ (PDF/MD) + Референсы стиля (PNG/JPG)    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PlayableOrchestrator                          │
│                    (координирует 5 агентов)                      │
└─────────────────────────────────────────────────────────────────┘
                              │
    ┌─────────────────────────┼─────────────────────────┐
    ▼                         ▼                         ▼
┌────────────┐        ┌──────────────┐          ┌─────────────┐
│  SCENARIO  │───────▶│    ASSET     │─────────▶│  GENERATOR  │
│   AGENT    │        │  GENERATOR   │          │    AGENT    │
│            │        │    AGENT     │          │             │
│ Gemini 3   │        │ Haiku 4.5 +  │          │Claude Sonnet│
│    Pro     │        │   FAL API    │          │    4.5      │
└────────────┘        └──────────────┘          └─────────────┘
      │                      │                        │
      │   SceneSpec +        │   AssetManifest        │   HTML
      │   AssetList +        │   (generated           │
      │   StyleDesc          │    images)             ▼
      │                      │               ┌───────────────────┐
      │                      │               │     QA LOOP       │
      │                      │               │  ┌─────────────┐  │
      │                      │               │  │  Visual QA  │  │
      │                      │               │  │Gemini Flash │  │
      │                      │               │  └─────────────┘  │
      │                      │               │  ┌─────────────┐  │
      │                      │               │  │Technical QA │  │
      │                      │               │  │ Haiku 4.5   │  │
      │                      │               │  └─────────────┘  │
      │                      │               │                   │
      │                      │               │  Max 5 iterations │
      │                      │               │  Escalate @ 3     │
      │                      │               └───────────────────┘
      │                      │                        │
      └──────────────────────┴────────────────────────┘
                              │
                              ▼
                 ┌─────────────────────────┐
                 │    Shared Memory Store   │
                 └─────────────────────────┘
```

---

## 3. Агенты

### 3.1 Scenario Agent

**Модель:** Gemini 3 Pro Preview (Vision)
**Конфиг:** `SCENARIO_AGENT_MODEL` в `.env`

**Задачи:**
1. Vision-анализ каждого референса → описание стиля
2. Парсинг ТЗ → понимание механики, сцен, UI
3. Сопоставление референсов с требованиями ТЗ
4. Составление списка нужных ассетов (AssetList)
5. Подтверждение понимания: "Я понял так: [описание]. Верно?"
6. Уточняющие вопросы по критичным пробелам

**Выход:** `SceneSpec` + `AssetList` + `StyleDescription`

---

### 3.2 Asset Generator Agent

**Модель:** Claude Haiku 4.5 (промпты) + FAL API Gemini Image (генерация)
**Конфиг:** `ASSET_GENERATOR_MODEL`, `FAL_API_KEY` в `.env`

**Задачи:**
1. Получить `AssetList` и `StyleDescription` от Scenario Agent
2. Для каждого ассета составить промпт для генерации
3. Вызвать FAL API (Gemini Image)
4. Vision-валидация результата (соответствует ли описанию?)
5. Retry с улучшенным промптом (max 3 попытки)
6. Оптимизация размера (PNG для прозрачности, JPEG для фонов)

**Выход:** `AssetManifest` {name → base64}

---

### 3.3 Generator Agent

**Модель:** Claude Sonnet 4.5
**Конфиг:** `GENERATOR_AGENT_MODEL` в `.env`

**Задачи:**
1. Получить `SceneSpec` + `AssetManifest`
2. Применить best practices для жанра (см. раздел 4)
3. Сгенерировать полный HTML с инлайн CSS/JS
4. При получении issues от QA — исправить код

**Выход:** HTML файл

**Best Practices для Car Wash / Cleaning:**
```
├── Механика стирания:
│   └── Offscreen canvas для маски грязи
│   └── globalCompositeOperation = 'destination-out'
│   └── Радиус стирания 30-50px
│
├── Эффекты воды:
│   └── Particle system: 4-8 частиц за кадр
│   └── Физика: gravity 0.2, fade 0.015, размер 6-12px
│   └── Цвет: rgba(100, 200, 255, alpha)
│
├── Физика шланга:
│   └── Verlet integration, 15-20 сегментов
│   └── Damping 0.85-0.92
│
├── Визуальные слои (z-index):
│   └── 0: Background
│   └── 10: Основной объект
│   └── 15: Overlay грязи
│   └── 20: Эффекты
│   └── 25: Инструмент
│   └── 30: UI
│
└── Victory sequence:
    └── Sparkle particles
    └── Fade transitions
    └── CTA с pulse + shimmer
```

---

### 3.4 Visual QA Agent

**Модель:** Gemini 3 Flash Preview (Vision)
**Конфиг:** `VISUAL_QA_MODEL` в `.env`

**Чеклист:**
- [ ] Все ассеты из ТЗ присутствуют в HTML?
- [ ] Ассеты правильно расположены (не обрезаны, не за экраном)?
- [ ] Масштаб ассетов соответствует композиции?
- [ ] Слои в правильном порядке?
- [ ] Эффекты воды/частиц реализованы?
- [ ] UI тексты соответствуют ТЗ?
- [ ] Прогресс-бар визуально корректен?
- [ ] Victory screen имеет нужные элементы?
- [ ] CTA кнопка заметна и анимирована?

**Выход:**
```json
{
  "passed": false,
  "issues": [
    {
      "severity": "critical",
      "category": "visual",
      "description": "...",
      "suggestion": "..."
    }
  ]
}
```

---

### 3.5 Technical QA Agent

**Модель:** Claude Haiku 4.5
**Конфиг:** `TECHNICAL_QA_MODEL` в `.env`

**Чеклист:**
- [ ] Размер HTML < 5MB?
- [ ] Нет синтаксических ошибок JS?
- [ ] Touch events реализованы (touchstart, touchmove, touchend)?
- [ ] Mouse events как fallback?
- [ ] MRAID: window.mraid проверка + mraid.open()?
- [ ] Store URLs корректные (Google Play и App Store)?
- [ ] Определение платформы (Android/iOS)?
- [ ] Canvas размеры адекватные?
- [ ] requestAnimationFrame для game loop?
- [ ] Нет утечек памяти?
- [ ] Viewport meta tag для мобильных?
- [ ] touch-action: none?

**Выход:** Аналогичный формат JSON

---

## 4. QA Loop с лимитами

```
iteration = 0
stuck_issues = {}

WHILE iteration < 5:
    │
    ├── Visual QA + Technical QA → all_issues
    │
    ├── IF all passed:
    │   └── EXIT SUCCESS
    │
    ├── Track stuck issues (3+ attempts)
    │
    ├── IF any issue stuck 3+ times:
    │   └── ЭСКАЛАЦИЯ К ПОЛЬЗОВАТЕЛЮ:
    │       "Не могу решить проблему: [описание]
    │        Причина: [анализ]
    │        Варианты:
    │        1. Упростить требование
    │        2. Использовать другой подход
    │        3. Продолжить без этой фичи
    │        4. Остановить и доработать вручную"
    │
    │       User выбирает → Generator применяет
    │
    ├── ELSE: Generator исправляет issues
    └── iteration += 1

IF iteration == 5:
    └── Финальный результат + отчёт о нерешённых issues
```

---

## 5. Shared Memory Store

```python
memory = {
    # INPUT
    "spec_text": "...",
    "style_references": {"filename": "<base64>", ...},

    # SCENARIO AGENT OUTPUT
    "style_description": "мультяшный, яркие цвета, flat shading",
    "asset_list": [
        {"name": "car_clean", "description": "...", "role": "main_object"},
        ...
    ],
    "scene_spec": {
        "genre": "car-wash",
        "mechanics": ["drag-to-clean", "reveal-mask"],
        "scenes": [...],
        "ui_texts": {...},
        "store_urls": {...}
    },

    # ASSET GENERATOR OUTPUT
    "asset_manifest": {"car_clean": "<base64>", ...},

    # GENERATOR OUTPUT
    "html_versions": [
        {"version": 1, "html": "...", "timestamp": "..."},
    ],

    # QA FEEDBACK
    "qa_history": [
        {
            "iteration": 1,
            "visual_qa": {"passed": False, "issues": [...]},
            "technical_qa": {"passed": True, "issues": []},
        },
    ]
}
```

---

## 6. Файловая структура

```
playable_agents/
│
├── orchestrator.py              # ИЗМЕНИТЬ: новый pipeline
│
├── scenario_agent.py            # СОЗДАТЬ
├── asset_generator_agent.py     # СОЗДАТЬ
├── generator_agent.py           # СОЗДАТЬ
├── visual_qa_agent.py           # СОЗДАТЬ
├── technical_qa_agent.py        # СОЗДАТЬ
├── memory_store.py              # СОЗДАТЬ
│
├── prompts/                     # СОЗДАТЬ
│   ├── scenario_agent.md
│   ├── generator_car_wash.md
│   ├── visual_qa.md
│   └── technical_qa.md
│
└── УДАЛИТЬ:
    ├── scenario_builder.py
    ├── generator.py
    ├── html_generator.py
    └── brief_extractor.py
```

---

## 7. Обработка ошибок

| Ситуация | Действие |
|----------|----------|
| Vision fail на референсе | Попросить описать вручную |
| ТЗ неясное | Больше уточняющих вопросов |
| API timeout | Retry 3 раза с exponential backoff |
| HTML > 5MB | Technical QA issue → сжатие |
| Превышен лимит итераций | Отдать лучшую версию + отчёт |
| Пользователь отменил | Сохранить состояние для возобновления |

---

## 8. Поддерживаемые жанры

**Приоритет 1 (сейчас):**
- Car Wash / Cleaning

**Приоритет 2 (будущее):**
- Merge
- Match-3
- Dress Up
- Building/Repair
- Tap to Collect
- Runner/Dodge
- Puzzle

---

## 9. Следующие шаги

1. [ ] Создать `memory_store.py`
2. [ ] Создать `scenario_agent.py` с Gemini 3 Pro
3. [ ] Создать `asset_generator_agent.py` с FAL API
4. [ ] Создать `generator_agent.py` с промптом для Car Wash
5. [ ] Создать `visual_qa_agent.py`
6. [ ] Создать `technical_qa_agent.py`
7. [ ] Обновить `orchestrator.py`
8. [ ] Удалить старые файлы
9. [ ] Тестирование на Car Wash ТЗ
