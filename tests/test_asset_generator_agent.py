"""Tests for AssetGeneratorAgent"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock


def test_asset_generator_agent_exists():
    """AssetGeneratorAgent is properly defined"""
    from playable_agents.asset_generator_agent import asset_generator_agent
    assert asset_generator_agent.name == "AssetGeneratorAgent"


def test_generate_asset_tool_exists():
    """generate_asset tool is defined"""
    from playable_agents.asset_generator_agent import generate_asset
    assert generate_asset.name == "generate_asset"


def test_generate_all_assets_tool_exists():
    """generate_all_assets tool is defined"""
    from playable_agents.asset_generator_agent import generate_all_assets
    assert generate_all_assets.name == "generate_all_assets"


def test_get_asset_status_tool_exists():
    """get_asset_status tool is defined"""
    from playable_agents.asset_generator_agent import get_asset_status
    assert get_asset_status.name == "get_asset_status"


def test_validate_asset_tool_exists():
    """validate_asset tool is defined"""
    from playable_agents.asset_generator_agent import validate_asset
    assert validate_asset.name == "validate_asset"


def test_agent_has_correct_tools():
    """Agent has all required tools"""
    from playable_agents.asset_generator_agent import asset_generator_agent

    tool_names = [t.name for t in asset_generator_agent.tools]
    assert "generate_asset" in tool_names
    assert "generate_all_assets" in tool_names
    assert "get_asset_status" in tool_names
    assert "validate_asset" in tool_names


def test_role_config_exists():
    """Role configuration is defined correctly"""
    from playable_agents.asset_generator_agent import ROLE_CONFIG

    assert "main_object" in ROLE_CONFIG
    assert "tool" in ROLE_CONFIG
    assert "background" in ROLE_CONFIG
    assert "ui_element" in ROLE_CONFIG
    assert "effect" in ROLE_CONFIG

    # Check main_object config
    main_config = ROLE_CONFIG["main_object"]
    assert main_config["size"] == (512, 512)
    assert main_config["format"] == "png"
    assert main_config["aspect_ratio"] == "1:1"

    # Check background config
    bg_config = ROLE_CONFIG["background"]
    assert bg_config["size"] == (960, 540)
    assert bg_config["format"] == "jpeg"
    assert bg_config["aspect_ratio"] == "16:9"


def test_build_prompt():
    """_build_prompt generates correct prompts"""
    from playable_agents.asset_generator_agent import _build_prompt

    asset = {
        "name": "car_dirty",
        "description": "dirty red car with mud splatters",
        "role": "main_object"
    }
    style_desc = {
        "style": "cartoon",
        "shading": "flat",
        "colors": ["#FF0000", "#0000FF", "#00FF00"]
    }

    prompt = _build_prompt(asset, style_desc)

    assert "dirty red car" in prompt
    assert "cartoon style" in prompt
    assert "transparent background" in prompt
    assert "centered" in prompt


def test_build_prompt_without_style():
    """_build_prompt works without style description"""
    from playable_agents.asset_generator_agent import _build_prompt

    asset = {
        "name": "hose",
        "description": "water hose sprayer",
        "role": "tool"
    }

    prompt = _build_prompt(asset, {})

    assert "water hose" in prompt
    assert "cartoon style" in prompt  # Default fallback


def test_role_config_has_required_fields():
    """Each role config has all required fields"""
    from playable_agents.asset_generator_agent import ROLE_CONFIG

    required_fields = ["suffix", "size", "format", "aspect_ratio"]

    for role, config in ROLE_CONFIG.items():
        for field in required_fields:
            assert field in config, f"Role {role} missing field {field}"


def test_memory_store_integration():
    """Memory store can hold asset data correctly"""
    from playable_agents.memory_store import MemoryStore

    memory = MemoryStore()

    # Set up asset list
    memory.set("asset_list", [
        {"name": "car", "role": "main_object", "description": "dirty car"},
        {"name": "hose", "role": "tool", "description": "water hose"},
    ])

    # Set up asset manifest
    memory.set("asset_manifest", {
        "car": {
            "data": "data:image/png;base64,abc123",
            "role": "main_object",
            "size": {"width": 512, "height": 512}
        }
    })

    # Verify storage
    asset_list = memory.get("asset_list")
    assert len(asset_list) == 2
    assert asset_list[0]["name"] == "car"

    manifest = memory.get("asset_manifest")
    assert "car" in manifest
    assert manifest["car"]["size"]["width"] == 512


def test_build_prompt_for_each_role():
    """_build_prompt generates appropriate prompts for each role"""
    from playable_agents.asset_generator_agent import _build_prompt, ROLE_CONFIG

    style = {"style": "cartoon", "shading": "flat"}

    for role in ROLE_CONFIG.keys():
        asset = {"name": f"test_{role}", "description": "test item", "role": role}
        prompt = _build_prompt(asset, style)

        # Check that role suffix is included
        assert ROLE_CONFIG[role]["suffix"].split(",")[0] in prompt
        assert "cartoon style" in prompt
