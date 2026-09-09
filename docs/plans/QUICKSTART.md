# 🚀 Playable Ads Agent — Quick Start (36h Hackathon)

## TL;DR

**Что делаем:** AI-агент, который из PDF ТЗ + картинок генерирует готовый playable ad HTML.

**Стек:** Python + Streamlit + OpenAI GPT-4o + Jinja2

**Результат:** Один файл `index.html` ≤5MB, готовый к загрузке в AppLovin/Unity.

---

## 🎯 MVP Scope (жёстко!)

| Делаем | НЕ делаем |
|--------|-----------|
| 1 шаблон (ship_grid_merge) | Несколько шаблонов |
| GridPlacement механика | Сложные физика/3D |
| Merge механика | Звук/музыка |
| Battle (HP bars) | Генерация ассетов |
| MRAID wrapper | A/B тестирование |
| Base64 inline | Analytics |

---

## 📁 Структура проекта

```
playable-agent/
├── app.py                  # Streamlit UI
├── agent/
│   └── tools.py            # 5 tools для агента
├── templates/
│   └── ship_grid_merge_v1/
│       ├── template.html   # Jinja2 шаблон
│       └── mechanics/      # JS механики
└── build/
    └── pipeline.py         # Сборка HTML
```

---

## 🔧 5 Tools агента

```python
# 1. Парсинг PDF
extract_brief_from_pdf(pdf) → DraftBrief

# 2. Анализ картинок (GPT-4V)
analyze_images(images[]) → AssetMapping

# 3. Генерация спецификации
generate_playable_spec(brief, assets, answers) → PlayableSpec

# 4. Рендер HTML
render_playable(spec) → index.html

# 5. Валидация
validate_playable(html) → {valid, errors, size_kb}
```

---

## ⚡ MRAID Requirements (Critical!)

```javascript
// Обязательный код в каждом playable:

// 1. Ждём ready
if (mraid.getState() === 'loading') {
  mraid.addEventListener('ready', onReady);
} else {
  onReady();
}

// 2. Ждём viewable
function onReady() {
  if (mraid.isViewable()) {
    startGame();
  } else {
    mraid.addEventListener('viewableChange', onViewable);
  }
}

// 3. CTA через mraid.open()
function openStore() {
  mraid.open(storeUrl);
}

// 4. Звук ТОЛЬКО после interaction
document.addEventListener('touchstart', enableAudio, {once: true});
```

---

## 📋 Checklist перед сдачей

- [ ] Один HTML файл
- [ ] Размер < 5MB
- [ ] Нет `src="http..."`
- [ ] Есть MRAID ready gate
- [ ] Есть viewableChange handling
- [ ] Звук после interaction
- [ ] CTA через mraid.open()
- [ ] Работает portrait + landscape

---

## 🏃 План на 36 часов

### День 1 (0-12ч)
- Setup + Streamlit UI
- Tool: extract_brief
- Tool: analyze_images
- HTML шаблон skeleton

### День 2 (12-24ч)
- GridPlacement механика
- Merge механика
- BattleLoop механика
- render_playable tool

### День 3 (24-36ч)
- MRAID wrapper
- Base64 inlining
- Validation
- E2E test + fix bugs

---

## 🔗 Полезные ссылки

- **Полное ТЗ:** `playable-agent-spec.md`
- **Пример спеки:** `pirate-ships-playable-spec.json`
- **MRAID Spec:** https://iabtechlab.com/standards/mraid/
- **Luna Examples:** https://github.com/LunaCommunity/Playable-Examples
- **Playable SDK:** https://github.com/smoudjs/playable-sdk

---

## ❓ Вопросы агента пользователю

**Всегда спрашиваем:**
1. Целевая сеть? (AppLovin / Unity / Mintegral)
2. Store URLs? (iOS / Android)
3. Язык? (RU / EN)

**Спрашиваем если неясно:**
4. Какая картинка — фон?
5. Какой персонаж — ремонтник?

---

## 🧪 Тестирование

```bash
# Локально
open output/index.html

# AppLovin Preview
https://p.applov.in/playablePreview

# Проверка размера
ls -la output/index.html | awk '{print $5/1024 " KB"}'

# Проверка внешних ссылок
grep -E 'src="https?://' output/index.html
# Должно быть пусто (кроме store URLs в mraid.open)
```

---

**Удачи на хакатоне! 🏆**
