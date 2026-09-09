# Отчёт: Миграция Orchestrator V2 на Anthropic SDK

## Дата: 2026-02-09

## Что было сделано

### 1. Миграция с OpenAI Agents SDK → Anthropic Python SDK

**Причина**: OpenAI Agents SDK накапливает полную историю + 15 tool definitions на каждый turn. При HTML-surgery (read_html_section, search_html) контекст быстро растёт до 624K токенов → превышает 30K TPM лимит gpt-4.1. Improvement loop невозможен.

**Решение**: Anthropic SDK с `beta.messages.tool_runner()`:
- 200K контекстное окно
- Server-side `clear_tool_uses_20250919` — автоочистка старых tool results
- `@beta_async_tool` decorator для 15 tools через closure factory pattern

### 2. Файлы изменены

| Файл | Изменение |
|------|-----------|
| `requirements.txt` | Добавлен `anthropic>=0.52.0` |
| `playable_agents/orchestrator.py` | Полный rewrite (726 строк) |
| `playable_agents/__init__.py` | Убран `orchestrator_agent` export |
| `tests/test_real_pipeline.py` | Добавлен anthropic logging, resume=True |

### 3. Баги найдены и исправлены

| Баг | Причина | Фикс |
|-----|---------|------|
| `TypeError: BetaFunctionTool not JSON serializable` | Sync `@beta_tool` не совместим с async `tool_runner` | Все 15 tools → `@beta_async_tool` + `async def` |
| `prompt too long: 236K > 200K` | `read_html_section` возвращал 1.6MB HTML целиком | MAX_TOOL_OUTPUT_CHARS=30K, MAX_READ_LINES=200 |
| SDK compaction bug `parsed_output: Extra inputs not permitted` | Баг в SDK при compaction с BetaAsyncFunctionTool | Отключен client-side compaction, только server-side |
| `429 rate limit 30K input tokens/min` | Лимит Anthropic API org | `max_retries=10` с exponential backoff |
| `credit balance too low` | Исчерпан баланс API | Смена API ключа |

### 4. Финальная конфигурация

```python
# Tool output limits
MAX_TOOL_OUTPUT_CHARS = 30_000  # ~7.5K tokens
MAX_READ_LINES = 200

# Server-side context management
context_management = {
    "edits": [{
        "type": "clear_tool_uses_20250919",
        "trigger": {"type": "input_tokens", "value": 40000},
        "keep": {"type": "tool_uses", "value": 3},
        "clear_at_least": {"type": "input_tokens", "value": 15000},
    }]
}

# Client (max_retries=10, no compaction — SDK bug)
```

## Результаты теста

### Успешный прогон (22:57 - 23:04)

- **55 turns** — оркестратор работал без крашей
- **9 версий HTML** сгенерировано (v1-v9)
- **5 итераций** improvement loop
- **Context management сработал**: 98K → 10K tokens (turn 27→28)
- **Score: 3.6** (максимум, не достиг цели 7.0)
- **Стоимость: ~$8** за один прогон

### Версии и скоры

| Version | Size | Score | Примечание |
|---------|------|-------|------------|
| v1 | 1628KB | 3.6 | Базовая (от generator_agent) |
| v2 | 1628KB | — | Первый патч |
| v3 | 1628KB | — | Второй патч |
| v4 | 1628KB | 3.6 | Rollback к v1 |
| v5 | 1628KB | 3.0 | Другой подход — score упал |
| v6 | 1628KB | 3.6 | Rollback к v1 |
| v7 | 1628KB | 3.0 | Ещё попытка — score упал |
| v8 | 1628KB | 3.6 | Rollback к v1 |
| v9 | 1629KB | 3.6 | Финальный (parallax clouds) |

### Паттерн поведения оркестратора

Оркестратор зациклился: patch → evaluate → score drops → rollback → patch differently → score drops → rollback. Ни одна из попыток не подняла score выше 3.6.

## Ключевая проблема: грязь на весь экран

### Что говорит ТЗ (эталон)

Из `TZ_SNB_Car.md`:
> "Спрайт автомобиля car_clean. Поверх него отрисована грязь car_dirt."

**Правильная механика:**
1. Рисуем `car_clean` (чистый VW Bus) на canvas
2. Поверх рисуем `car_dirt` (PNG с прозрачным фоном, грязь только на контуре машины)
3. При drag пользователя — стираем `car_dirt`, открывая `car_clean`

**Reference assets:**
- `car_clean.png` — чистый красный VW Bus (70KB, с прозрачным фоном)
- `car_dirt.png` — грязь в форме контура машины (88KB, прозрачный фон сверху)
- `car_bright.png` — яркая версия для победного экрана

### Что сделал generator_agent (ошибка в v1)

```javascript
// output_v1.html, line 478-481
function initDirtMask() {
    maskCtx.fillStyle = '#000000';
    maskCtx.fillRect(0, 0, GAME_WIDTH, GAME_HEIGHT);  // ← ОШИБКА
}
```

`maskCanvas` (z-index: 15) заполняется **сплошным чёрным прямоугольником** 945x540 поверх всего. Вместо того чтобы отрисовать `car_dirt.png` (спрайт грязи на контуре машины), генератор нарисовал чёрный экран.

### Почему оркестратор не смог это исправить

1. **Оркестратор видит HTML только через скриншоты** — видит чёрный экран, пытается патчить CSS/JS
2. **Усечение контекста** (30KB max) — не может прочитать весь HTML (1.6MB), видит фрагменты
3. **Нет доступа к reference images** — оркестратор НЕ видит эталонные PNG, не знает как должна выглядеть car_dirt
4. **Нет diff между версиями** — не может сравнить "ожидание" vs "реальность"

### Корневая причина

**Generator agent** сгенерировал неправильный HTML с самого начала. Оркестратор получил сломанный v1 и пытался чинить патчами, но `initDirtMask()` — архитектурная ошибка, которую нельзя исправить мелкими правками.

**Проблема workflow**: generator видит base64 ассеты, но не понимает семантику `car_dirt` — что это прозрачный PNG-оверлей, а не текстура для заливки.

## Рекомендации

### Быстрые фиксы
1. **Детализировать промпт generator_agent**: явно описать layering (car_clean → car_dirt overlay → erase mask)
2. **Передавать метаданные ассетов**: описание каждого ("car_dirt: transparent PNG overlay, same position as car_clean, erase on drag")
3. **Снизить MAX_TOOL_OUTPUT_CHARS** (сделано: 100K → 30K) для экономии

### Системные улучшения
1. **Pre-validation**: проверять v1 перед improvement loop — если базовая механика сломана, перегенерировать
2. **Reference screenshots для оркестратора**: "вот как должно выглядеть" vs "вот что получилось"
3. **Стоимость**: $8/прогон неприемлемо. Рассмотреть Haiku для exploration, Sonnet для patching
4. **Стратегия регенерации**: если score после 2 итераций < 5.0, лучше перегенерировать с уточнённым промптом чем патчить
