#!/usr/bin/env python3
"""
Real integration test for multi-agent pipeline

Run from project root: python test_real_agents.py
"""

import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Verify API keys
required_keys = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "FAL_KEY"]
missing_keys = [key for key in required_keys if not os.getenv(key)]

if missing_keys:
    print(f"❌ Missing API keys: {', '.join(missing_keys)}")
    print("Please set them in .env file")
    sys.exit(1)

print("✅ All API keys found")
print("="*80)


async def test_scenario_agent():
    """Test Scenario Agent with real Gemini API"""
    from playable_agents import scenario_agent
    from playable_agents.memory_store import MemoryStore
    from agents import Runner

    print("\n🧪 Testing Scenario Agent with real Gemini API")
    print("-"*80)

    spec_text = """
# Car Wash Playable Ad

## Gameplay
Игрок использует водяной шланг для мытья грязной машины.

## Механика
- Drag-to-clean: игрок водит пальцем по экрану
- Reveal mask: грязь стирается, показывая чистую машину
- Progress bar: показывает процент чистоты (0% → 100%)

## Сцены
1. Gameplay: Мойка машины
2. Victory: Показ чистой машины + CTA кнопка

## UI Тексты
- Подсказка: "Проведи пальцем, чтобы помыть машину!"
- CTA: "ИГРАТЬ СЕЙЧАС"

## Store URLs
- Android: https://play.google.com/store/apps/details?id=com.example.carwash
- iOS: https://apps.apple.com/app/id123456789
"""

    memory = MemoryStore()
    memory.set("spec_text", spec_text)
    context = {"memory_store": memory}

    try:
        result = await Runner.run(
            scenario_agent,
            input="Analyze the specification. Call analyze_spec() and create_asset_list().",
            context=context
        )

        print(f"\n📋 Agent Output:\n{result.final_output}\n")

        scene_spec = memory.get("scene_spec")
        asset_list = memory.get("asset_list")

        if scene_spec:
            print(f"✅ Scene Spec created:")
            print(f"   Genre: {scene_spec.get('genre')}")
            print(f"   Mechanics: {scene_spec.get('mechanics')}")
            print(f"   Scenes: {len(scene_spec.get('scenes', []))}")

        if asset_list:
            print(f"✅ Asset List created: {len(asset_list)} assets")
            for asset in asset_list[:3]:
                print(f"   - {asset.get('name')} ({asset.get('role')})")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_generator_agent():
    """Test Generator Agent with real Claude API"""
    from playable_agents import generator_agent
    from playable_agents.memory_store import MemoryStore
    from agents import Runner

    print("\n🧪 Testing Generator Agent with real Claude Sonnet 4.5 API")
    print("-"*80)

    memory = MemoryStore()

    # Minimal required data
    memory.set("scene_spec", {
        "genre": "car-wash",
        "mechanics": ["drag-to-clean"],
        "scenes": [
            {"name": "gameplay", "description": "Wash the car"},
            {"name": "victory", "description": "Show CTA"}
        ],
        "ui_texts": {"hint": "Drag to wash!", "cta": "PLAY NOW"},
        "store_urls": {
            "android": "https://play.google.com/store/apps",
            "ios": "https://apps.apple.com/app"
        }
    })

    memory.set("asset_manifest", {
        "car": {
            "data": "data:image/png;base64,iVBORw0KGgo",
            "role": "main_object",
            "size": {"width": 512, "height": 512}
        },
        "hose": {
            "data": "data:image/png;base64,iVBORw0KGgo",
            "role": "tool",
            "size": {"width": 256, "height": 256}
        }
    })

    context = {"memory_store": memory}

    try:
        result = await Runner.run(
            generator_agent,
            input="Generate the HTML playable ad. Call generate_html().",
            context=context
        )

        print(f"\n📋 Agent Output:\n{result.final_output}\n")

        html = memory.get_latest_html()

        if html:
            print(f"✅ HTML generated:")
            print(f"   Size: {len(html)} bytes ({len(html)/1024:.1f}KB)")
            print(f"   Has canvas: {'<canvas' in html}")
            print(f"   Has game loop: {'requestAnimationFrame' in html}")
            print(f"   Has touch events: {'touchstart' in html}")

            # Save to file
            output_path = Path("test_output.html")
            output_path.write_text(html)
            print(f"   Saved to: {output_path.absolute()}")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_technical_qa():
    """Test Technical QA Agent"""
    from playable_agents import technical_qa_agent
    from playable_agents.memory_store import MemoryStore
    from agents import Runner

    print("\n🧪 Testing Technical QA Agent")
    print("-"*80)

    memory = MemoryStore()

    html = """<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<style>body { touch-action: none; overflow: hidden; }</style>
</head>
<body>
<canvas id="canvas"></canvas>
<script>
const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');

canvas.addEventListener('touchstart', (e) => { e.preventDefault(); });
canvas.addEventListener('touchmove', (e) => { e.preventDefault(); }, { passive: false });
canvas.addEventListener('touchend', (e) => {});

function gameLoop() { requestAnimationFrame(gameLoop); }
function openStore() {
    if (window.mraid) mraid.open('https://play.google.com/store/apps');
}
gameLoop();
</script>
</body>
</html>"""

    memory.append_html_version(html)
    memory.set("scene_spec", {
        "store_urls": {
            "android": "https://play.google.com/store/apps",
            "ios": "https://apps.apple.com/app"
        }
    })

    context = {"memory_store": memory}

    try:
        result = await Runner.run(
            technical_qa_agent,
            input="Run all technical checks. Call run_all_checks().",
            context=context
        )

        print(f"\n📋 Agent Output:\n{result.final_output}\n")

        qa_history = memory.get("qa_history")
        if qa_history:
            technical_qa = qa_history[-1].get("technical_qa", {})
            passed = technical_qa.get("passed")
            issues = technical_qa.get("issues", [])

            print(f"{'✅' if passed else '❌'} QA Result: {'PASSED' if passed else 'FAILED'}")
            print(f"   Issues: {len(issues)}")
            for issue in issues[:3]:
                print(f"   - [{issue.get('severity')}] {issue.get('description')}")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("\n🚀 Starting Real Integration Tests")
    print("⚠️  WARNING: This will make real API calls and consume credits!")
    print("="*80)

    results = {}

    # Test 1: Scenario Agent
    results['scenario'] = await test_scenario_agent()

    # Test 2: Generator Agent
    results['generator'] = await test_generator_agent()

    # Test 3: Technical QA
    results['technical_qa'] = await test_technical_qa()

    # Summary
    print("\n" + "="*80)
    print("📊 Test Summary:")
    print("-"*80)
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:20s}: {status}")

    print("="*80)

    if all(results.values()):
        print("✅ All tests PASSED!")
        return 0
    else:
        print("❌ Some tests FAILED")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
