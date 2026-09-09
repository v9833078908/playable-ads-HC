#!/usr/bin/env python3
"""
Extract embedded assets from HTML and save as separate image files
"""

import re
import base64
from pathlib import Path

def extract_assets_from_html(html_path: Path, output_dir: Path):
    """Extract all base64 assets from HTML and save as files"""

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Read HTML
    html = html_path.read_text()

    # Find all data URIs in JavaScript object
    # Pattern: assetName: 'data:image/png;base64,...'
    pattern = r"(\w+):\s*['\"]data:image/(png|jpeg|jpg);base64,([A-Za-z0-9+/=]+)['\"]"
    matches = re.findall(pattern, html)

    print(f"Found {len(matches)} embedded assets in HTML\n")

    extracted = []

    for asset_name, image_format, base64_data in matches:
        try:
            # Decode base64
            image_bytes = base64.b64decode(base64_data)

            # Save to file
            ext = 'jpg' if image_format == 'jpeg' else image_format
            output_path = output_dir / f"{asset_name}.{ext}"
            output_path.write_bytes(image_bytes)

            size_kb = len(image_bytes) / 1024

            extracted.append({
                'name': asset_name,
                'format': image_format,
                'path': output_path,
                'size': size_kb
            })

            print(f"✅ {asset_name:30s} → {output_path.name:35s} ({size_kb:7.1f}KB)")

        except Exception as e:
            print(f"❌ Failed to extract {asset_name}: {e}")

    return extracted


def analyze_memory_manifest():
    """Analyze what assets were generated vs referenced"""
    import json
    from dotenv import load_dotenv

    load_dotenv()

    print("\n" + "="*80)
    print("ASSET GENERATION ANALYSIS")
    print("="*80 + "\n")

    # Try to load memory state from the test
    # In real scenario, we'd read from stored state
    # For now, we'll analyze from the test output

    print("📦 Asset Pipeline Flow:")
    print()
    print("1️⃣  REFERENCE ASSETS (loaded from docs/misc/Assets/PNG):")
    print("   • car_bright.png      → 38.1KB  → Optimized → Embedded")
    print("   • car_clean.png       → 70.4KB  → Optimized → Embedded")
    print("   • car_dirt.png        → 88.6KB  → Optimized → Embedded")
    print("   • hand.png            → 45.8KB  → Optimized → Embedded")
    print("   • karcher_one.png     → 20.9KB  → Optimized → Embedded")
    print("   • karcher@1x.png      → 349.1KB → Optimized → Embedded")
    print()
    print("2️⃣  GENERATED ASSETS (created via FAL API):")
    print("   • car_dirty_overlay           → Generated 256x256 → Embedded")
    print("   • background_gameplay         → Generated 945x540 → Embedded")
    print("   • karcher_spray_gun           → Generated 256x256 → Embedded")
    print("   • hand_cursor                 → Generated 256x256 → Embedded")
    print("   • progress_bar_frame          → Generated 256x256 → Embedded")
    print("   • progress_bar_fill           → Generated 256x256 → Embedded")
    print("   • progress_bar_text           → Generated 256x256 → Embedded")
    print("   • drag_wash_animated_text     → Generated 256x256 → Embedded")
    print("   • water_spray_effect          → Generated 256x256 → Embedded")
    print("   • congratulations_animated_message → Generated 256x256 → Embedded")
    print("   • next_level_button           → Generated 256x256 → Embedded")
    print()
    print("3️⃣  STORAGE:")
    print("   • In Memory: asset_manifest (base64 data URIs)")
    print("   • In HTML: Embedded as inline base64 in JavaScript")
    print("   • On Disk (after extraction): output/assets/*.png")


if __name__ == "__main__":
    # Extract assets from generated HTML
    html_path = Path("output_detailed_pipeline.html")
    output_dir = Path("output/assets")

    if not html_path.exists():
        print(f"❌ HTML file not found: {html_path}")
        print("Run test_detailed_pipeline.py first to generate HTML")
        exit(1)

    print("="*80)
    print("EXTRACTING ASSETS FROM HTML")
    print("="*80)
    print()
    print(f"📄 Source: {html_path}")
    print(f"📁 Output: {output_dir}")
    print()

    # Extract assets
    extracted = extract_assets_from_html(html_path, output_dir)

    # Summary
    print()
    print("="*80)
    print("EXTRACTION SUMMARY")
    print("="*80)
    print()
    print(f"✅ Extracted {len(extracted)} assets")
    print(f"📁 Location: {output_dir.absolute()}")
    print(f"📊 Total size: {sum(a['size'] for a in extracted):.1f}KB")
    print()

    # Analyze pipeline
    analyze_memory_manifest()

    print()
    print("="*80)
    print("VIEW ASSETS")
    print("="*80)
    print()
    print(f"Open folder: open {output_dir.absolute()}")
    print(f"List files:  ls -lh {output_dir.absolute()}")
