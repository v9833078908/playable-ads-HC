Ниже — детальное ТЗ архитектуры (и для “идеального продукта”, и для MVP на 1–2 дня хакатона) с опорой на ваш пример PDF ТЗ и итоговый single-file HTML.

0) Контекст, который фиксируем как “истину” из ваших файлов
Ограничения/комплаенс playable (must-have)

Из PDF явно следуют требования (как минимум под Applovin/Unity-style проверку): один HTML, без внешних файлов, ассеты в base64, MRAID, не стартовать до viewable/ready, не запускать звук до first interaction, ≤ 5MB, без сетевых запросов и т.п. 

Pirate Ships Reference TZ

Референсный формат single-file HTML

Ваш пример HTML делает ровно то, что нужно для сеток: в коде есть MRAID viewableChange gate и “обвязка” super_html с download() через mraid.open, а также встроенный base64 zip (window.__zip = "UEsDB...") внутри одного файла. 

PirateShips_unity

Сценарий playable (storyboard)

PDF описывает конкретный пайплайн сцен (Repair → Weapons → Merge → Victory/Store) с drag-and-drop в клетки и merge механикой. 

Pirate Ships Reference TZ

1) Цель продукта (идеальная)

Вход: PDF ТЗ + несколько JPG/PNG ассетов (скрины, персонажи, UI), + (опционально) store links/язык/сеть.
Процесс: агент задаёт уточняющие вопросы “ровно столько, сколько надо”, затем собирает playable.
Выход: 1 файл index.html (self-contained, готов к загрузке маркетологами).

2) Главная идея архитектуры: не “генерировать игру с нуля”, а “собрать playable из блоков”

Чтобы уложиться в хакатон и снизить риск нерабочего кода, правильнее:

Сделать “библиотеку механик” (building blocks): GridPlacement, DragDrop, Merge2→1, BattleLoop, HP bars, Tutorial overlay, Reward screen.

Генерацию через LLM свести к:

извлечению требований (из PDF/картинок),

заполнению параметров блоков (копирайт, позиции, тайминги, какие ассеты куда),

рендеру по шаблону (template → HTML/JS/CSS),

авто-валидации.

Это ближе к тому, как “Sett-подобные” системы масштабируются: вариативность = параметры/ассеты/копирайт, а не переписывание движка каждый раз.

3) Архитектура ИИ-агента (production target) на базе OpenAI Agents SDK
Почему Agents SDK

Нам нужен управляемый workflow: многошаговый диалог, tool calling, трассировка, роли, циклы “сгенерил → проверил → починил”. Это прямой use-case Agents SDK и function/tool calling .

Компоненты

A. UI (Web):

Upload: PDF + images

Чат/опросник уточнений

Preview iframe (рендер HTML)

Export: скачать index.html

B. Backend (Python/FastAPI):

Storage сессии (in-memory/SQLite)

Оркестратор workflow

Инструменты (tools) для агента: парсинг PDF, разбор изображений, сбор ассетов, генерация HTML по шаблону, валидация

C. Agent Workflow (multi-role):

BriefExtractorAgent

читает PDF (в т.ч. как картинки страниц) и вытаскивает:

сети/ограничения (MRAID/5MB/one-file),

storyboard сцен,

обязательный copy (CTA тексты),

список недостающих данных (“unknowns”)

AssetMapperAgent

анализирует входные JPG/PNG (что фон, что иконка, что персонаж),

предлагает “слоты” ассетов (background battle, module icons, reward items…)

ClarifyAgent

генерирует минимальный набор вопросов (см. раздел 5)

PlayablePlannerAgent

строит PlayableSpec.json (DSL) — формализованный план playable

TemplateComposerAgent

выбирает шаблон (например ship_grid_merge_v1)

заполняет параметры

QA/ComplianceAgent

запускает валидаторы:

“single file?”

“нет внешних запросов?”

“MRAID gating есть?”

“старт после viewable/ready?”

“CTA через mraid.open?”

“вес < 5MB?”

при ошибках формирует patch-задание для Composer

PackagerAgent

инлайнит ассеты (base64)

(опц.) упаковывает в zip-строку внутри HTML (как у вас в примере) 

PirateShips_unity

минифицирует

4) DSL: PlayableSpec (ключ к управляемой генерации)

Схема (упрощё

PirateShips_unity

"title": "...", "language": "RU", "network": "applovin", "max_size_mb": 5 },
"mraid": { "start_gate": ["ready", "viewableChange"], "click_url_android": "...", "click_url_ios": "..." },
"layout": { "base_resolution": [1080,1080], "safe_area": true, "orientation": "both" },
"assets": {
"images": [{"id":"bg_ocean","file":"002.jpg","role":"background"}],
"sprites": [{"id":"repairman","file":"Repairer.png","role":"unit"}]
},
"scenes": [
{
"id": "repair_tutorial",
"ui": { "title":"REPAIR YOUR SHIP", "subtitle":"DRAG REPAIRMANS ON SHIP" },
"mechanics": [
{ "type":"GridPlacement", "grid":[3,2], "required":[{"asset":"repairman","cells":1}] },
{ "type":"GridPlacement", "required":[{"asset":"shield","cells":2}] }
]
},
{ "id":"battle_1", "mechanics":[{"type":"BattleLoop","enemy_fire":true,"repair_tick":true}] },
{ "id":"weapons_tutorial", "mechanics":[{"type":"GridPlacement","required":[{"asset":"cannon","cells":1},{"asset":"cannon","cells":1}]}] },
{ "id":"merge_tutorial", "mechanics":[{"type":"MergeTwoToOne","from":"cannon","to":"skeleton_cannon","result_cells":2}] },
{ "id":"victory", "ui": { "title":"VICTORY!", "cta":"TAKE REWARD" }, "mechanics":[{"type":"CTAOpenStore"}] }
]
}


Эта структура 1) идеально ложится на ваш storyboard :contentReference[oaicite:7]{index=7}, 2) позволяет делать вариации без переписывания игры.

---

## 5) Уточняющие вопросы (то, что аг:contentReference[oaicite:8]{index=8} агент спрашивает **только то, что критично для генерации** и что не получается однозначно вытащить из PDF/картинок.

**Минимальный набор для MVP:**
1) **Сеть/площадка** (Applovin / Mintegral / другое) — влияет на MRAID/проверки :contentReference[oaicite:9]{index=9}  
2) **Store links** (iOS/Android) — для `mraid.open()` :contentReference[oaicite:10]{index=10}  
3) **Язы:contentReference[oaicite:11]{index=11} RU/EN :contentReference[oaicite:12]{index=12}  
4) **Ориентация** (p:contentReference[oaicite:13]{index=13}:contentReference[oaicite:14]{index=14}  
5) **Какие картинки :contentReference[oaicite:15]{index=15}ётся уверенно смэппить: “это фон?”, “это иконка:contentReference[oaicite:16]{index=16}
6) **Целевой “look & feel” степень упрощения** (пример: “оставляем low-poly, но без тяжелых VFX”)

**В production версии** добавляются: длительность, допустимый вес, необходимость аналитики, фейковые/реальные UI элементы, требования по брендингу.

---

## 6) Технические требования к HTML runtime (прямо для разработчика)

### 6.1. Обязательная MRAID-обвязка
Должно быть:
- `mraid` ready + `viewableChange` gate (старт только когда можно) :contentReference[oaicite:17]{index=17}  
- запрет “трогать DOM/игру до ready” и запрет звука до первого взаимодействия — это в ваших :contentReference[oaicite:18]{index=18}:contentReference[oaicite:19]{index=19}  
- clickthrough только через `mraid.open()` (или fallback `window.open`) :contentReference[oaicite:20]{index=20}:contentReference[oaicite:21]{index=21}контракт:**
- `window.super_html.game_ready()` — вызывается после инициализ:contentReference[oaicite:22]{index=22}tml.download()` — CTA

(Это совместимо с вашим примером структуры `super_html`) :contentReference[oaicite:23]{index=23}

### 6.2. Single-file pack
Два уровня:
- **MVP:** все изображения инлайн `data:image/...;base6:contentReference[oaicite:24]{index=24}>`
- **Как в вашем примере:** все ассеты складываем в zip → base64 строка `window.__zip="UEsDB..."` и маленький распаковщик на старте :contentReference[oaicite:25]{index=25}

### 6.3. Никаких внешних запросов
- запрет XHR/Fetch/CDN (в production)
- на хакатоне можно д:contentReference[oaicite:26]{index=26}view режиме, но экспорт должен быть self-contained.

### 6.4. Блоки механик (реализация)
Для вашего сценария достаточно:
- Grid 3×2 (или параметризуемо)
- Drag&Drop с подсветкой целевых клеток
- Merge (drag item A onto B → replace with C)
- Battle симуляция (HP bars + периодический урон/починка)
- Victory popup + CTA

---

## 7) MVP на хакатон (1–2 дня): что реально сделать
Цель MVP: **на вход PirateShips-подобный PDF + jpg → на выход working HTML по одному шаблону** (grid/drag/merge/victory).

### MVP scope (жёстко режем)
- **1 шаблон**: `ship_grid_merge_v1` (ровно ваш storyboard) :contentReference[oaicite:27]{index=27}  
- ассеты: фон(ы) + 5 иконок внизу + 1–2 “улучшенных” итема для победы
- никаких сложных 3D/phy:contentReference[oaicite:28]{index=28}а

### План работ (очень прикладной)
**День 1**
1) FastAPI + простая Web UI (upload + чат + preview iframe)
2) Tool: `ingest_files(session_id, pdf, images[])`
3) Tool: `extract_brief(pdf_images) -> DraftBrief`
4) Tool: `propose_questions(DraftBrief) -> questions[]`
5) Ручной ответ в UI → `answers`
6) `build_playable_spec(DraftBrief, answers, assets_index) -> PlayableSpec.json`
7) `render_template(PlayableSpec) -> index.html` (пока без минификации)

**День 2**
8) Инлайн base64 для всех картинок
9) Валидации:
   - статический анализ HTML (нет `http`, нет `<script src=...>`)
   - размер файла
   - smoke test (headless Chrome/Playwright: открыли, нет ошибок, скрин)
10) MRAID wrapper (ready/viewableChange gate + clickthrough) как в референсе :contentReference[oaicite:29]{index=29}  
11) Экспорт `index.html`

---

## 8) Разбор предложенного плана вашего знакомого (что взять,:contentReference[oaicite:30]{index=30}**
- Ролевая схема “Architect → Coder → Validator” — это верно для устойчивости.
- “Fixer loop” (генерация → проверка → исправление) — must.
- Требование “Single-File Output” — совпадает с вашим PDF :contentReference[oaicite:31]{index=31}

**Что плохо/чего не хватает именно под ваши требования:**
- **CDN Phaser** (даже временно) лома:contentReference[oaicite:32]{index=32}ту (в сетках часто запрещено).
- Нет явного **MRAID gating** (ready/viewableChange), хотя у вас это прямо в требованиях :contentReference[oaicite:33]{index=33}  
- Нет формализации в виде **PlayableSpec/DSL** → LLM будет “кодить игру”, а не “собирать из бл:contentReference[oaicite:34]{index=34}вать.
- Unity упомянут, но pipeline “Unity WebGL в один HTML ≤5MB” нереалистичен для большинства сборок. Поэтому на MVP лучше честно делать **HTML-шаблон playable**, который выглядит как игра (через ассеты), но не тащит Unity runtime.

**Что берем как лучшее:**
- Agentic pipeline + validator loop
- Single-file requirement
- Идея “использовать заглушки/простые ассеты” — но в вашем кейсе заглушки заменяются входными JPG/PNG.

---

## 9) Acceptance Criteria (чеклист готовности)
1) `index.html` открывается локально, без интернета.
2) Нет внешних ссылок/запросов.
3) Старт игры только после `mraid ready` + `viewableChange` (или fallback без mraid) :contentReference[oaicite:35]{index=35}  
4) Звук выключен до первого взаимодействия :contentReference[oaicite:36]{index=36}  
5) Есть tutorial fl:contentReference[oaicite:37]{index=37}→ Victory) :contentReference[oaicite:38]{index=38}  
6) CT:contentReference[oaicite:39]{index=39} `mraid.open()` :contentReference[oaicite:40]{index=40}  
7) Размер ≤ 5M:contentReference[oaicite:41]{index=41}едупреждение) :contentReference[oaicite:42]{index=42}

---

Есл:contentReference[oaicite:43]{index=43}*конкретное “ТЗ для разработчика” в формате PRD/Tech Spec*:contentReference[oaicite:44]{index=44}турами папок, и псевдокодом tools/агентов) под твой стек (Python + OpenAI Agents SDK + простой фронт) — так, чтобы это можно было отдать и за 1–2 дня реально собрать.
::contentReference[oaicite:45]{index=45}
