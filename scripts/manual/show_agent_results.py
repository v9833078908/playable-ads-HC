#!/usr/bin/env python3
"""Show detailed results from each agent"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # repo root on sys.path


def _fixture_spec() -> Path:
    """Spec file for manual runs: $PLAYABLE_SPEC, else the local docs/misc fixture."""
    path = Path(os.getenv("PLAYABLE_SPEC", "docs/misc/TZ_SNB_Car.md"))
    if not path.is_file():
        raise SystemExit(
            f"Spec not found: {path}. Set PLAYABLE_SPEC to your own brief "
            "(docs/misc/ holds private fixtures and is not published)."
        )
    return path


def _fixture_assets() -> Path:
    """Reference-asset directory: $PLAYABLE_ASSETS, else the local docs/misc fixture."""
    path = Path(os.getenv("PLAYABLE_ASSETS", "docs/misc/Assets/PNG"))
    if not path.is_dir():
        raise SystemExit(
            f"Assets directory not found: {path}. Set PLAYABLE_ASSETS to your own "
            "reference images (docs/misc/ holds private fixtures and is not published)."
        )
    return path

import asyncio
import base64
import json
from dotenv import load_dotenv

# Load environment
load_dotenv()

from playable_agents.memory_store import MemoryStore
from playable_agents import scenario_agent, asset_generator_agent
from agents import Runner


async def show_agent_outputs():
    # Load TZ
    tz_path = _fixture_spec()
    spec_text = tz_path.read_text()

    # Load assets
    assets_dir = _fixture_assets()
    asset_files = {
        'car_bright': 'car_bright.png',
        'car_clean': 'car_clean.png',
        'car_dirt': 'car_dirt.png',
        'hand': 'hand.png',
        'karcher_one': 'karcher_one.png',
        'karcher_water': 'karcher@1x.png',
    }

    reference_assets = {}
    for name, filename in asset_files.items():
        file_path = assets_dir / filename
        if file_path.exists():
            img_bytes = file_path.read_bytes()
            b64_data = base64.b64encode(img_bytes).decode()
            reference_assets[name] = f'data:image/png;base64,{b64_data}'

    # Initialize memory
    memory = MemoryStore()
    memory.set('spec_text', spec_text)
    memory.set('reference_assets', reference_assets)
    context = {'memory_store': memory}

    # Run Scenario Agent
    print('='*80)
    print('SCENARIO AGENT OUTPUT')
    print('='*80)
    result = await Runner.run(
        scenario_agent,
        input='Analyze the specification. Call analyze_spec() and create_asset_list().',
        context=context
    )

    scene_spec = memory.get('scene_spec')
    asset_list = memory.get('asset_list')

    print('\n📋 SCENE SPEC:')
    print(json.dumps(scene_spec, indent=2, ensure_ascii=False))

    print('\n\n📋 ASSET LIST:')
    print(json.dumps(asset_list, indent=2, ensure_ascii=False))

    # Run Asset Generator
    print('\n\n')
    print('='*80)
    print('ASSET GENERATOR AGENT OUTPUT')
    print('='*80)
    result = await Runner.run(
        asset_generator_agent,
        input='Map reference assets and generate missing ones. Call use_reference_assets() then generate_missing_assets().',
        context=context
    )

    asset_manifest = memory.get('asset_manifest')
    print('\n📋 ASSET MANIFEST:')
    for asset_id, asset_data in asset_manifest.items():
        source = asset_data.get('source', 'unknown')
        data_uri_len = len(asset_data.get('data_uri', ''))
        print(f'  {asset_id}:')
        print(f'    source: {source}')
        print(f'    data_uri_length: {data_uri_len} chars')
        if 'metadata' in asset_data:
            print(f'    metadata: {asset_data["metadata"]}')


if __name__ == "__main__":
    asyncio.run(show_agent_outputs())
