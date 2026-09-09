#!/usr/bin/env python3
"""
Detailed pipeline test showing full output of each agent
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # repo root on sys.path

import os
import asyncio
import base64
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Verify API keys
required_keys = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY"]
missing_keys = [key for key in required_keys if not os.getenv(key)]

if missing_keys:
    print(f"❌ Missing API keys: {', '.join(missing_keys)}")
    sys.exit(1)

print("✅ All API keys found")
print("="*80)


def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def print_json(data, indent=2):
    """Pretty print JSON data"""
    print(json.dumps(data, indent=indent, ensure_ascii=False))


async def test_detailed_pipeline():
    """Test full pipeline with detailed output"""
    from playable_agents import scenario_agent, asset_generator_agent, generator_agent, technical_qa_agent
    from playable_agents.memory_store import MemoryStore
    from agents import Runner

    print_section("PIPELINE START: Loading Input Data")

    # Load TZ
    tz_path = Path("docs/misc/TZ_SNB_Car.md")
    spec_text = tz_path.read_text()
    print(f"📄 TZ File: {tz_path}")
    print(f"   Size: {len(spec_text)} chars")
    print(f"\n📋 TZ Content:\n{'-'*80}")
    print(spec_text)
    print(f"{'-'*80}")

    # Load assets as base64 and store as reference_assets
    assets_dir = Path("docs/misc/Assets/PNG")
    asset_files = {
        "car_bright": "car_bright.png",
        "car_clean": "car_clean.png",
        "car_dirt": "car_dirt.png",
        "hand": "hand.png",
        "karcher_one": "karcher_one.png",
        "karcher_water": "karcher@1x.png",
    }

    print(f"\n📦 Loading Reference Assets from: {assets_dir}")
    reference_assets = {}
    for name, filename in asset_files.items():
        file_path = assets_dir / filename
        if file_path.exists():
            img_bytes = file_path.read_bytes()
            b64_data = base64.b64encode(img_bytes).decode()
            reference_assets[name] = f"data:image/png;base64,{b64_data}"
            print(f"   ✅ {name:20s} → {filename:25s} ({len(img_bytes):7,d} bytes)")

    print(f"\n✅ Loaded {len(reference_assets)} reference assets")

    # Initialize memory
    memory = MemoryStore()
    memory.set("spec_text", spec_text)
    memory.set("reference_assets", reference_assets)
    context = {"memory_store": memory}

    # ========================================================================
    # PHASE 1: SCENARIO AGENT
    # ========================================================================
    print_section("PHASE 1/4: SCENARIO AGENT")
    print("Task: Analyze TZ and create scene_spec + asset_list\n")

    try:
        result = await Runner.run(
            scenario_agent,
            input="Analyze the specification. Call analyze_spec() and create_asset_list().",
            context=context
        )

        print(f"🤖 Agent Output:\n{'-'*80}")
        print(result.final_output)
        print(f"{'-'*80}\n")

        # Show scene_spec
        scene_spec = memory.get("scene_spec")
        if scene_spec:
            print("📊 SCENE_SPEC Created:")
            print_json(scene_spec)
        else:
            print("⚠️  No scene_spec created")

        # Show asset_list
        print("\n")
        asset_list = memory.get("asset_list")
        if asset_list:
            print(f"📋 ASSET_LIST Created ({len(asset_list)} assets):")
            for i, asset in enumerate(asset_list, 1):
                print(f"\n  [{i:2d}] {asset.get('name', 'unnamed')}")
                print(f"       Role: {asset.get('role', 'unknown')}")
                print(f"       Desc: {asset.get('description', 'no description')}")
        else:
            print("⚠️  No asset_list created")

        print(f"\n✅ Scenario Agent completed successfully")

    except Exception as e:
        print(f"❌ Scenario Agent failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # ========================================================================
    # PHASE 2: ASSET GENERATOR AGENT
    # ========================================================================
    print_section("PHASE 2/4: ASSET GENERATOR AGENT")
    print("Task: Map reference assets and generate missing ones\n")

    try:
        result = await Runner.run(
            asset_generator_agent,
            input="Map reference assets and generate missing ones. Call use_reference_assets() then generate_missing_assets().",
            context=context
        )

        print(f"🤖 Agent Output:\n{'-'*80}")
        print(result.final_output)
        print(f"{'-'*80}\n")

        # Show asset_manifest
        asset_manifest = memory.get("asset_manifest")
        if asset_manifest:
            print(f"📦 ASSET_MANIFEST Created ({len(asset_manifest)} assets):")

            reference_assets_mapped = []
            generated_assets_mapped = []

            for name, data in asset_manifest.items():
                source = data.get("source", "unknown")
                size = data.get("size", {})
                role = data.get("role", "unknown")
                data_size = len(data.get("data", ""))

                asset_info = {
                    "name": name,
                    "source": source,
                    "role": role,
                    "size": f"{size.get('width', '?')}x{size.get('height', '?')}",
                    "data_size": f"{data_size / 1024:.1f}KB"
                }

                if source == "reference":
                    reference_assets_mapped.append(asset_info)
                else:
                    generated_assets_mapped.append(asset_info)

            print(f"\n  📎 Reference Assets ({len(reference_assets_mapped)}):")
            for asset in reference_assets_mapped:
                print(f"     • {asset['name']:25s} | {asset['role']:15s} | {asset['size']:10s} | {asset['data_size']}")

            print(f"\n  🎨 Generated Assets ({len(generated_assets_mapped)}):")
            for asset in generated_assets_mapped:
                print(f"     • {asset['name']:25s} | {asset['role']:15s} | {asset['size']:10s} | {asset['data_size']}")

            total_size = sum(len(a.get("data", "")) for a in asset_manifest.values())
            print(f"\n  📊 Total manifest size: {total_size / 1024:.1f}KB")
        else:
            print("⚠️  No asset_manifest created")

        print(f"\n✅ Asset Generator Agent completed successfully")

    except Exception as e:
        print(f"❌ Asset Generator Agent failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # ========================================================================
    # PHASE 3: GENERATOR AGENT
    # ========================================================================
    print_section("PHASE 3/4: GENERATOR AGENT")
    print("Task: Generate HTML playable ad\n")

    try:
        result = await Runner.run(
            generator_agent,
            input="Generate the HTML playable ad using the real assets from asset_manifest. Call generate_html().",
            context=context
        )

        print(f"🤖 Agent Output:\n{'-'*80}")
        print(result.final_output)
        print(f"{'-'*80}\n")

        html = memory.get_latest_html()
        if html:
            print(f"📄 HTML Generated:")
            print(f"   Size: {len(html):,} bytes ({len(html)/1024:.1f}KB)")

            # Analyze HTML structure
            print(f"\n   📊 HTML Analysis:")
            print(f"      • Has <canvas>: {'✅' if '<canvas' in html else '❌'}")
            print(f"      • Has touch events: {'✅' if 'touchstart' in html or 'touchmove' in html else '❌'}")
            print(f"      • Has MRAID: {'✅' if 'mraid' in html.lower() else '❌'}")
            print(f"      • Has requestAnimationFrame: {'✅' if 'requestAnimationFrame' in html else '❌'}")
            print(f"      • Embedded assets: {html.count('data:image')}")

            # Save to file
            output_path = Path("output_detailed_pipeline.html")
            output_path.write_text(html)
            print(f"\n   💾 Saved to: {output_path.absolute()}")
        else:
            print("❌ No HTML generated")
            return False

        print(f"\n✅ Generator Agent completed successfully")

    except Exception as e:
        print(f"❌ Generator Agent failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # ========================================================================
    # PHASE 4: TECHNICAL QA AGENT
    # ========================================================================
    print_section("PHASE 4/4: TECHNICAL QA AGENT")
    print("Task: Run technical checks on HTML\n")

    try:
        result = await Runner.run(
            technical_qa_agent,
            input="Run all technical checks. Call run_all_checks().",
            context=context
        )

        print(f"🤖 Agent Output:\n{'-'*80}")
        print(result.final_output)
        print(f"{'-'*80}\n")

        qa_history = memory.get("qa_history")
        if qa_history:
            latest_qa = qa_history[-1]
            technical_qa = latest_qa.get("technical_qa", {})
            passed = technical_qa.get("passed")
            issues = technical_qa.get("issues", [])

            print(f"📊 QA Results:")
            print(f"   Status: {'✅ PASSED' if passed else '❌ FAILED'}")
            print(f"   Issues: {len(issues)}")

            if issues:
                print(f"\n   Issues found:")
                for i, issue in enumerate(issues, 1):
                    severity = issue.get('severity', 'unknown')
                    description = issue.get('description', 'no description')
                    print(f"      [{i}] [{severity}] {description}")
        else:
            print("⚠️  No QA results available")

        print(f"\n✅ Technical QA Agent completed successfully")

    except Exception as e:
        print(f"❌ Technical QA Agent failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # ========================================================================
    # FINAL SUMMARY
    # ========================================================================
    print_section("PIPELINE SUMMARY")

    scene_spec = memory.get("scene_spec")
    asset_list = memory.get("asset_list")
    asset_manifest = memory.get("asset_manifest")
    html_versions = memory.get("html_versions")
    qa_history = memory.get("qa_history")

    print(f"✅ Scenario Agent:")
    print(f"   • Scene spec: {'✅' if scene_spec else '❌'}")
    print(f"   • Asset list: {len(asset_list)} assets" if asset_list else "   • Asset list: ❌")

    print(f"\n✅ Asset Generator Agent:")
    if asset_manifest:
        ref_count = sum(1 for a in asset_manifest.values() if a.get("source") == "reference")
        gen_count = sum(1 for a in asset_manifest.values() if a.get("source") == "generated")
        print(f"   • Total assets: {len(asset_manifest)}")
        print(f"   • Reference: {ref_count}")
        print(f"   • Generated: {gen_count}")
    else:
        print(f"   • Asset manifest: ❌")

    print(f"\n✅ Generator Agent:")
    if html_versions:
        latest_html = html_versions[-1]['html']
        print(f"   • HTML generated: {len(latest_html):,} bytes ({len(latest_html)/1024:.1f}KB)")
        print(f"   • Versions: {len(html_versions)}")
    else:
        print(f"   • HTML: ❌")

    print(f"\n✅ Technical QA Agent:")
    if qa_history:
        latest_qa = qa_history[-1]
        technical_qa = latest_qa.get("technical_qa", {})
        passed = technical_qa.get("passed")
        issues = technical_qa.get("issues", [])
        print(f"   • Status: {'PASSED' if passed else 'FAILED'}")
        print(f"   • Issues: {len(issues)}")
    else:
        print(f"   • QA: ❌")

    print("\n" + "="*80)
    print("✅ E2E PIPELINE COMPLETED SUCCESSFULLY!")
    print("="*80)
    return True


if __name__ == "__main__":
    success = asyncio.run(test_detailed_pipeline())
    sys.exit(0 if success else 1)
