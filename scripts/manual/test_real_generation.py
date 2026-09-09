#!/usr/bin/env python3
"""
Тест генерации HTML с реальными ассетами из существующих данных
"""

import sys
import json
from pathlib import Path

from models.spec import PlayableSpec
from playable_agents.html_generator import generate_html

print("🧪 Тест генерации HTML с реальными ассетами")
print("=" * 60)

# Ищем существующие JSON файлы со спецификациями
spec_files = list(Path(".").rglob("*.json"))
spec_files = [f for f in spec_files if "spec" in f.name.lower() or "playable" in f.name.lower()]

if not spec_files:
    print("❌ Не найдены JSON файлы со спецификациями")
    print("\nСоздаю тестовую спецификацию с mock данными...")

    # Создаем минимальную тестовую спецификацию
    test_spec = {
        "meta": {
            "title": "Test Car Wash - Real Assets",
            "language": "EN"
        },
        "mraid": {
            "android_url": "https://play.google.com/store/apps/details?id=com.test.carwash",
            "ios_url": "https://apps.apple.com/app/car-wash-test/id123456789"
        },
        "assets": {
            "images": {
                "char_0": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAFUlEQVR42mNk+M9Qz0AEYBxVSF+FAP0QBADKuv8sAAAAAElFTkSuQmCC",
                "tool_0": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAFUlEQVR42mP8z8BQz0AEYBxVSF+FAP0BBQDKuv8sAAAAAElFTkSuQmCC",
                "decoration_0": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAFUlEQVR42mNkYPhfz0AEYBxVSF+FAP0TBgDKuv8sAAAAAElFTkSuQmCC"
            },
            "background": None
        },
        "scenes": [
            {
                "id": "scene_tutorial",
                "type": "tutorial",
                "background": "#87CEEB",
                "ui": {
                    "progress_text": "0% Чисто",
                    "victory_text": "🎉 Идеально!",
                    "cta_button": "Скачать игру"
                }
            }
        ],
        "mechanics": ["drag-drop", "canvas"]
    }

    spec = PlayableSpec(**test_spec)
    source = "mock data"
else:
    print(f"✅ Найдено {len(spec_files)} JSON файлов")
    print("\nВыбираю первый файл:", spec_files[0])

    with open(spec_files[0], 'r') as f:
        data = json.load(f)

    spec = PlayableSpec(**data)
    source = str(spec_files[0])

print(f"\n📄 Источник: {source}")
print(f"📝 Заголовок: {spec.meta.get('title', 'N/A')}")
print(f"🎮 Механики: {spec.mechanics}")
print(f"🖼️  Количество ассетов: {len(spec.assets.get('images', {}))}")

if spec.assets.get('images'):
    print("\n🖼️  Список ассетов:")
    for key in spec.assets['images'].keys():
        data_url = spec.assets['images'][key]
        if data_url:
            size = len(data_url)
            print(f"  - {key}: {size} bytes")
        else:
            print(f"  - {key}: ❌ пустой")
else:
    print("\n⚠️  Нет ассетов в images")

print("\n" + "=" * 60)
print("🔨 Генерирую HTML...")

try:
    html = generate_html(spec)

    # Сохраняем результат
    output_path = Path("test_generated_output.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ HTML сгенерирован успешно!")
    print(f"📁 Сохранено в: {output_path.absolute()}")

    # Проверки
    print("\n" + "=" * 60)
    print("🔍 Проверка ключевых элементов:")

    checks = [
        ("ASSETS.images заполнен", '"char_0":' in html or '"tool_0":' in html),
        ("loadImage функция", "function loadImage" in html),
        ("Promise.all загрузка", "Promise.all" in html),
        ("drawImage для машины", "drawImage(carClean" in html or "ctx.drawImage" in html),
        ("drawImage для лейки", "drawImage(hoseImg" in html or "ctx.drawImage" in html),
        ("Store URLs реальные", "https://" in html and "STORE_CONFIG" in html),
        ("console.log загрузки", "images to load" in html),
        ("Fallback shapes", "fillStyle = '#CC0000'" in html or "fillStyle = '#4A90E2'" in html),
        ("Missing assets warning", "Missing assets, using fallbacks" in html),
    ]

    passed = 0
    failed = 0

    for check_name, result in checks:
        status = "✅" if result else "❌"
        print(f"{status} {check_name}")
        if result:
            passed += 1
        else:
            failed += 1

    print("\n" + "=" * 60)
    print(f"📊 Результат: {passed}/{len(checks)} проверок пройдено")

    if failed > 0:
        print(f"⚠️  Есть проблемы: {failed} проверок не прошли")
    else:
        print("🎉 Все проверки успешно пройдены!")

    # Показываем фрагмент ASSETS
    print("\n" + "=" * 60)
    print("📦 Фрагмент ASSETS объекта:")

    assets_start = html.find("const ASSETS = {")
    if assets_start != -1:
        assets_end = html.find("console.log(\"Assets initialized", assets_start)
        if assets_end == -1:
            assets_end = assets_start + 500

        assets_snippet = html[assets_start:assets_end]
        lines = assets_snippet.split("\n")[:15]  # Первые 15 строк

        for line in lines:
            if "data:image" in line and len(line) > 100:
                # Обрезаем длинные data URLs
                parts = line.split('"')
                if len(parts) >= 3:
                    key = parts[1] if len(parts) > 1 else "?"
                    data_part = parts[3] if len(parts) > 3 else parts[1]
                    if len(data_part) > 60:
                        truncated = data_part[:40] + "..." + data_part[-10:]
                        print(f'    "{key}": "{truncated}",')
                    else:
                        print(line)
            else:
                print(line)

    # Показываем Store URLs
    print("\n" + "=" * 60)
    print("🔗 Store URLs:")

    store_start = html.find("const STORE_CONFIG = {")
    if store_start != -1:
        store_end = html.find("};", store_start) + 2
        store_snippet = html[store_start:store_end]
        print(store_snippet)

    print("\n" + "=" * 60)
    print("🌐 Открываю HTML в браузере...")

    import subprocess
    subprocess.run(["open", str(output_path.absolute())])

    print("\n✅ Тест завершен!")
    print("👀 Проверьте браузер и консоль разработчика (F12)")
    print("   Ожидаемые логи:")
    print("   - Assets initialized: X images to load")
    print("   - Loaded: char_0 (WxH)")
    print("   - Game ready: X/Y images loaded")

except Exception as e:
    print(f"\n❌ ОШИБКА при генерации HTML:")
    print(f"   {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
