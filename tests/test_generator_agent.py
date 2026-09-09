"""Tests for GeneratorAgent"""

import pytest
from unittest.mock import MagicMock, patch


def test_generator_agent_exists():
    """GeneratorAgent is properly defined"""
    from playable_agents.generator_agent import generator_agent
    assert generator_agent.name == "GeneratorAgent"


def test_generate_html_tool_exists():
    """generate_html tool is defined"""
    from playable_agents.generator_agent import generate_html
    assert generate_html.name == "generate_html"


def test_fix_issues_tool_exists():
    """fix_issues tool is defined"""
    from playable_agents.generator_agent import fix_issues
    assert fix_issues.name == "fix_issues"


def test_get_html_status_tool_exists():
    """get_html_status tool is defined"""
    from playable_agents.generator_agent import get_html_status
    assert get_html_status.name == "get_html_status"


def test_export_html_tool_exists():
    """export_html tool is defined"""
    from playable_agents.generator_agent import export_html
    assert export_html.name == "export_html"


def test_agent_has_correct_tools():
    """Agent has all required tools"""
    from playable_agents.generator_agent import generator_agent

    tool_names = [t.name for t in generator_agent.tools]
    assert "generate_html" in tool_names
    assert "fix_issues" in tool_names
    assert "get_html_status" in tool_names
    assert "export_html" in tool_names


def test_load_prompt():
    """_load_prompt loads car wash prompt"""
    from playable_agents.generator_agent import _load_prompt

    prompt = _load_prompt("generator_car_wash")
    assert len(prompt) > 100
    assert "Car Wash" in prompt or "canvas" in prompt.lower()


def test_get_genre_prompt():
    """_get_genre_prompt maps genres to prompts"""
    from playable_agents.generator_agent import _get_genre_prompt

    car_wash_prompt = _get_genre_prompt("car-wash")
    assert len(car_wash_prompt) > 0

    cleaning_prompt = _get_genre_prompt("cleaning")
    assert len(cleaning_prompt) > 0

    # Same prompt for similar genres
    assert car_wash_prompt == cleaning_prompt


def test_inject_assets():
    """_inject_assets replaces placeholders with data URIs"""
    from playable_agents.generator_agent import _inject_assets

    html = '''<script>
    const assets = {
        car: "{{asset:car_dirty}}",
        hose: "ASSET_HOSE"
    };
    </script>'''

    manifest = {
        "car_dirty": {"data": "data:image/png;base64,ABC123"},
        "hose": {"data": "data:image/png;base64,XYZ789"}
    }

    result = _inject_assets(html, manifest)

    assert "data:image/png;base64,ABC123" in result
    assert "data:image/png;base64,XYZ789" in result
    assert "{{asset:car_dirty}}" not in result
    assert "ASSET_HOSE" not in result


def test_inject_assets_with_string_data():
    """_inject_assets handles string data (not dict)"""
    from playable_agents.generator_agent import _inject_assets

    html = '<img src="{{asset:bg}}">'

    manifest = {
        "bg": "data:image/jpeg;base64,BACKGROUND"
    }

    result = _inject_assets(html, manifest)

    assert "data:image/jpeg;base64,BACKGROUND" in result


def test_generator_instructions_include_car_wash():
    """Generator instructions mention Car Wash best practices"""
    from playable_agents.generator_agent import generator_agent

    instructions = generator_agent.instructions.lower()
    assert "car wash" in instructions
    assert "mraid" in instructions
    assert "canvas" in instructions


def test_memory_store_html_versions():
    """Memory store can track HTML versions"""
    from playable_agents.memory_store import MemoryStore

    memory = MemoryStore()

    # Add versions
    v1 = memory.append_html_version("<html>v1</html>")
    v2 = memory.append_html_version("<html>v2</html>")

    assert v1 == 1
    assert v2 == 2

    # Get latest
    latest = memory.get_latest_html()
    assert latest == "<html>v2</html>"

    # Get all versions
    versions = memory.get("html_versions")
    assert len(versions) == 2
