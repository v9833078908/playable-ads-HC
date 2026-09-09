# План: Автономный оркестратор по принципам OpenClaw

## Контекст

**Проблема:** Pipeline генерирует функциональный, но визуально бедный HTML. Нет облаков, CSS-анимаций, полированных UI, хореографированных переходов. При этом система должна работать для ЛЮБОГО ТЗ и жанра — без эталонных шаблонов.

**Корневая причина:** Оркестратор — фиксированный pipeline без интеллекта. Не видит свой output (Visual QA отключён). Generator получает сниппеты и упрощает. Feedback loop передаёт только структурные ошибки.

**Решение по принципам OpenClaw:**
- Оркестратор становится **LLM-агентом** с tools для вызова sub-agents (как OpenClaw agent runtime)
- Система **ВИДИТ** свой output через Playwright screenshots + Gemini Vision
- **Адаптивная итерация** — оркестратор сам решает что улучшить, основываясь на визуальной оценке
- **Quality Knowledge** — знания о том что делает playable ads полированными (не код, а описание качества)

---

## Архитектура: Было → Стало

### БЫЛО (фиксированный pipeline):
```
for iteration in range(5):
    if iteration == 0: generate_html()
    else: fix_issues(issues_text)
    run_technical_qa()
    if passed: break
```

### СТАЛО (OpenClaw-style autonomous agent):
```
Orchestrator Agent (Claude Sonnet 4.5):
  tools: [analyze_spec, generate_assets, generate_html,
          take_screenshot, evaluate_visual, run_technical_qa,
          improve_html, ask_user]

  Сам решает порядок действий, видит результат, итерирует до качества
```

---

## Изменения (7 шагов)

### 1. Создать screenshot tool (Playwright)
**Новый файл:** `playable_agents/screenshot_tool.py`

Функция `take_screenshot(html_path) -> base64_png`:
- Принимает путь к HTML файлу
- Запускает Playwright headless Chromium
- Viewport 640x960 (mobile portrait)
- Ждёт загрузки всех изображений (networkidle)
- Делает screenshot → base64
- Возвращает base64 PNG

```python
async def take_screenshot(html_path: str) -> str:
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 640, "height": 960})
        await page.goto(f"file://{html_path}", wait_until="networkidle")
        await page.wait_for_timeout(1000)  # Let animations start
        screenshot = await page.screenshot(type="png")
        await browser.close()
    return base64.b64encode(screenshot).decode()
```

### 2. Создать quality knowledge prompt
**Новый файл:** `playable_agents/prompts/quality_rubric.md`

Описание того что делает playable ads полированными — не код, а КАЧЕСТВЕННЫЕ КРИТЕРИИ:

```markdown
# Playable Ad Quality Rubric

## Атмосфера и глубина
- Фон НЕ должен быть сплошным цветом — нужен градиент неба
- Параллакс-эффекты добавляют глубину (облака, частицы на разных слоях)
- Тени на элементах создают объём

## UI элементы
- Progress bar, кнопки, текст — HTML/CSS элементы (НЕ canvas-drawn)
- CSS linear-gradient для progress bar с glossy эффектом (::before pseudo-element)
- CSS box-shadow с несколькими слоями для 3D-эффекта кнопок

## Анимации
- @keyframes для: pulse (CTA), shimmer (CTA блик), buttonAppear (появление CTA)
- CSS transitions для плавных изменений состояний (opacity, width)
- Хореографированная victory sequence: задержки, crossfade, поэтапное появление

## Физика и частицы
- Частицы воды с гравитацией (vy += 0.2) для реалистичных дуг
- Шланг: >= 18 сегментов, Verlet integration, adaptive damping, гравитация
- Искры: радиальный взрыв с разными скоростями и временем жизни

## Интерактивность
- Canvas portrait 640x960 для мобильного UX
- Радиус стирания >= 40px (прощающий)
- Визуальный эффект при каждом касании (частицы, stream image)

## Victory последовательность
- НЕ мгновенный переход — плавный reveal с setTimeout задержками
- Crossfade progress bar → congratulations text
- CTA появляется с bounce-анимацией (cubic-bezier)
```

### 3. Улучшить generator prompt — quality-focused
**Файл:** `playable_agents/prompts/generator_car_wash.md` — ПЕРЕПИСАТЬ

Ключевое изменение: вместо 10 code snippets → **quality rubric + конкретные требования к реализации**:

```markdown
# Generator: Car Wash Playable Ad

Ты создаёшь ПОЛИРОВАННЫЙ, ПРОДАКШН-ГОТОВЫЙ playable ad.

## ОБЯЗАТЕЛЬНЫЕ качества (НЕ УПРОЩАТЬ!)

### Архитектура
- Canvas 640x960 portrait
- UI элементы (progress bar, CTA, текст) — HTML/CSS, НЕ canvas
- CSS @keyframes: pulse, shimmer, buttonAppear
- HTML progress bar с linear-gradient и glossy ::before эффектом

### Атмосфера
- Sky: createLinearGradient с цветовыми переходами
- Облака: параллакс-система (3 слоя: far/mid/near, 6-8 облаков)
- Тени на всех элементах

### Физика шланга
- 20 сегментов, segmentLength 30
- Verlet integration с prevX/prevY
- Adaptive damping: isMoving ? 0.92 : 0.80
- Гравитация: seg.y += 0.15
- 5 итераций constraint solving

### Частицы
- Вода: 4 штуки за spray, гравитация 0.2, life decay 0.015
- Искры: 8 штук radial burst при victory
- Water stream image с opacity 0.7

### Victory sequence
- setTimeout задержки для хореографии
- Crossfade: progress bar opacity → 0
- Info text fade-in с text-shadow
- CTA: buttonAppear animation → pulse → shimmer
- cubic-bezier(0.68, -0.55, 0.265, 1.55) для bounce

### Механика стирания
- Radius 42px
- globalCompositeOperation = 'destination-out'
- cleanPercent += 0.44 per touch (фиксированный инкремент)

[Далее: MRAID, Touch events, Game loop — сохранить текущие сниппеты]
```

### 4. Перестроить orchestrator как LLM-агент
**Файл:** `playable_agents/orchestrator.py` — метод `run_pipeline()` ПЕРЕПИСАТЬ

Новый подход: оркестратор — Agent с tools, который САМ решает что делать.

```python
from agents import Agent, function_tool, Runner

# Tools для оркестратора — обёртки над sub-agents
@function_tool
async def analyze_spec(ctx, spec_text: str) -> str:
    """Analyze TZ and create scene_spec + asset_list via Scenario Agent."""
    result = await Runner.run(scenario_agent, input=..., context=ctx.context)
    return result.final_output

@function_tool
async def generate_assets(ctx) -> str:
    """Generate missing assets via Asset Generator Agent."""
    result = await Runner.run(asset_generator_agent, input=..., context=ctx.context)
    return result.final_output

@function_tool
async def generate_html(ctx, instructions: str = "") -> str:
    """Generate HTML via Generator Agent. Pass specific quality instructions."""
    input_msg = f"Generate HTML. {instructions}" if instructions else "Generate HTML."
    result = await Runner.run(generator_agent, input=input_msg, context=ctx.context)
    return result.final_output

@function_tool
async def take_screenshot(ctx) -> str:
    """Save HTML to file, take Playwright screenshot, return base64 PNG."""
    from .screenshot_tool import capture_screenshot
    html = ctx.context["memory_store"].get_latest_html()
    # save to temp file, capture screenshot
    screenshot_b64 = await capture_screenshot(html)
    ctx.context["latest_screenshot"] = screenshot_b64
    return f"Screenshot captured ({len(screenshot_b64)} chars base64)"

@function_tool
async def evaluate_visual_quality(ctx) -> str:
    """Send screenshot to Gemini Vision for quality evaluation."""
    screenshot = ctx.context.get("latest_screenshot", "")
    result = await Runner.run(visual_qa_agent,
        input="Validate visual quality.", context={**ctx.context, "screenshot_base64": screenshot})
    return result.final_output

@function_tool
async def run_technical_checks(ctx) -> str:
    """Run technical QA checks."""
    result = await Runner.run(technical_qa_agent, input="Run all checks.", context=ctx.context)
    return result.final_output

@function_tool
async def improve_html(ctx, feedback: str) -> str:
    """Send specific improvement instructions to Generator Agent."""
    result = await Runner.run(generator_agent,
        input=f"Fix and improve: {feedback}", context=ctx.context)
    return result.final_output

# Orchestrator Agent
orchestrator_agent = Agent(
    name="PlayableAdOrchestrator",
    model="claude-sonnet-4-5-20250929",
    instructions=ORCHESTRATOR_PROMPT,  # см. ниже
    tools=[analyze_spec, generate_assets, generate_html,
           take_screenshot, evaluate_visual_quality,
           run_technical_checks, improve_html],
)
```

### 5. Написать orchestrator system prompt (OpenClaw-style)
**Новый файл:** `playable_agents/prompts/orchestrator.md`

```markdown
# Playable Ad Orchestrator

Ты автономный оркестратор, создающий ВЫСОКОКАЧЕСТВЕННЫЕ playable ads.
У тебя есть tools для вызова специализированных агентов.

## Workflow

1. **Анализ ТЗ**: analyze_spec() → получить scene_spec и asset_list
2. **Генерация ассетов**: generate_assets() → создать все визуальные ассеты
3. **Генерация HTML**: generate_html() → создать первую версию

4. **ЦИКЛ САМООЦЕНКИ** (до 5 итераций):
   a. take_screenshot() → увидеть результат
   b. evaluate_visual_quality() → получить оценку от Vision-модели
   c. run_technical_checks() → проверить техническое качество
   d. Проанализировать результаты:
      - Если visual QA PASSED и technical QA PASSED → готово!
      - Если есть проблемы → improve_html(конкретный feedback)
      - Повторить цикл

## Как давать feedback для improve_html()
НЕ просто перечисляй issues. Дай КОНКРЕТНЫЕ инструкции:
- "Добавь параллакс-систему облаков с 3 слоями (far/mid/near)"
- "Замени canvas progress bar на HTML div с CSS gradient"
- "Добавь @keyframes pulse и shimmer для CTA кнопки"
- "Увеличь количество сегментов шланга до 20, добавь гравитацию"

## Критерии качества
[Вставляется quality_rubric.md]

## Правила
- Максимум 5 итераций улучшений
- Если после 3 итераций visual quality не улучшается — остановись
- Всегда делай screenshot ПОСЛЕ каждого improve_html
- Приоритет: атмосфера > анимации > физика > мелкие детали
```

### 6. Обновить visual_qa_agent prompt
**Файл:** `playable_agents/prompts/visual_qa.md` — ДОПОЛНИТЬ

Добавить quality scoring (0-10) и конкретные категории:

```markdown
## Оценка качества (0-10)

Оцени каждую категорию:
- **Атмосфера** (0-10): Есть ли глубина? Градиент неба? Облака? Тени?
- **UI полировка** (0-10): CSS анимации? Glossy progress bar? 3D кнопки?
- **Физика** (0-10): Реалистичный шланг? Частицы с гравитацией?
- **Анимации** (0-10): Плавные переходы? Victory choreography?
- **Общее впечатление** (0-10): Выглядит как профессиональный продукт?

Средний балл < 7 = FAILED
Средний балл >= 7 = PASSED

Для каждой категории с баллом < 7, дай КОНКРЕТНОЕ описание что нужно улучшить.
```

### 7. Обновить exports, тест, установить Playwright
**Файлы:**
- `playable_agents/__init__.py` — добавить `orchestrator_agent`
- `test_real_pipeline.py` — переписать: один вызов `Runner.run(orchestrator_agent, ...)`
- `requirements.txt` — добавить `playwright`
- Команда: `playwright install chromium`

Новый тест:
```python
async def test_full_pipeline():
    from playable_agents.orchestrator import orchestrator_agent
    memory = MemoryStore()
    memory.set("spec_text", spec_text)
    memory.set("reference_assets", reference_assets)

    result = await Runner.run(
        orchestrator_agent,
        input="Create a high-quality playable ad from the spec and assets.",
        context={"memory_store": memory},
    )
    print(result.final_output)
```

---

## Файлы

| Файл | Действие |
|------|----------|
| `playable_agents/screenshot_tool.py` | CREATE — Playwright screenshot capture |
| `playable_agents/prompts/quality_rubric.md` | CREATE — Quality criteria (genre-independent) |
| `playable_agents/prompts/orchestrator.md` | CREATE — Smart orchestrator system prompt |
| `playable_agents/prompts/generator_car_wash.md` | REWRITE — Quality-focused вместо snippet-based |
| `playable_agents/prompts/visual_qa.md` | MODIFY — Добавить quality scoring 0-10 |
| `playable_agents/orchestrator.py` | REWRITE — LLM-agent с tools вместо fixed pipeline |
| `playable_agents/__init__.py` | MODIFY — Добавить orchestrator_agent |
| `test_real_pipeline.py` | REWRITE — Один вызов orchestrator_agent |
| `requirements.txt` | MODIFY — Добавить playwright |

## Порядок реализации

1. `pip install playwright && playwright install chromium`
2. Создать `screenshot_tool.py`
3. Создать `prompts/quality_rubric.md`
4. Переписать `prompts/generator_car_wash.md`
5. Дополнить `prompts/visual_qa.md`
6. Создать `prompts/orchestrator.md`
7. Переписать `orchestrator.py` — новый orchestrator_agent
8. Обновить `__init__.py`
9. Переписать `test_real_pipeline.py`
10. Запустить тест

## Верификация

1. `python test_real_pipeline.py` — полный прогон
2. Проверить что оркестратор сделал >= 2 итераций (generate → screenshot → evaluate → improve)
3. Проверить visual QA score >= 7/10
4. Открыть output_real_pipeline.html в браузере — визуальная проверка
5. Сравнить с эталоном: облака, CSS анимации, HTML progress bar, victory choreography
