"""Tests for MemoryStore - shared state between agents"""

import pytest
from playable_agents.memory_store import MemoryStore


def test_memory_store_initialization():
    """MemoryStore initializes with empty state"""
    store = MemoryStore()
    assert store.get("spec_text") is None
    assert store.get_all() == {}


def test_memory_store_set_and_get():
    """Can set and get values"""
    store = MemoryStore()
    store.set("spec_text", "Test specification")
    assert store.get("spec_text") == "Test specification"


def test_memory_store_nested_paths():
    """Can access nested paths like 'scene_spec.genre'"""
    store = MemoryStore()
    store.set("scene_spec", {"genre": "car-wash", "mechanics": ["drag-to-clean"]})
    assert store.get("scene_spec.genre") == "car-wash"
    assert store.get("scene_spec.mechanics") == ["drag-to-clean"]


def test_memory_store_asset_list():
    """Stores asset_list correctly"""
    store = MemoryStore()
    assets = [
        {"name": "car_clean", "description": "Clean car", "role": "main_object"},
        {"name": "hose", "description": "Water hose", "role": "tool"},
    ]
    store.set("asset_list", assets)
    assert len(store.get("asset_list")) == 2


def test_memory_store_qa_history():
    """Tracks QA iterations"""
    store = MemoryStore()
    store.append_qa_result(iteration=1, visual_qa={"passed": False}, technical_qa={"passed": True})
    history = store.get("qa_history")
    assert len(history) == 1
    assert history[0]["iteration"] == 1


def test_memory_store_html_versions():
    """Tracks HTML versions"""
    store = MemoryStore()
    v1 = store.append_html_version("<html>v1</html>")
    v2 = store.append_html_version("<html>v2</html>")
    assert v1 == 1
    assert v2 == 2
    assert store.get_latest_html() == "<html>v2</html>"


def test_memory_store_reset():
    """Reset clears all state"""
    store = MemoryStore()
    store.set("spec_text", "test")
    store.reset()
    assert store.get("spec_text") is None
