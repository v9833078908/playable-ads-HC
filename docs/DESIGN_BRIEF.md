# Техническое задание на редизайн Playable Ads Generator

## 1. Описание продукта

**Playable Ads Generator** — AI-агент для автоматической генерации интерактивной рекламы (playable ads) из PDF-спецификаций.

**Целевая аудитория:** Маркетологи мобильных игр, UA-специалисты, креативные продюсеры.

**Ценность продукта:**
- Генерация playable ads за 5-10 минут вместо 3-5 дней разработки
- Не нужны навыки программирования
- Соответствие требованиям рекламных сетей (Unity, AppLovin, Mintegral)

---

## 2. Текущие проблемы интерфейса

### Критичные:
1. **Чат-интерфейс перегружен** — пользователь видит слишком много технических деталей (extraction summary, scene detection, JSON-структуры)
2. **Неинтуитивный flow** — непонятно, на каком этапе находишься и сколько еще осталось
3. **Scene cards в sidebar** — информация раскидана, трудно отслеживать прогресс
4. **Вопросы агента малочитаемы** — reasoning, suggestions, defaults смешиваются с основным вопросом
5. **Нет визуального фидбека** — не видно, как ответы влияют на финальный результат

### Второстепенные:
- Streamlit-стиль выглядит как dev-tool, не как продукт
- Нет онбординга для новых пользователей
- Preview iframe появляется только в конце
- Невозможно вернуться назад и изменить ответы

---

## 3. User Flow (текущий)

```
1. Upload Screen
   ├─ Upload PDF (техническое задание)
   ├─ Upload Images (ассеты игры: фоны, персонажи, иконки)
   └─ Click "Start Analysis"

2. Scenario Building (главная проблема)
   ├─ AI анализирует PDF → выводит в чат "Detected X scenes"
   ├─ AI задает вопросы по каждой сцене (3-7 вопросов на сцену)
   │  ├─ Вопрос: "What mechanic for Scene 1?"
   │  ├─ Reasoning: "This scene appears to be a tutorial..."
   │  ├─ Suggestions: "GridPlacement, DragDrop, Merge"
   │  └─ User вводит ответ в chat input
   ├─ Scene cards обновляются в sidebar (expander'ы)
   └─ Repeat для всех сцен

3. Confirmation Screen
   ├─ Review scenario (все scene cards)
   ├─ Edit если нужно
   └─ Click "Generate Playable"

4. Download Screen
   ├─ Preview HTML в iframe
   ├─ Показ validation (size, MRAID compliance)
   └─ Download button
```

---

## 4. Желаемый User Flow (для редизайна)

```
1. Upload & Quick Start
   ├─ Дружелюбный upload с drag-and-drop
   ├─ Preview загруженных файлов (thumbnails)
   └─ Один клик "Generate"

2. Interactive Scenario Builder (НЕ чат!)
   ├─ Визуальная timeline/карта сцен
   ├─ Карточки сцен показаны сразу
   ├─ Вопросы появляются inline в карточке
   ├─ Live preview изменений (если возможно)
   └─ Progress bar: "Scene 2 of 5"

3. Review & Adjust
   ├─ Полный обзор сценария
   ├─ Inline editing любых полей
   └─ Optional: A/B варианты от AI

4. Generate & Export
   ├─ Live progress: "Generating HTML... 60%"
   ├─ Preview с device frames (mobile)
   ├─ Validation results (size, compliance)
   └─ Download + share options
```

---

## 5. Ключевые экраны для редизайна

### 5.1 Upload Screen
**Текущее:** Sidebar с file_uploader + info text в main area

**Нужно:**
- Hero section с value proposition
- Drag-and-drop зона с микроанимациями
- Preview загруженных файлов (PDF pages as thumbnails, image grid)
- Clear CTA button "Start Building"
- Optional: примеры/templates для быстрого старта

**Референсы:** Notion file upload, Figma import screen, Loom upload

---

### 5.2 Scenario Builder (ГЛАВНЫЙ ЭКРАН)
**Текущее:** Streamlit chat + sidebar с expanders

**Проблемы:**
- Чат скрывает контекст предыдущих ответов
- Scene cards в sidebar — приходится скроллить sidebar и main area одновременно
- Вопросы выглядят как техническая документация
- Непонятно, сколько еще вопросов

**Нужно:**
- **Layout:** Горизонтальный timeline сцен сверху + активная карточка в центре
- **Scene Timeline:**
  - Все сцены видны сразу (горизонтальный scroll если много)
  - Визуальные состояния: Empty (⚪) → In Progress (🔵) → Complete (✅)
  - Click на сцену → переход к ней
  - Progress indicator: "3/7 scenes complete"
- **Active Scene Card:**
  - Большая карточка в центре экрана
  - Scene title + icon (tutorial/battle/victory)
  - Вопросы показываются inline, НЕ как чат
  - Каждый вопрос = отдельный UI-элемент (не текстовый инпут)
- **Question UI:**
  - Вопрос текстом (крупный шрифт)
  - Reasoning мелким шрифтом под вопросом (collapsible)
  - Suggestions как кнопки/chips (клик = выбор)
  - Или custom input если suggestions не подходят
  - Default value показан placeholder'ом
- **Navigation:**
  - "Next Question" button (или auto-advance после ответа)
  - "Previous" button для возврата
  - "Skip" для optional вопросов
- **Live Updates:**
  - Карточка сцены обновляется в реальном времени
  - Анимация перехода между вопросами

**Референсы:**
- Typeform (пошаговые формы с красивой анимацией)
- Notion database cards
- Linear issue cards
- Airtable interface designer

**Макет (ASCII):**
```
┌────────────────────────────────────────────────────────────────┐
│  Progress: 3/7 scenes complete                        [Preview] │
├────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ⚪Scene1  ✅Scene2  🔵Scene3  ⚪Scene4  ⚪Scene5  ⚪Scene6       │
│  Hook     Repair   Battle    Merge    Victory  Store           │
│                        ↑ Active                                 │
├────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  ⚔️ Scene 3: Battle Phase                              │    │
│  │                                                          │    │
│  │  Question 2 of 5                                        │    │
│  │                                                          │    │
│  │  What should happen during this battle?                │    │
│  │  This scene appears to be a combat phase based on      │    │
│  │  the PDF description. [Show reasoning]                 │    │
│  │                                                          │    │
│  │  💡 Suggestions:                                        │    │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐     │    │
│  │  │ Auto-battle │ │ HP bars only│ │ With enemies│     │    │
│  │  └─────────────┘ └─────────────┘ └─────────────┘     │    │
│  │                                                          │    │
│  │  Or enter custom: _________________________            │    │
│  │                                                          │    │
│  │  [← Previous]              [Skip]    [Next Question →] │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                  │
└────────────────────────────────────────────────────────────────┘
```

---

### 5.3 Confirmation Screen
**Текущее:** Все scene cards в sidebar, кнопка "Generate"

**Нужно:**
- Красивый overview всего сценария
- Карточки сцен в grid layout (2-3 колонки)
- Inline editing (click любое поле → edit mode)
- Visual flow diagram (стрелки между сценами)
- Warnings/issues показаны явно (⚠️ "Scene 4 duration too long")
- Estimated playable size/duration

**Референсы:** Figma prototype flow, Miro board view

---

### 5.4 Generation & Download
**Текущее:** Spinner → iframe preview + download button

**Нужно:**
- Animated progress с этапами:
  - "Analyzing scenario... ✓"
  - "Rendering HTML... 60%"
  - "Inlining assets... 80%"
  - "Validating compliance... 95%"
  - "Done! ✓"
- Preview с device frame (iPhone/Android mock)
- Validation results как checklist:
  - ✅ Size: 2.3 MB (< 5 MB limit)
  - ✅ MRAID compliant
  - ✅ No external requests
  - ⚠️ Warning: No audio (optional)
- Download options:
  - Download HTML
  - Copy embed code
  - Send to email
- "Start Over" / "Edit Scenario" buttons

**Референсы:** Loom processing screen, Vercel deployment status

---

## 6. UI Components для дизайна

### 6.1 Scene Card Component
**Состояния:**
- Empty (⚪) - сцена создана, но не заполнена
- In Progress (🔵) - идет заполнение вопросов
- Complete (✅) - все вопросы отвечены
- Warning (⚠️) - есть проблемы (например, duration слишком большой)

**Содержимое:**
- Scene number + title
- Scene type icon (🎯 tutorial, ⚔️ battle, 🏆 victory)
- Mechanics list (chips)
- UI elements (title, subtitle, CTA text)
- Timing info (duration, transitions)
- Progress indicator (сколько вопросов отвечено)

**Взаимодействие:**
- Click → открыть для редактирования
- Hover → показать quick preview
- Drag → изменить порядок сцен (если нужно)

---

### 6.2 Question Component
**Типы вопросов:**
1. **Choice** - выбор из suggestions (кнопки/chips)
2. **Text** - текстовый input (для copy: titles, CTA)
3. **Number** - slider или number input (duration, HP)
4. **Multi-select** - чекбоксы (mechanics: drag + merge + battle)

**Элементы:**
- Question text (clear, non-technical)
- Reasoning (collapsible, серый текст)
- Input area (зависит от типа)
- Optional indicator ("You can skip this")
- Default value (placeholder или hint)

---

### 6.3 Progress Indicators
**Global progress:**
- Top bar: "Building scenario: 3/7 scenes complete"
- Percentage: "42% complete"
- Animated progress bar

**Scene progress:**
- In timeline: "3/5" под карточкой
- Visual: filled circle states

**Generation progress:**
- Step-by-step с анимацией
- ETA: "~30 seconds remaining"

---

## 7. Визуальный стиль

### Текущий (shadcn-inspired):
- Minimalist, black/white/gray
- Subtle borders, shadows
- System font stack
- Работает, но скучный

### Желаемый:
- **Более игровой**, но профессиональный
- **Цветовая схема:**
  - Primary: яркий акцент (не фиолетовый!) — синий, зеленый, оранжевый
  - Background: светлый или опционально dark mode
  - Scene types имеют свои цвета (tutorial = blue, battle = red, victory = gold)
- **Typography:**
  - Heading font: что-то с характером (не Inter/Roboto)
  - Body font: читаемый, modern (может быть system font)
- **Иконки:**
  - Использовать иконки для scene types, mechanics, states
  - Lucide, Heroicons, или custom
- **Анимации:**
  - Smooth transitions между вопросами
  - Confetti/celebration при завершении сцены
  - Pulse на active элементах
  - Skeleton loaders при загрузке

---

## 8. Технические требования

### Must-have:
- Responsive (desktop primary, mobile secondary)
- Работает в современных браузерах (Chrome, Safari, Firefox)
- Accessibility: keyboard navigation, screen readers
- Light/Dark mode (optional, но желательно)

### Framework (если нужен код):
- Текущий: Streamlit (Python)
- Опции для редизайна:
  - Остаться на Streamlit, но с custom CSS + components
  - Переписать на React/Next.js + Python backend API
  - Использовать React + Streamlit через components

### Приоритет:
**Фокус на Scenario Builder screen** — это 80% времени пользователя.

---

## 9. Референсы и вдохновение

### Product flow:
- **Typeform** — пошаговые формы с красивой анимацией
- **Framer** — wizard-style onboarding
- **Gamma.app** — AI-генерация презентаций с пошаговым flow

### UI Components:
- **Linear** — issue cards, status indicators
- **Notion** — database cards, inline editing
- **Airtable** — interface designer

### Generation progress:
- **Loom** — processing video screen
- **Vercel** — deployment progress
- **Replicate** — AI model running status

### Playable ads tools (конкуренты):
- **Luna Creator** — no-code playable builder
- **Playable Factory** — template-based
- **Adact** — gamification platform

---

## 10. Deliverables от дизайнера

### Phase 1 (критично):
1. **Scenario Builder screen** — главный экран
   - Desktop layout (1920x1080, 1440x900)
   - Scene timeline component
   - Active scene card с вопросами
   - 3-4 примера разных типов вопросов
2. **UI Kit:**
   - Scene card states (empty, in-progress, complete, warning)
   - Question types (choice, text, number)
   - Buttons, inputs, badges
   - Color palette + typography

### Phase 2 (важно):
3. **Upload screen** — первый экран
4. **Confirmation screen** — обзор сценария
5. **Generation & Download screen**

### Phase 3 (nice to have):
6. Dark mode variants
7. Mobile layouts
8. Micro-animations specs
9. Empty states, error states

---

## 11. Вопросы для обсуждения с дизайнером

1. **Как показывать много сцен?** — horizontal scroll, pagination, или collapse?
2. **Показывать live preview во времяbuilderа?** — split screen или отдельная вкладка?
3. **Editing после generation** — можно ли вернуться и изменить сценарий?
4. **Mobile experience** — насколько критично? Пока 95% пользователей на desktop
5. **Branding** — есть ли логотип, название продукта?

---

## 12. Текущий стек (для контекста)

**Frontend:**
- Streamlit (Python web framework)
- Custom CSS (shadcn-inspired)
- No React/Vue (пока)

**Backend:**
- Python (asyncio)
- OpenAI Agents SDK
- Google Gemini Vision API

**Data flow:**
```
PDF + Images
  → AI analysis (brief + assets)
  → ScenarioBuilder (questions)
  → User answers
  → PlayableSpec (JSON)
  → Template renderer
  → HTML file
```

---

## Контакт

При вопросах или нужна дополнительная информация — пиши в Slack или на email.

**Priority:** Высокий
**Deadline:** ASAP
**Бюджет:** [уточнить]

---

**P.S.** Главная боль — чат интерфейс. Пользователи теряются, не понимают, сколько еще вопросов, и не видят результат своих ответов. Нужен визуальный, понятный, НЕ чатовый интерфейс.
