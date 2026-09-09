"""Tests for VisualQAAgent"""

import pytest
from unittest.mock import MagicMock


def test_visual_qa_agent_exists():
    """VisualQAAgent is properly defined"""
    from playable_agents.visual_qa_agent import visual_qa_agent
    assert visual_qa_agent.name == "VisualQAAgent"


def test_validate_visual_tool_exists():
    """validate_visual tool is defined"""
    from playable_agents.visual_qa_agent import validate_visual
    assert validate_visual.name == "validate_visual"


def test_check_asset_presence_tool_exists():
    """check_asset_presence tool is defined"""
    from playable_agents.visual_qa_agent import check_asset_presence
    assert check_asset_presence.name == "check_asset_presence"


def test_get_visual_qa_history_tool_exists():
    """get_visual_qa_history tool is defined"""
    from playable_agents.visual_qa_agent import get_visual_qa_history
    assert get_visual_qa_history.name == "get_visual_qa_history"


def test_agent_has_correct_tools():
    """Agent has all required tools"""
    from playable_agents.visual_qa_agent import visual_qa_agent

    tool_names = [t.name for t in visual_qa_agent.tools]
    assert "validate_visual" in tool_names
    assert "check_asset_presence" in tool_names
    assert "get_visual_qa_history" in tool_names


def test_visual_qa_prompt_exists():
    """Visual QA prompt file exists"""
    from pathlib import Path

    prompts_dir = Path(__file__).parent.parent / "playable_agents" / "prompts"
    prompt_file = prompts_dir / "visual_qa.md"

    assert prompt_file.exists(), f"Prompt file not found: {prompt_file}"


def test_memory_store_qa_tracking():
    """Memory store correctly tracks QA results"""
    from playable_agents.memory_store import MemoryStore

    memory = MemoryStore()

    # Test asset tracking
    memory.set("asset_list", [
        {"name": "car", "role": "main_object"},
        {"name": "hose", "role": "tool"},
    ])

    # Asset manifest with base64 data
    car_data = "data:image/png;base64," + "A" * 100
    memory.set("asset_manifest", {
        "car": {"data": car_data}
    })

    # Verify storage
    assert len(memory.get("asset_list")) == 2
    assert "car" in memory.get("asset_manifest")


def test_memory_store_qa_history():
    """Memory store tracks QA history correctly"""
    from playable_agents.memory_store import MemoryStore

    memory = MemoryStore()
    memory.append_qa_result(
        iteration=1,
        visual_qa={"passed": False, "issues": [{"description": "Missing asset"}]},
        technical_qa={}
    )
    memory.append_qa_result(
        iteration=2,
        visual_qa={"passed": True, "issues": []},
        technical_qa={}
    )

    qa_history = memory.get("qa_history")
    assert len(qa_history) == 2
    assert qa_history[0]["visual_qa"]["passed"] is False
    assert qa_history[1]["visual_qa"]["passed"] is True


def test_html_version_tracking():
    """Memory store tracks HTML versions"""
    from playable_agents.memory_store import MemoryStore

    memory = MemoryStore()

    # Add HTML versions
    memory.append_html_version("<html>v1</html>")
    memory.append_html_version("<html>v2</html>")

    latest = memory.get_latest_html()
    assert latest == "<html>v2</html>"

    versions = memory.get("html_versions")
    assert len(versions) == 2

