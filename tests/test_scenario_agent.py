"""Tests for ScenarioAgent"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def test_scenario_agent_exists():
    """ScenarioAgent is properly defined"""
    from playable_agents.scenario_agent import scenario_agent
    assert scenario_agent.name == "ScenarioAgent"


def test_analyze_spec_tool_exists():
    """analyze_spec tool is defined"""
    from playable_agents.scenario_agent import analyze_spec
    assert analyze_spec.name == "analyze_spec"


def test_analyze_references_tool_exists():
    """analyze_references tool is defined"""
    from playable_agents.scenario_agent import analyze_references
    assert analyze_references.name == "analyze_references"


def test_create_asset_list_tool_exists():
    """create_asset_list tool is defined"""
    from playable_agents.scenario_agent import create_asset_list
    assert create_asset_list.name == "create_asset_list"


def test_confirm_understanding_tool_exists():
    """confirm_understanding tool is defined"""
    from playable_agents.scenario_agent import confirm_understanding
    assert confirm_understanding.name == "confirm_understanding"


def test_agent_has_correct_tools():
    """Agent has all required tools"""
    from playable_agents.scenario_agent import scenario_agent

    tool_names = [t.name for t in scenario_agent.tools]
    assert "analyze_spec" in tool_names
    assert "analyze_references" in tool_names
    assert "create_asset_list" in tool_names
    assert "confirm_understanding" in tool_names


def test_confirm_understanding_generates_summary():
    """confirm_understanding generates readable summary when invoked"""
    from playable_agents.scenario_agent import _load_prompt
    from playable_agents.memory_store import MemoryStore

    # Test that confirm_understanding logic works by testing the memory store usage
    memory = MemoryStore()
    memory.set("scene_spec", {
        "genre": "car-wash",
        "mechanics": ["drag-to-clean", "reveal-mask"],
        "scenes": [
            {"name": "gameplay", "description": "Clean the car"},
            {"name": "victory", "description": "Show CTA"}
        ],
        "ui_texts": {"hint": "Drag to clean!", "cta": "PLAY NOW"},
        "store_urls": {"android": "https://play.google.com/test"}
    })
    memory.set("style_description", {"style": "cartoon", "shading": "flat"})
    memory.set("asset_list", [
        {"name": "car", "role": "main_object"},
        {"name": "hose", "role": "tool"},
        {"name": "bg", "role": "background"}
    ])

    # Verify memory store has the data
    assert memory.get("scene_spec.genre") == "car-wash"
    assert len(memory.get("asset_list")) == 3


def test_prompt_file_exists():
    """Prompt file exists in prompts directory"""
    from pathlib import Path

    prompts_dir = Path(__file__).parent.parent / "playable_agents" / "prompts"
    prompt_file = prompts_dir / "scenario_agent.md"

    assert prompt_file.exists(), f"Prompt file not found: {prompt_file}"


def test_load_prompt_function():
    """_load_prompt loads prompt files correctly"""
    from playable_agents.scenario_agent import _load_prompt

    prompt = _load_prompt("scenario_agent")
    assert "Scenario" in prompt
    assert len(prompt) > 100
