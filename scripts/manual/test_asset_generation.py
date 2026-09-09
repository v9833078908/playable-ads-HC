#!/usr/bin/env python3
"""Test script for asset generation with real FAL API (Phase 8 validation)"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env file
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key] = value
    print(f"✅ Loaded .env from {env_path}")

from playable_agents.asset_generator import generate_assets
from models import DraftBrief
from playable_agents.scene_card import SceneCard
import json


def test_real_api():
    """Test with real FAL API"""

    print("=" * 60)
    print("Asset Generation Real API Test")
    print("=" * 60)

    brief = DraftBrief(
        title="Car Wash Game",
        scenes=[],
        networks=["facebook"],
        languages=["en"],
        copy_texts={"title": "Clean the car!"}
    )

    scene_cards = [
        SceneCard(
            id="scene_1",
            title="Wash Car",
            mechanics=["drag_drop"],
            ui_elements={"progress": "0% Clean"},
            user_actions=["drag sponge over dirty_car"],
            technical={"swipe_mechanics": "canvas"}
        )
    ]

    print("\nGenerating assets with real FAL API...")
    print(f"Brief: {brief.title}")
    print(f"Scene cards: {len(scene_cards)}")

    try:
        manifest = generate_assets(brief, scene_cards, [])

        print("\n" + "=" * 60)
        print("✅ Asset Generation Complete!")
        print("=" * 60)
        print(f"\nGenerated {len(manifest['assets'])} assets")
        print(f"Total size: {manifest['total_size_bytes'] / 1024 / 1024:.2f}MB")
        print(f"Optimized: {manifest['metadata']['optimized']}")

        print("\nAsset Details:")
        for asset in manifest['assets']:
            size_kb = len(asset['data']) / 1024
            print(f"  - {asset['name']} ({asset['role']}): {size_kb:.1f}KB | z_index={asset['z_index']}")

        # Save manifest for inspection (without base64 data)
        manifest_copy = {
            **manifest,
            "assets": [
                {**a, "data": f"<base64 data {len(a['data'])} chars>"}
                for a in manifest["assets"]
            ]
        }

        output_path = Path(__file__).parent.parent / "tmp" / "asset_manifest_test.json"
        output_path.parent.mkdir(exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(manifest_copy, f, indent=2)

        print(f"\n✅ Manifest saved to {output_path}")

        # Validation checklist
        print("\n" + "=" * 60)
        print("Validation Checklist:")
        print("=" * 60)

        checks = [
            ("Assets generated successfully", len(manifest['assets']) > 0),
            ("Total size < 2MB", manifest['total_size_bytes'] < 2 * 1024 * 1024),
            ("All assets have base64 data URIs", all(a['data'].startswith('data:image/') for a in manifest['assets'])),
            ("z_index ordering correct", manifest['assets'] == sorted(manifest['assets'], key=lambda a: a['z_index'])),
            ("Critical assets marked", any(a['critical'] for a in manifest['assets'])),
            ("Metadata populated", all(k in manifest['metadata'] for k in ['generation_time', 'optimized', 'brief_style']))
        ]

        all_passed = True
        for check_name, result in checks:
            status = "✅" if result else "❌"
            print(f"{status} {check_name}")
            if not result:
                all_passed = False

        if all_passed:
            print("\n🎉 All validation checks passed!")
        else:
            print("\n⚠️  Some validation checks failed")

        return manifest

    except Exception as e:
        print(f"\n❌ Error during asset generation: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    test_real_api()
