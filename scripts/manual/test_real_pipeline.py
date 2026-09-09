#!/usr/bin/env python3
"""
Real pipeline test — Orchestrator V2

Single entry point: run_orchestrator() handles everything.
Verifies: iterations, scores, version history, memory, output HTML.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # repo root on sys.path

import os
import asyncio
import base64
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Enable logging for all agents
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S',
)
# Reduce noise from HTTP libraries
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)
logging.getLogger('openai').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('anthropic').setLevel(logging.INFO)

# Verify API keys
required_keys = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY"]
missing_keys = [key for key in required_keys if not os.getenv(key)]

if missing_keys:
    print(f"Missing API keys: {', '.join(missing_keys)}")
    sys.exit(1)

print("All API keys found")
print("=" * 80)


async def test_orchestrator_v2():
    """Test Orchestrator V2 end-to-end with real data."""
    from playable_agents.orchestrator import run_orchestrator

    print("\nOrchestrator V2 — Full Pipeline Test")
    print("-" * 80)

    # Load TZ
    tz_path = Path("docs/misc/TZ_SNB_Car.md")
    spec_text = tz_path.read_text()
    print(f"Loaded TZ: {len(spec_text)} chars")

    # Load reference assets
    assets_dir = Path("docs/misc/Assets/PNG")
    asset_files = {
        "car_bright": "car_bright.png",
        "car_clean": "car_clean.png",
        "car_dirt": "car_dirt.png",
        "hand": "hand.png",
        "karcher_one": "karcher_one.png",
        "karcher_water": "karcher@1x.png",
    }

    reference_assets = {}
    for name, filename in asset_files.items():
        file_path = assets_dir / filename
        if file_path.exists():
            img_bytes = file_path.read_bytes()
            b64_data = base64.b64encode(img_bytes).decode()
            reference_assets[name] = f"data:image/png;base64,{b64_data}"
            print(f"  Loaded: {name} ({len(img_bytes)} bytes)")

    print(f"Reference assets: {len(reference_assets)}")
    print("-" * 80)

    # Run orchestrator V2
    print("\nRunning Orchestrator V2...")
    print("(This will take several minutes — generating, screenshotting, evaluating, patching)")
    print()

    result = await run_orchestrator(
        spec_text=spec_text,
        reference_assets=reference_assets,
        output_dir="output",
        memory_dir="memory",
        resume=True,
    )

    # === Results ===
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)

    success = result.get("success", False)
    print(f"Success: {success}")
    print(f"Iterations: {result.get('iterations', 0)}")
    print(f"Scores: {result.get('scores', {})}")

    # Version history
    history = result.get("version_history", [])
    print(f"\nVersion History ({len(history)} versions):")
    for v in history:
        score_str = f"score={v.get('overall')}" if v.get('overall') else "no score"
        print(f"  v{v['version']}: {v.get('size_kb', 0):.0f}KB, {score_str}")

    # Save final HTML
    html = result.get("html")
    if html:
        output_path = Path("output_real_pipeline.html")
        output_path.write_text(html)
        size_kb = len(html.encode('utf-8')) / 1024
        print(f"\nFinal HTML: {size_kb:.1f}KB → {output_path.absolute()}")
    else:
        print("\nNo HTML generated!")

    # Agent output
    agent_output = result.get("agent_output", "")
    if agent_output:
        print(f"\nAgent summary:\n{agent_output[:500]}")

    # === Verification ===
    print("\n" + "=" * 80)
    print("VERIFICATION")
    print("=" * 80)

    checks = []

    # Check 1: Orchestrator did >= 2 iterations
    iterations = result.get("iterations", 0)
    check1 = iterations >= 2
    checks.append(("Iterations >= 2", check1, f"iterations={iterations}"))

    # Check 2: Visual QA score
    overall_score = result.get("scores", {}).get("overall", 0)
    check2 = overall_score >= 7
    checks.append(("Visual QA score >= 7", check2, f"score={overall_score}"))

    # Check 3: Version history >= 2 versions
    check3 = len(history) >= 2
    checks.append(("Version history >= 2", check3, f"versions={len(history)}"))

    # Check 4: Memory file created
    memory_dir = Path("memory")
    memory_files = list(memory_dir.glob("*.md")) if memory_dir.exists() else []
    check4 = len(memory_files) > 0
    checks.append(("Memory file created", check4, f"files={len(memory_files)}"))

    # Check 5: Output HTML exists and is valid
    check5 = html is not None and len(html) > 1000
    checks.append(("Output HTML exists", check5, f"size={len(html) if html else 0}"))

    # Check 6: HTML has key features
    if html:
        has_canvas = "<canvas" in html
        has_touch = "touchstart" in html
        has_mraid = "mraid" in html
        has_raf = "requestAnimationFrame" in html
        check6 = has_canvas and has_touch and has_mraid and has_raf
        detail = f"canvas={has_canvas}, touch={has_touch}, mraid={has_mraid}, raf={has_raf}"
    else:
        check6 = False
        detail = "no HTML"
    checks.append(("HTML has key features", check6, detail))

    # Print results
    all_passed = True
    for name, passed, detail in checks:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}: {detail}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("ALL CHECKS PASSED!")
    elif success:
        print("Pipeline completed but some checks failed.")
    else:
        error = result.get("error", "Unknown error")
        print(f"Pipeline failed: {error}")

    print("=" * 80)
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(test_orchestrator_v2())
    sys.exit(0 if success else 1)
