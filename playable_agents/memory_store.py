"""
Shared Memory Store for Multi-Agent Pipeline

Stores all state between agents:
- Input: spec_text, style_references
- Scenario Agent Output: style_description, asset_list, scene_spec
- Asset Generator Output: asset_manifest
- Generator Output: html_versions
- QA Feedback: qa_history
"""

from typing import Any, Optional
from datetime import datetime


class MemoryStore:
    """
    Thread-safe shared memory for agent pipeline.

    Usage:
        store = MemoryStore()
        store.set("scene_spec", {"genre": "car-wash"})
        genre = store.get("scene_spec.genre")  # "car-wash"
    """

    def __init__(self):
        self._data: dict[str, Any] = {}

    def get(self, path: str) -> Optional[Any]:
        """
        Get value by path. Supports dot notation for nested access.

        Examples:
            store.get("spec_text")  # top-level
            store.get("scene_spec.genre")  # nested
        """
        if "." not in path:
            return self._data.get(path)

        parts = path.split(".")
        current = self._data
        for part in parts:
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]
        return current

    def set(self, key: str, value: Any) -> None:
        """Set a top-level value"""
        self._data[key] = value

    def get_all(self) -> dict[str, Any]:
        """Get all stored data"""
        return self._data.copy()

    def append_qa_result(
        self,
        iteration: int,
        visual_qa: dict,
        technical_qa: dict
    ) -> None:
        """Append QA result to history"""
        if "qa_history" not in self._data:
            self._data["qa_history"] = []

        self._data["qa_history"].append({
            "iteration": iteration,
            "visual_qa": visual_qa,
            "technical_qa": technical_qa,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def append_html_version(self, html: str) -> int:
        """Append HTML version and return version number"""
        if "html_versions" not in self._data:
            self._data["html_versions"] = []

        version = len(self._data["html_versions"]) + 1
        self._data["html_versions"].append({
            "version": version,
            "html": html,
            "timestamp": datetime.utcnow().isoformat(),
        })
        return version

    def get_latest_html(self) -> Optional[str]:
        """Get most recent HTML version"""
        versions = self._data.get("html_versions", [])
        if not versions:
            return None
        return versions[-1]["html"]

    def reset(self) -> None:
        """Clear all stored data"""
        self._data = {}
