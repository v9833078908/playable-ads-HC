"""Tests for TechnicalQAAgent"""

import pytest
from unittest.mock import MagicMock


def test_technical_qa_agent_exists():
    """TechnicalQAAgent is properly defined"""
    from playable_agents.technical_qa_agent import technical_qa_agent
    assert technical_qa_agent.name == "TechnicalQAAgent"


def test_check_size_tool_exists():
    """check_size tool is defined"""
    from playable_agents.technical_qa_agent import check_size
    assert check_size.name == "check_size"


def test_check_touch_events_tool_exists():
    """check_touch_events tool is defined"""
    from playable_agents.technical_qa_agent import check_touch_events
    assert check_touch_events.name == "check_touch_events"


def test_check_mraid_tool_exists():
    """check_mraid tool is defined"""
    from playable_agents.technical_qa_agent import check_mraid
    assert check_mraid.name == "check_mraid"


def test_check_viewport_tool_exists():
    """check_viewport tool is defined"""
    from playable_agents.technical_qa_agent import check_viewport
    assert check_viewport.name == "check_viewport"


def test_check_game_loop_tool_exists():
    """check_game_loop tool is defined"""
    from playable_agents.technical_qa_agent import check_game_loop
    assert check_game_loop.name == "check_game_loop"


def test_run_all_checks_tool_exists():
    """run_all_checks tool is defined"""
    from playable_agents.technical_qa_agent import run_all_checks
    assert run_all_checks.name == "run_all_checks"


def test_agent_has_correct_tools():
    """Agent has all required tools"""
    from playable_agents.technical_qa_agent import technical_qa_agent

    tool_names = [t.name for t in technical_qa_agent.tools]
    assert "check_size" in tool_names
    assert "check_touch_events" in tool_names
    assert "check_mraid" in tool_names
    assert "check_viewport" in tool_names
    assert "check_game_loop" in tool_names
    assert "run_all_checks" in tool_names


def test_technical_qa_prompt_exists():
    """Technical QA prompt file exists"""
    from pathlib import Path

    prompts_dir = Path(__file__).parent.parent / "playable_agents" / "prompts"
    prompt_file = prompts_dir / "technical_qa.md"

    assert prompt_file.exists(), f"Prompt file not found: {prompt_file}"


def test_max_size_constant():
    """MAX_SIZE_BYTES is correctly defined"""
    from playable_agents.technical_qa_agent import MAX_SIZE_BYTES

    assert MAX_SIZE_BYTES == 5 * 1024 * 1024  # 5MB


def test_agent_instructions_contain_requirements():
    """Agent instructions include technical requirements"""
    from playable_agents.technical_qa_agent import technical_qa_agent

    instructions = technical_qa_agent.instructions.lower()
    assert "mraid" in instructions
    assert "touch" in instructions
    assert "5mb" in instructions or "5 mb" in instructions
    assert "requestanimationframe" in instructions


def test_memory_store_with_valid_html():
    """Memory store can track HTML with technical requirements"""
    from playable_agents.memory_store import MemoryStore

    memory = MemoryStore()

    # Add valid HTML
    valid_html = '''<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<style>
body { touch-action: none; overflow: hidden; }
</style>
</head>
<body>
<canvas id="canvas"></canvas>
<script>
const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');

canvas.addEventListener('touchstart', (e) => { e.preventDefault(); });
canvas.addEventListener('touchmove', (e) => { e.preventDefault(); }, { passive: false });
canvas.addEventListener('touchend', (e) => { e.preventDefault(); });

function openStore() {
    if (window.mraid) {
        mraid.open('https://play.google.com/store/apps');
    }
}

function gameLoop() {
    requestAnimationFrame(gameLoop);
}
gameLoop();
</script>
</body>
</html>'''

    memory.append_html_version(valid_html)

    # Verify it's stored
    latest = memory.get_latest_html()
    assert "touchstart" in latest
    assert "mraid.open" in latest
    assert "requestAnimationFrame" in latest


def test_html_size_calculation():
    """Size calculation works correctly"""
    from playable_agents.memory_store import MemoryStore

    memory = MemoryStore()

    # Add HTML of known size
    html = "x" * 1024  # 1KB
    memory.append_html_version(html)

    latest = memory.get_latest_html()
    size = len(latest.encode('utf-8'))

    assert size == 1024
