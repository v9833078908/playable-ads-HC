# Orchestrator V2 — Detailed Design

## Контекст

**Проблема:** Pipeline генерирует функциональный, но визуально бедный HTML. Нет облаков, CSS-анимаций, полированных UI, хореографированных переходов. Система должна работать для ЛЮБОГО ТЗ и жанра — без эталонных шаблонов.

**Корневая причина:** Оркестратор V1 — фиксированный pipeline без интеллекта. Не видит свой output (Visual QA отключён). Generator получает code snippets и упрощает. fix_issues() обрезает HTML до 15000 символов — теряет весь JS код. Feedback loop передаёт только структурные ошибки.

**Решение по принципам OpenClaw:** Оркестратор становится LLM-агентом с tools. Система ВИДИТ свой output через Playwright screenshots + Gemini Vision. Адаптивная итерация с score tracking. Память между запусками для обучения.

## Принятые архитектурные решения

| Решение | Выбор |
|---|---|
| Управление HTML | HTML-in-file (не передаём в контекст LLM) |
| Визуальная оценка | Мульти-стейт скриншоты (динамическое кол-во из scene_spec) |
| Механизм feedback | Code-level инструкции с номерами строк |
| Механизм правок | replace_html_section (хирургическая замена строк) |
| Критерий остановки | Score-based с delta tracking + rollback при регрессии |
| Память | Generation memory (SQLite + markdown, учится на прошлых запусках) |
| Обработка ошибок | Classified retry (разные стратегии по типу ошибки) |
| Первая генерация | Memory-primed (подтягивает паттерны из прошлых успешных запусков) |

---

## Секция 1: Общая архитектура

Оркестратор — LLM-агент (Claude Sonnet 4.5) с 12 tools. Он НЕ выполняет фиксированный pipeline, а сам решает порядок действий, анализируя результаты каждого шага.

**Поток данных:**
```
User Input (TZ + assets)
  → Orchestrator Agent
    ├─ analyze_spec()          → scene_spec в MemoryStore
    ├─ generate_assets()       → asset_manifest в MemoryStore
    ├─ search_memory(genre)    → best practices из прошлых запусков
    ├─ generate_html(primed)   → HTML файл на диске
    │
    ├─ LOOP: Self-evaluation
    │   ├─ take_screenshots()  → N скриншотов (по scene_spec.scenes)
    │   ├─ evaluate_visual()   → scores 0-10 по категориям
    │   ├─ run_technical_qa()  → structural checks
    │   ├─ read_html_section() → анализ проблемного кода
    │   ├─ replace_section()   → хирургическая правка
    │   └─ (repeat until score >= 7 or plateau)
    │
    ├─ save_to_memory()        → сохранить что сработало
    └─ return final HTML
```

**Ключевое отличие от V1:** оркестратор ВИДИТ результат (скриншоты), ПОНИМАЕТ код (read_html_section), и ТОЧЕЧНО правит (replace_section). Не переписывает HTML целиком.

**Version history:** каждая версия HTML сохраняется. При регрессии score — автоматический откат к лучшей версии.

---

## Секция 2: Tools оркестратора — полный список

Оркестратор получает 12 tools, разделённых на 4 группы:

**Группа 1 — Pipeline tools (вызов sub-agents):**
- `analyze_spec(spec_text, references)` → запускает Scenario Agent, возвращает scene_spec
- `generate_assets()` → запускает Asset Generator, возвращает asset_manifest
- `generate_html(instructions, memory_hints)` → запускает Generator Agent, сохраняет HTML в файл

**Группа 2 — Visual feedback tools:**
- `take_screenshots()` → Playwright делает N скриншотов по состояниям из scene_spec. Для каждого состояния симулирует нужные touch events. Возвращает список `{state_name, base64_png}`
- `evaluate_visual(screenshots[])` → отправляет скриншоты в Gemini Vision с quality rubric. Возвращает `{scores: {atmosphere: 8, ui: 5, physics: 7, ...}, issues: [...], overall: 6.5}`
- `run_technical_qa()` → код-анализ HTML (size, MRAID, touch, game loop)

**Группа 3 — HTML surgery tools:**
- `read_html_section(start_line, end_line)` → читает фрагмент HTML файла
- `replace_html_section(start_line, end_line, new_code)` → заменяет строки, валидирует синтаксис
- `validate_syntax()` → проверяет HTML/JS на ошибки, автоматически фиксит мелочи (незакрытые теги, пропущенные `;`)

**Группа 4 — Memory & utility tools:**
- `search_memory(query)` → semantic search по прошлым успешным генерациям
- `save_to_memory(genre, scores, successful_patterns)` → сохраняет что сработало
- `ask_user(question)` → эскалация если информации в ТЗ недостаточно

---

## Секция 3: Мульти-стейт скриншоты — механика

Playwright должен не просто открыть HTML — он должен **проиграть сценарий**, делая скриншот на каждом ключевом состоянии.

**Как определяются состояния:**
Оркестратор берёт `scene_spec.scenes` и строит список states автоматически. Для car-wash:
```
scenes: [
  {name: "gameplay", mechanic: "drag-to-clean"},
  {name: "victory", mechanic: "cta"}
]
→ states: [
  {name: "initial",     action: null,              wait: 1000ms},
  {name: "gameplay_0",  action: null,              wait: 500ms},
  {name: "gameplay_50", action: touch_swipe(50%),  wait: 1000ms},
  {name: "victory",     action: touch_swipe(100%), wait: 2000ms},
  {name: "cta",         action: null,              wait: 500ms}
]
```

**Симуляция взаимодействия:**
Для каждого state с action Playwright выполняет touch events на canvas:
- `touch_swipe(percent)` — серия touchstart→touchmove→touchend по canvas, покрывая N% площади
- `tap(selector)` — нажатие на элемент (CTA кнопка)
- `wait(ms)` — ожидание анимации

**Универсальность для других жанров:**
Действия привязаны к `mechanic` из scene_spec, не к жанру. Маппинг:
- `drag-to-clean` / `scratch` / `reveal-mask` → `touch_swipe`
- `tap-target` / `whack-a-mole` → `tap` по координатам
- `drag-and-drop` → `touch_drag(from, to)`
- `cta` → `tap(".cta-button")`

Оркестратор сам не знает как симулировать — tool `take_screenshots()` маппит mechanics → actions внутри себя.

---

## Секция 4: Visual QA scoring — как оценивать качество

Visual QA получает N скриншотов + quality rubric и возвращает структурированную оценку. Ключевое — оценка должна быть **числовой и actionable**.

**Категории оценки (0-10 каждая):**
- **Atmosphere** — глубина сцены: градиент неба, облака/частицы, тени, параллакс
- **UI Polish** — progress bar (HTML/CSS, не canvas), hint text, шрифты, glossy эффекты
- **Physics** — реалистичность интерактивных элементов: шланг/инструмент, частицы воды, гравитация
- **Animations** — CSS @keyframes, плавные transitions, victory choreography с задержками
- **Completeness** — все ассеты видны, нет placeholder'ов, все состояния работают

**Формат ответа Visual QA:**
```json
{
  "scores": {"atmosphere": 4, "ui": 6, "physics": 3, "animations": 2, "completeness": 8},
  "overall": 4.6,
  "per_state": {
    "initial": {"issues": ["Сплошной цвет фона, нет облаков"]},
    "gameplay_50": {"issues": ["Нет частиц воды при касании", "Шланг статичный"]},
    "victory": {"issues": ["Мгновенный переход, нет анимации CTA"]}
  },
  "priority_improvements": [
    {"category": "atmosphere", "what": "Нет облаков и градиента", "impact": "high"},
    {"category": "physics", "what": "Шланг без Verlet physics", "impact": "high"},
    {"category": "animations", "what": "Нет CSS keyframes", "impact": "medium"}
  ]
}
```

**Как оркестратор использует это:**
1. Сортирует `priority_improvements` по impact
2. Берёт top-1 проблему
3. Через `read_html_section()` находит соответствующий код
4. Формулирует точечную инструкцию для `replace_html_section()`
5. После правки — новые скриншоты, новый score, сравнивает delta

**Одна проблема за итерацию** — не пытается исправить всё сразу, чтобы отслеживать что именно улучшило score.

---

## Секция 5: Classified retry — обработка ошибок

Каждая ошибка классифицируется и получает свою стратегию восстановления. Оркестратор не падает — он адаптируется.

**Классификация ошибок:**

| Тип ошибки | Детекция | Стратегия | Max retries |
|---|---|---|---|
| **JS syntax error** | `validate_syntax()` после replace_section | Автофикс через отдельный LLM-вызов "fix this syntax error: ..." | 2 |
| **Replace broke logic** | Score упал после правки | Rollback к предыдущей версии HTML + попробовать другой подход к той же проблеме | 1 |
| **Playwright crash** | Timeout / browser error | Restart browser, retry screenshot | 2 |
| **Playwright timeout** | Page не загружается (JS infinite loop) | Rollback HTML, пометить "infinite loop introduced" | 1 |
| **LLM rate limit** | 429 / "rate limit" в ответе | Exponential backoff: 5s → 15s → 45s | 3 |
| **LLM context overflow** | "context too large" | Не должно случаться (HTML-in-file), но если да — compact history | 1 |
| **Gemini Vision невнятный ответ** | Scores отсутствуют или все 0 | Retry с упрощённым prompt, fallback на technical QA only | 2 |
| **Asset generation failed** | FAL API error | Retry 2 раза, потом placeholder + warning в финальном отчёте | 2 |

**Version history для rollback:**
```python
html_versions = [
  {"version": 1, "path": "output_v1.html", "scores": {"overall": 4.6}},
  {"version": 2, "path": "output_v2.html", "scores": {"overall": 5.8}},
  {"version": 3, "path": "output_v3.html", "scores": {"overall": 5.1}},  # regression!
  # → rollback to v2, try different approach
]
```

**Принцип: никогда не терять прогресс.** Каждая версия на диске, откат мгновенный. Оркестратор всегда знает какая версия лучшая.

---

## Секция 6: Generation memory — обучение между запусками

После каждого успешного запуска (overall score >= 7) оркестратор сохраняет опыт. При следующем запуске — подтягивает лучшие практики.

**Что сохраняется (файл `memory/{genre}_{timestamp}.md`):**
```markdown
# Car-Wash Generation — 2026-02-09

## Result: score 8.2, iterations: 3

## Successful Patterns
- drawBackground(): gradient sky (#87CEEB → #E0F0FF) +
  parallax clouds 3 layers (0.2/0.5/1.0 speed) → atmosphere: 9
- Hose: 20 segments Verlet, damping 0.92/0.80 → physics: 8
- Progress bar: HTML div + CSS gradient + ::before glossy → ui: 9
- Victory: setTimeout chain 500→1000→1500ms +
  cubic-bezier bounce → animations: 8

## Failed Approaches (не повторять)
- Canvas-drawn progress bar → ui: 4 (выглядит flat)
- 10 hose segments → physics: 3 (слишком жёсткий)
- Мгновенный victory transition → animations: 2

## Improvement Log
- iteration 1 → 4.6: baseline, no clouds, canvas progress bar
- iteration 2 → 6.8: added clouds, HTML progress bar
- iteration 3 → 8.2: added Verlet hose, victory choreography
```

**Как memory используется при новом запуске:**
1. Оркестратор вызывает `search_memory("car-wash playable ad best practices")`
2. Получает top-3 релевантных фрагмента из прошлых запусков
3. Вставляет в промпт генератора: *"Проверенные паттерны из прошлых генераций: [patterns]. Избегай: [failed approaches]"*
4. Первая генерация сразу включает облака, Verlet physics, HTML progress bar

**Для нового жанра (нет памяти):** генератор использует только quality rubric как baseline. После первого успешного запуска — появляется память и для этого жанра.

**Хранение:** markdown файлы в папке `memory/`, поиск через embedding-based semantic search (как в OpenClaw). SQLite + vector index. Первая версия — простой full-text search.

---

## Секция 7: Orchestrator system prompt — как агент принимает решения

Промпт строится динамически из 3 частей.

**Часть 1 — Роль и workflow (статичная, `prompts/orchestrator.md`):**
```
Ты автономный оркестратор playable ads. У тебя есть tools.
Ты ВИДИШЬ результат через скриншоты. Ты ЧИТАЕШЬ код через
read_html_section. Ты ТОЧЕЧНО правишь через replace_html_section.

Workflow:
1. analyze_spec → понять ТЗ
2. generate_assets → создать ассеты
3. search_memory → подтянуть опыт
4. generate_html → первая версия (с memory hints)
5. LOOP: take_screenshots → evaluate_visual →
   read проблемную секцию → replace_html_section → repeat
6. save_to_memory → сохранить опыт

Правила:
- Одна проблема за итерацию (top priority по impact)
- После каждой правки — обязательно take_screenshots
- Следи за delta score: если < 0.5 — меняй подход
- Если score упал — rollback через version history
- Max 7 итераций, стоп при overall >= 7
```

**Часть 2 — Quality rubric (статичная, `prompts/quality_rubric.md`):**
Критерии оценки по категориям — что значит score 3, 5, 7, 9 для каждой категории. Не код, а описание качества.

**Часть 3 — Memory hints (динамическая, inject at runtime):**
```
## Опыт прошлых генераций (genre: car-wash):
Сработало: [patterns из memory_search]
Не работало: [failed approaches]
```

Промпт собирается в runtime: `part1 + part2 + part3`. Для первого запуска жанра part3 пустая.

**Ключевой принцип из OpenClaw:** оркестратор — не скрипт. Он LLM, который ДУМАЕТ. Если стандартный подход не работает (score не растёт) — он сам решает попробовать другую стратегию. Prompt даёт ему framework, но не жёсткий алгоритм.

---

## Секция 8: Роль оркестратора — стратег, не фиксер

Оркестратор всегда держит в контексте **baseline** (score первой итерации) и **best** (лучший достигнутый score). На каждой итерации он принимает одно из 4 стратегических решений:

**Decision tree оркестратора:**
```
После evaluate_visual():

  current_score vs best_score:

  1. PATCH — score растёт, delta >= 0.5
     → read_html_section → replace_section
     → точечная правка, продолжаем

  2. RETHINK — score не растёт 2 итерации подряд (plateau)
     → сменить стратегию: если правили physics,
       переключиться на atmosphere
     → или попробовать другой подход к той же проблеме

  3. REGENERATE — score упал ниже baseline ИЛИ
     plateau после 3 итераций
     → откат к лучшей версии
     → пересобрать данные если нужно (re-run analyze_spec
       с уточнениями, re-run generate_assets)
     → вызвать generate_html заново с накопленным опытом:
       "Предыдущая генерация провалилась по: [reasons].
        Обязательно включи: [что работало из best version]"

  4. CLARIFY — недостаточно информации для улучшения
     → ask_user("В ТЗ не указано X, как должно выглядеть Y?")
     → после ответа: REGENERATE с новой информацией
```

**Оркестратор сравнивает КАЖДУЮ версию с первой:**
```python
history = [
  {v: 1, overall: 4.6, best_categories: {completeness: 8}},
  {v: 2, overall: 5.8, best_categories: {atmosphere: 7}},
  {v: 3, overall: 5.1, decision: "ROLLBACK to v2"},
  {v: 4, overall: 6.5, decision: "PATCH"},
  {v: 5, overall: 6.6, decision: "RETHINK - plateau"},
  {v: 6, overall: 6.4, decision: "REGENERATE - 3 iterations no progress"},
  # → полная перегенерация с накопленным опытом
  {v: 7, overall: 7.8, decision: "DONE - score >= 7"},
]
```

**REGENERATE — не провал, а инструмент.** Оркестратор явно передаёт генератору что работало в лучшей версии и что нет. Это не "начни с нуля", а "начни заново, вооружившись опытом".

**Пересборка данных:** если оркестратор понимает что проблема не в коде, а в scene_spec (например, не хватает ассетов для эффектов) — он может re-run `analyze_spec` с дополнительными требованиями или `generate_assets` для недостающих спрайтов.

### Две тактики — PATCH vs REGENERATE

Оркестратор использует **оба инструмента** — это его ключевая сила. Он выбирает тактику по ситуации:

```
Тактика PATCH (replace_html_section):
  Когда: score растёт, проблема локальная
  Что: читает конкретную секцию, заменяет 20-50 строк
  Пример: "drawBackground() без облаков" → заменить
           строки 180-210 на версию с параллаксом
  Плюс: быстро, дёшево, не ломает работающий код

Тактика REGENERATE (generate_html):
  Когда: plateau 3 итерации, или score ниже baseline
  Что: полная перегенерация через Generator Agent
  Пример: патчи сделали код нечитаемым, конфликты между
           секциями, фундаментальная проблема архитектуры HTML
  Плюс: чистый код, можно кардинально сменить подход
```

**Полный набор tools оркестратора для работы с HTML — 3 штуки:**

| Tool | Что делает | Когда |
|---|---|---|
| `generate_html()` | Полная генерация через Generator Agent | Первый раз + REGENERATE |
| `read_html_section()` | Читает фрагмент HTML файла | Перед каждым PATCH |
| `replace_html_section()` | Заменяет строки в HTML файле | PATCH |

**Типичный сценарий за один запуск:**
```
generate_html()          → v1, score 4.6
  PATCH: replace clouds  → v2, score 5.8
  PATCH: replace hose    → v3, score 6.2
  PATCH: replace victory → v4, score 6.3
  PATCH: replace progbar → v5, score 6.4
  plateau 3 итерации...
  REGENERATE             → v6, score 7.5 (чистый код
                            с облаками + hose + victory
                            сразу, потому что всё это
                            передано в промпт генератора)
  PATCH: polish CTA      → v7, score 8.0
  DONE
```

Оркестратор **начинает с PATCH** (дешевле, быстрее). Если PATCH перестаёт работать — **эскалирует до REGENERATE**. После REGENERATE может снова вернуться к PATCH для финального polish.

---

## Секция 9: Файловая структура и зависимости

Что создаём, что переписываем, что не трогаем.

**Новые файлы:**
```
playable_agents/
├── screenshot_tool.py              # Playwright multi-state screenshots
├── memory_manager.py               # SQLite + vector search для generation memory
├── error_classifier.py             # Классификация ошибок + стратегии retry
├── html_file_manager.py            # HTML-in-file: read/replace/validate/version history
├── prompts/
│   ├── orchestrator.md             # System prompt оркестратора (роль + workflow + rules)
│   └── quality_rubric.md           # Критерии качества по категориям (score 1-10 примеры)
└── memory/                         # Папка для generation memory файлов
```

**Переписываем:**
```
playable_agents/
├── orchestrator.py                 # Полный rewrite: LLM-agent с 12 tools
├── prompts/
│   ├── generator_car_wash.md       # Quality requirements вместо code snippets
│   └── visual_qa.md               # Добавить scoring 0-10 + per-state evaluation
└── __init__.py                     # Добавить orchestrator_agent, новые модули
test_real_pipeline.py               # Один вызов Runner.run(orchestrator_agent)
requirements.txt                    # +playwright, +sqlite-vec (опционально)
```

**Не трогаем:**
```
playable_agents/
├── scenario_agent.py               # Работает хорошо
├── asset_generator_agent.py        # Работает хорошо
├── generator_agent.py              # Только generate_html(), fix_issues() удаляем
├── visual_qa_agent.py              # Обновляем только prompt
├── technical_qa_agent.py           # Работает хорошо
├── memory_store.py                 # Оставляем для inter-agent communication
├── prompts/
│   ├── scenario_agent.md           # Без изменений
│   └── technical_qa.md             # Без изменений
services/                           # Все сервисы без изменений
models/                             # Все модели без изменений
tools/                              # Все утилиты без изменений
```

**Принцип: минимальные изменения в работающем коде.** Новая функциональность — в новых файлах. Существующие агенты — только обновление промптов.

---

## Секция 10: Порядок реализации — пошаговый план

12 шагов, каждый атомарный и тестируемый отдельно. Зависимости указаны.

**Фаза 1 — Инфраструктура (нет зависимостей между шагами):**

```
Шаг 1: pip install playwright && playwright install chromium
        Добавить playwright в requirements.txt

Шаг 2: html_file_manager.py
        - save_html(html, version) → сохраняет файл, обновляет version history
        - read_section(start, end) → строки из файла
        - replace_section(start, end, new_code) → замена + validate syntax
        - rollback(version) → откат к конкретной версии
        - get_best_version() → версия с max overall score
        Тест: создать HTML, replace секцию, rollback

Шаг 3: screenshot_tool.py
        - take_screenshots(html_path, scene_spec) → [{state, base64}]
        - map_mechanic_to_actions(mechanic) → список Playwright actions
        - simulate_state(page, actions) → выполнить touch events
        Тест: скриншот статичного HTML, проверить что base64 не пустой

Шаг 4: error_classifier.py
        - classify_error(error) → {type, strategy, max_retries}
        - ErrorType enum: SYNTAX, REGRESSION, PLAYWRIGHT, RATE_LIMIT,
          CONTEXT_OVERFLOW, VISION_UNCLEAR, ASSET_FAILED
        Тест: unit-тесты на классификацию строк ошибок
```

**Фаза 2 — Промпты и память (после фазы 1):**

```
Шаг 5: prompts/quality_rubric.md
        Для каждой категории: описание score 1-3, 4-6, 7-8, 9-10
        Жанро-независимый, но с примерами

Шаг 6: prompts/orchestrator.md
        Роль + decision tree (PATCH/RETHINK/REGENERATE/CLARIFY)
        + правила + workflow

Шаг 7: Переписать prompts/generator_car_wash.md
        Quality requirements вместо code snippets

Шаг 8: Дополнить prompts/visual_qa.md
        Scoring 0-10 + per-state evaluation + priority_improvements

Шаг 9: memory_manager.py
        - search_memory(query, genre) → top-k результатов
        - save_memory(genre, scores, patterns, failed) → markdown файл
        - Первая версия: простой full-text search по markdown файлам
        - Позже: SQLite + vector embeddings
        Тест: save → search, проверить что находит
```

**Фаза 3 — Сборка (после фаз 1 и 2):**

```
Шаг 10: Переписать orchestrator.py
         - orchestrator_agent = Agent(tools=[12 tools])
         - Каждый tool — обёртка над инфраструктурой из фазы 1
         - Decision loop внутри LLM, не в коде
         Тест: mock tools, проверить что агент вызывает их

Шаг 11: Обновить __init__.py
         Добавить exports новых модулей

Шаг 12: Переписать test_real_pipeline.py
         Один вызов: Runner.run(orchestrator_agent, input, context)
         Проверки: iterations >= 2, final score >= 7,
         output файл существует
```

**Верификация после всех шагов:**
```
python test_real_pipeline.py
→ Ожидаем: 3-5 итераций, score >= 7,
  облака + physics + CSS animations в output
```

---

## Секция 11: Риски и edge cases

Что может пойти не так и как план это учитывает.

**Риск 1: Оркестратор зацикливается**
LLM-агент может повторять одни и те же действия бесконечно. Защита:
- Hard limit 7 итераций в коде (не в промпте — промпт LLM может проигнорировать)
- `html_file_manager` считает версии, после 7й — принудительный return best version
- Если одна и та же категория патчится 3 раза без улучшения — skip, перейти к следующей

**Риск 2: replace_section ломает нумерацию строк**
После замены 10 строк на 25 строк — все номера строк сдвигаются. Если оркестратор запомнил "physics на строке 300" — уже неверно. Защита:
- `read_html_section` и `replace_html_section` работают с АКТУАЛЬНЫМ файлом каждый раз
- Оркестратор ОБЯЗАН вызывать `read_html_section` перед каждым `replace` — это в промпте как правило
- Дополнительно: `html_file_manager` может искать секции по маркерам (`// === BACKGROUND ===`) а не только по номерам строк

**Риск 3: Claude не влезает в контекст оркестратора**
Оркестратор — LLM сам. За 7 итераций его контекст растёт: промпт + 7x (screenshots описания + scores + reasoning). Защита:
- Скриншоты НЕ передаются в контекст оркестратора (только в Gemini Vision)
- Оркестратор получает только текстовые scores + issues, ~500 токенов за итерацию
- При 7 итерациях: ~3500 токенов истории + ~4000 промпт = ~7500 токенов. Безопасно

**Риск 4: Первый запуск без памяти — низкое качество**
Нет memory hints → генератор опирается только на quality rubric → может быть 4-5 итераций. Защита:
- Quality rubric достаточно детальный чтобы дать score ~5-6 на первой генерации
- Это нормально: первый запуск — обучающий, последующие быстрее
- Можно seed memory вручную: записать паттерны из эталонного car-wash HTML в `memory/` перед первым запуском

**Риск 5: Gemini Vision нестабильно оценивает**
Один и тот же скриншот может получить score 6 и score 8 при повторном вызове. Защита:
- Structured output format (JSON) снижает вариативность
- Temperature 0 для Visual QA
- Если разброс между итерациями > 2 баллов при том же HTML — повторить оценку и усреднить

---

## Секция 12: Quality Rubric — детализация шкалы

Что конкретно означает каждый балл для каждой категории. Это основа по которой Visual QA оценивает, а оркестратор приоритизирует.

**Atmosphere (0-10):**
| Score | Что видим |
|---|---|
| 1-3 | Сплошной цвет фона. Нет глубины. Плоская сцена |
| 4-6 | Градиент неба, но нет облаков/частиц. Статичный фон |
| 7-8 | Градиент + облака с параллаксом (минимум 2 слоя). Тени на объектах |
| 9-10 | Многослойный параллакс (3+ слоя), частицы в воздухе, динамические тени, ощущение живого мира |

**UI Polish (0-10):**
| Score | Что видим |
|---|---|
| 1-3 | Текст и прогресс нарисованы на canvas. Нет стилей |
| 4-6 | HTML элементы, но без gradient/shadow. Базовые стили |
| 7-8 | CSS gradient progress bar, box-shadow на кнопках, readable шрифты |
| 9-10 | Glossy progress bar (::before), multi-layer shadows, CSS transitions на hover/active |

**Physics (0-10):**
| Score | Что видим |
|---|---|
| 1-3 | Инструмент/объект привязан к пальцу жёстко. Нет частиц |
| 4-6 | Базовые частицы (без гравитации). Инструмент следует за пальцем с задержкой |
| 7-8 | Verlet physics (15+ сегментов), частицы с гравитацией и decay |
| 9-10 | 20+ сегментов, adaptive damping, частицы с разной скоростью/размером, вторичные эффекты (капли, брызги) |

**Animations (0-10):**
| Score | Что видим |
|---|---|
| 1-3 | Мгновенные переходы. Нет CSS анимаций |
| 4-6 | Базовый fade-in/out. Один-два @keyframes |
| 7-8 | Victory sequence с setTimeout цепочкой. Pulse + shimmer на CTA. Плавные transitions |
| 9-10 | Хореографированная victory (3+ этапа), bounce с cubic-bezier, shimmer + pulse + appear на CTA, каждый UI элемент анимирован |

**Completeness (0-10):**
| Score | Что видим |
|---|---|
| 1-3 | Отсутствуют ассеты, placeholder'ы видны. Не все состояния работают |
| 4-6 | Все ассеты на месте, но некоторые состояния сломаны (victory не срабатывает) |
| 7-8 | Все состояния работают. MRAID интегрирован. Touch корректен |
| 9-10 | Все состояния + edge cases (двойное касание, resize). Platform detection. Идеальная навигация по состояниям |

**Overall = среднее арифметическое пяти категорий.**
