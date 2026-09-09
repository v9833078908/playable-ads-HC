#!/usr/bin/env python3
"""End-to-end test: Full workflow from Brief to HTML with AI-generated assets"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key] = value
    print(f"✅ Loaded .env\n")

from playable_agents.asset_generator import generate_assets
from playable_agents.html_generator import generate_html
from models import DraftBrief, PlayableSpec, SceneSpec, MechanicConfig
from playable_agents.scene_card import SceneCard
import json


def test_full_workflow():
    """Test complete workflow: Brief → Scene Cards → Assets → Spec → HTML"""

    print("=" * 70)
    print("🚀 Full Workflow Test: Brief → Assets → HTML")
    print("=" * 70)

    # ===================================================================
    # Step 1: Create Brief
    # ===================================================================
    print("\n📋 Step 1: Creating Brief...")

    brief = DraftBrief(
        title="Car Wash Challenge",
        scenes=[],
        networks=["facebook", "unity"],
        languages=["en"],
        copy_texts={
            "title": "Car Wash Challenge",
            "tutorial": "Drag the sponge to clean!",
            "victory": "Perfect! Download now!"
        }
    )

    print(f"✅ Brief created: {brief.title}")

    # ===================================================================
    # Step 2: Create Scene Cards
    # ===================================================================
    print("\n🎬 Step 2: Creating Scene Cards...")

    scene_cards = [
        SceneCard(
            id="scene_tutorial",
            title="Tutorial",
            mechanics=["drag_drop"],
            ui_elements={
                "instruction": "Drag the sponge to clean the car!",
                "progress": "0% Clean"
            },
            user_actions=[
                "drag sponge over dirty_car",
                "clean dirt spots"
            ],
            technical={
                "duration": 3.0,
                "target_percentage": 30
            }
        ),
        SceneCard(
            id="scene_gameplay",
            title="Main Gameplay",
            mechanics=["drag_drop"],
            ui_elements={
                "progress": "Progress: 0%",
                "timer": "Time: 10s"
            },
            user_actions=[
                "drag sponge over dirty_car",
                "reach 100% clean"
            ],
            technical={
                "duration": 10.0,
                "target_percentage": 100
            }
        ),
        SceneCard(
            id="scene_victory",
            title="Victory",
            mechanics=["tap"],
            ui_elements={
                "message": "Perfect! Car is clean!",
                "cta": "Download Now"
            },
            user_actions=[
                "tap download button"
            ],
            technical={
                "duration": 2.0
            }
        )
    ]

    print(f"✅ Created {len(scene_cards)} scene cards")
    for card in scene_cards:
        print(f"   - {card.title}: {', '.join(card.mechanics)}")

    # ===================================================================
    # Step 3: Generate Assets with AI
    # ===================================================================
    print("\n🎨 Step 3: Generating Assets with AI...")
    print("   This will take 30-60 seconds...\n")

    try:
        asset_manifest = generate_assets(
            brief=brief,
            scene_cards=scene_cards,
            reference_images=[]
        )

        print(f"\n✅ Asset Generation Complete!")
        print(f"   Generated: {len(asset_manifest['assets'])} assets")
        print(f"   Total size: {asset_manifest['total_size_bytes']/1024:.1f}KB")
        print(f"   Optimized: {asset_manifest['metadata']['optimized']}")
        print(f"   Duration: {asset_manifest['metadata']['duration_seconds']:.1f}s")

        print("\n   Assets:")
        for asset in asset_manifest['assets']:
            size_kb = len(asset['data']) / 1024
            critical = "⚠️" if asset['critical'] else "  "
            print(f"   {critical} {asset['name']:20s} ({asset['role']:12s}) {size_kb:6.1f}KB  z:{asset['z_index']}")

    except Exception as e:
        print(f"\n❌ Asset generation failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # ===================================================================
    # Step 4: Build PlayableSpec
    # ===================================================================
    print("\n📦 Step 4: Building PlayableSpec...")

    # Build scenes
    scenes = []
    for card in scene_cards:
        mechanics = [
            MechanicConfig(type=m, config=card.technical.get(f"{m}_config", {}))
            for m in card.mechanics
        ]

        scenes.append(SceneSpec(
            id=card.id,
            type=card.mechanics[0] if card.mechanics else "generic",
            ui=card.ui_elements,
            mechanics=mechanics
        ))

    # Build assets dict from manifest
    assets_dict = {}
    images = {}
    background = None

    for asset in asset_manifest["assets"]:
        if asset["role"] == "background":
            background = asset["data"]
        else:
            images[asset["name"]] = asset["data"]

    assets_dict["images"] = images
    if background:
        assets_dict["background"] = background

    # Create spec
    spec = PlayableSpec(
        meta={
            "title": brief.title,
            "language": "EN",
            "network": "unity"
        },
        scenes=scenes,
        mechanics=list(set(m for c in scene_cards for m in c.mechanics)),
        assets=assets_dict,
        mraid={
            "android_url": "https://play.google.com/store/apps/details?id=com.example.carwash",
            "ios_url": "https://apps.apple.com/app/car-wash/id123456789"
        }
    )

    print(f"✅ PlayableSpec built")
    print(f"   Scenes: {len(spec.scenes)}")
    print(f"   Mechanics: {', '.join(spec.mechanics)}")
    print(f"   Assets: {len(assets_dict['images'])} images, background={background is not None}")

    # ===================================================================
    # Step 5: Generate HTML
    # ===================================================================
    print("\n🌐 Step 5: Generating HTML...")

    try:
        html = generate_html(spec)

        html_size_kb = len(html.encode('utf-8')) / 1024
        print(f"✅ HTML generated: {html_size_kb:.1f}KB")

        # Save HTML
        output_path = Path(__file__).parent.parent / "tmp" / "test_full_workflow.html"
        output_path.parent.mkdir(exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"   Saved to: {output_path}")

    except Exception as e:
        print(f"\n❌ HTML generation failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # ===================================================================
    # Step 6: Validate HTML
    # ===================================================================
    print("\n✅ Step 6: Validating HTML...")

    # Check for assets in HTML
    checks = {
        "ASSETS object exists": "const ASSETS = {" in html,
        "Images embedded": "images:" in html and len(images) > 0,
        "loadImage function": "function loadImage" in html or "loadImage(key, src)" in html,
        "drawImage calls": "drawImage(" in html or "ctx.drawImage" in html,
        "Store URLs": "play.google.com" in html or "apps.apple.com" in html,
        "MRAID wrapper": "mraid" in html.lower(),
        "Size < 5MB": html_size_kb < 5 * 1024
    }

    print("\n   Validation Results:")
    all_passed = True
    for check_name, result in checks.items():
        status = "✅" if result else "❌"
        print(f"   {status} {check_name}")
        if not result:
            all_passed = False

    # ===================================================================
    # Summary
    # ===================================================================
    print("\n" + "=" * 70)
    if all_passed:
        print("🎉 SUCCESS! Full workflow completed successfully!")
    else:
        print("⚠️  Workflow completed with warnings")
    print("=" * 70)

    print(f"""
Summary:
  Brief: {brief.title}
  Scene Cards: {len(scene_cards)}
  Assets Generated: {len(asset_manifest['assets'])}
  Assets Size: {asset_manifest['total_size_bytes']/1024:.1f}KB
  HTML Size: {html_size_kb:.1f}KB
  Total Size: {(asset_manifest['total_size_bytes'] + len(html.encode('utf-8')))/1024:.1f}KB

Output:
  HTML: {output_path}

Next Steps:
  1. Open the HTML file in browser
  2. Test interactivity
  3. Verify assets load correctly
  4. Check console for errors
    """)

    return True


if __name__ == "__main__":
    test_full_workflow()
