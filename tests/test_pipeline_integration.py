"""Integration tests for the multi-agent pipeline"""

import os

import pytest

# Set mock API keys for testing (before any imports)
os.environ.setdefault("OPENAI_API_KEY", "test-key-for-testing")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-for-testing")
os.environ.setdefault("GEMINI_API_KEY", "test-key-for-testing")


class TestPipelineIntegration:
    """Integration tests for the full pipeline"""

    def test_memory_store_flow(self):
        """Test data flow through memory store"""
        from playable_agents.memory_store import MemoryStore

        store = MemoryStore()

        # Simulate Scenario Agent
        store.set("spec_text", "Car wash playable ad specification")
        store.set("scene_spec", {
            "genre": "car-wash",
            "mechanics": ["drag-to-clean", "reveal-mask"],
            "scenes": [{"name": "gameplay"}, {"name": "victory"}],
            "ui_texts": {"hint": "Drag to clean!", "cta": "PLAY NOW"},
            "store_urls": {
                "android": "https://play.google.com/store/apps",
                "ios": "https://apps.apple.com/app"
            }
        })
        store.set("asset_list", [
            {"name": "car_dirty", "role": "main_object", "description": "dirty car"},
            {"name": "car_clean", "role": "main_object", "description": "clean car"},
            {"name": "hose", "role": "tool", "description": "water hose"},
            {"name": "background", "role": "background", "description": "car wash bg"}
        ])
        store.set("style_description", {"style": "cartoon", "shading": "flat"})

        # Simulate Asset Generator
        store.set("asset_manifest", {
            "car_dirty": {"data": "data:image/png;base64,CAR_DIRTY", "role": "main_object"},
            "car_clean": {"data": "data:image/png;base64,CAR_CLEAN", "role": "main_object"},
            "hose": {"data": "data:image/png;base64,HOSE", "role": "tool"},
            "background": {"data": "data:image/jpeg;base64,BG", "role": "background"}
        })

        # Simulate Generator
        html = """<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<style>body { touch-action: none; }</style>
</head>
<body>
<canvas id="canvas"></canvas>
<script>
canvas.addEventListener('touchstart', handleStart);
canvas.addEventListener('touchmove', handleMove, { passive: false });
canvas.addEventListener('touchend', handleEnd);
function gameLoop() { requestAnimationFrame(gameLoop); }
if (window.mraid) { mraid.open('https://play.google.com/store/apps'); }
</script>
</body>
</html>"""
        version = store.append_html_version(html)

        # Simulate QA
        store.append_qa_result(
            iteration=1,
            visual_qa={"passed": True, "issues": []},
            technical_qa={"passed": True, "issues": [], "metrics": {"file_size_kb": 2.5}}
        )

        # Verify complete flow
        assert store.get("scene_spec.genre") == "car-wash"
        assert len(store.get("asset_list")) == 4
        assert len(store.get("asset_manifest")) == 4
        assert version == 1
        assert store.get_latest_html() == html
        assert len(store.get("qa_history")) == 1
        assert store.get("qa_history")[0]["visual_qa"]["passed"] is True

    def test_agent_exports(self):
        """Test all agents are properly exported"""
        from playable_agents import (
            MemoryStore,
            scenario_agent,
            asset_generator_agent,
            generator_agent,
            visual_qa_agent,
            technical_qa_agent,
        )

        assert scenario_agent.name == "ScenarioAgent"
        assert asset_generator_agent.name == "AssetGeneratorAgent"
        assert generator_agent.name == "GeneratorAgent"
        assert visual_qa_agent.name == "VisualQAAgent"
        assert technical_qa_agent.name == "TechnicalQAAgent"

    def test_agent_tools_consistency(self):
        """Test agents have consistent tool patterns"""
        from playable_agents import (
            scenario_agent,
            asset_generator_agent,
            generator_agent,
            visual_qa_agent,
            technical_qa_agent,
        )

        # All agents should have tools
        assert len(scenario_agent.tools) >= 3
        assert len(asset_generator_agent.tools) >= 3
        assert len(generator_agent.tools) >= 3
        assert len(visual_qa_agent.tools) >= 2
        assert len(technical_qa_agent.tools) >= 5

    def test_prompt_files_exist(self):
        """Test all prompt files exist"""
        from pathlib import Path

        prompts_dir = Path(__file__).parent.parent / "playable_agents" / "prompts"

        assert (prompts_dir / "scenario_agent.md").exists()
        assert (prompts_dir / "generator_car_wash.md").exists()
        assert (prompts_dir / "visual_qa.md").exists()
        assert (prompts_dir / "technical_qa.md").exists()

    def test_qa_iteration_tracking(self):
        """Test QA iteration tracking in memory store"""
        from playable_agents.memory_store import MemoryStore

        store = MemoryStore()

        # Simulate multiple QA iterations
        for i in range(3):
            passed = i == 2  # Pass on 3rd iteration
            store.append_qa_result(
                iteration=i + 1,
                visual_qa={"passed": passed, "issues": [] if passed else [{"description": "issue"}]},
                technical_qa={"passed": passed, "issues": []}
            )

        history = store.get("qa_history")
        assert len(history) == 3
        assert history[0]["iteration"] == 1
        assert history[2]["visual_qa"]["passed"] is True

    def test_html_version_tracking(self):
        """Test HTML version tracking"""
        from playable_agents.memory_store import MemoryStore

        store = MemoryStore()

        # Add multiple versions
        v1 = store.append_html_version("<html>v1</html>")
        v2 = store.append_html_version("<html>v2</html>")
        v3 = store.append_html_version("<html>v3</html>")

        assert v1 == 1
        assert v2 == 2
        assert v3 == 3
        assert store.get_latest_html() == "<html>v3</html>"

        versions = store.get("html_versions")
        assert len(versions) == 3
        assert all("timestamp" in v for v in versions)


class TestTechnicalChecks:
    """Test technical QA check functions"""

    def test_check_size_within_limit(self):
        """Test size check passes for small HTML"""
        from playable_agents.memory_store import MemoryStore

        store = MemoryStore()
        store.append_html_version("<html>small</html>")  # ~16 bytes

        # Size should be well under 5MB
        html = store.get_latest_html()
        size = len(html.encode('utf-8'))
        assert size < 5 * 1024 * 1024

    def test_check_size_over_limit(self):
        """Test size check fails for large HTML"""
        from playable_agents.memory_store import MemoryStore
        from playable_agents.technical_qa_agent import MAX_SIZE_BYTES

        store = MemoryStore()

        # Create HTML larger than 5MB
        large_html = "x" * (MAX_SIZE_BYTES + 1000)
        store.append_html_version(large_html)

        html = store.get_latest_html()
        size = len(html.encode('utf-8'))
        assert size > MAX_SIZE_BYTES

    def test_valid_html_structure(self):
        """Test HTML with all required elements"""
        html = """<!DOCTYPE html>
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
canvas.addEventListener('touchend', (e) => {});

canvas.addEventListener('mousedown', handleStart);
canvas.addEventListener('mousemove', handleMove);
canvas.addEventListener('mouseup', handleEnd);

function gameLoop() {
    requestAnimationFrame(gameLoop);
}

if (window.mraid) {
    mraid.open('https://play.google.com/store/apps');
}

gameLoop();
</script>
</body>
</html>"""

        # Check all required elements
        assert "touchstart" in html
        assert "touchmove" in html
        assert "touchend" in html
        assert "mousedown" in html
        assert "mraid" in html
        assert "mraid.open" in html
        assert "requestAnimationFrame" in html
        assert "user-scalable=no" in html
        assert "touch-action: none" in html
        assert "<canvas" in html
        assert "getContext" in html


