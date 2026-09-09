"""
HTML File Manager — HTML-in-file operations for Orchestrator V2

Manages HTML on disk: save/read/replace sections/validate/version history/rollback.
HTML never enters LLM context directly — only read_section excerpts.
"""

import logging
import os
import re
import shutil
from pathlib import Path
from typing import Optional

logger = logging.getLogger('HTMLFileManager')


class HTMLFileManager:
    """Manages HTML file versioning, section editing, and rollback."""

    MAX_VERSIONS = 10  # Hard limit to prevent infinite loops

    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.versions: list[dict] = []  # [{version, path, scores}]
        self._current_path: Optional[Path] = None

    @property
    def current_path(self) -> Optional[Path]:
        """Path to current (latest) HTML file."""
        return self._current_path

    @property
    def version_count(self) -> int:
        return len(self.versions)

    def save_html(self, html: str, scores: Optional[dict] = None) -> dict:
        """
        Save HTML as new version. Returns version info dict.

        Args:
            html: Complete HTML string
            scores: Optional scores dict {overall: float, ...}

        Returns:
            {"version": int, "path": str, "size_kb": float}
        """
        if self.version_count >= self.MAX_VERSIONS:
            logger.warning(f"Max versions ({self.MAX_VERSIONS}) reached, returning best version")
            return self.get_best_version()

        version = self.version_count + 1
        filename = f"output_v{version}.html"
        path = self.output_dir / filename

        path.write_text(html, encoding='utf-8')
        self._current_path = path

        version_info = {
            "version": version,
            "path": str(path),
            "scores": scores or {},
            "size_kb": len(html.encode('utf-8')) / 1024,
        }
        self.versions.append(version_info)

        logger.info(f"Saved HTML v{version}: {version_info['size_kb']:.1f}KB")
        return version_info

    def read_current(self) -> Optional[str]:
        """Read the current (latest) HTML file."""
        if not self._current_path or not self._current_path.exists():
            return None
        return self._current_path.read_text(encoding='utf-8')

    def read_section(self, start_line: int, end_line: int) -> Optional[str]:
        """
        Read a section of current HTML by line numbers (1-based, inclusive).

        Returns string with line numbers prefixed for LLM context.
        """
        html = self.read_current()
        if not html:
            return None

        lines = html.split('\n')
        start = max(0, start_line - 1)
        end = min(len(lines), end_line)

        result_lines = []
        for i in range(start, end):
            result_lines.append(f"{i + 1:4d} | {lines[i]}")

        return '\n'.join(result_lines)

    def replace_section(
        self,
        start_line: int,
        end_line: int,
        new_code: str,
        scores: Optional[dict] = None
    ) -> dict:
        """
        Replace lines start_line..end_line (1-based, inclusive) with new_code.
        Saves as new version. Returns version info.

        Args:
            start_line: First line to replace (1-based)
            end_line: Last line to replace (1-based, inclusive)
            new_code: Replacement code
            scores: Optional scores for new version

        Returns:
            Version info dict or error dict
        """
        html = self.read_current()
        if not html:
            return {"error": "No current HTML to edit"}

        lines = html.split('\n')
        start = max(0, start_line - 1)
        end = min(len(lines), end_line)

        new_lines = new_code.split('\n')
        lines[start:end] = new_lines

        new_html = '\n'.join(lines)

        return self.save_html(new_html, scores)

    def find_section_by_marker(self, marker: str) -> Optional[tuple[int, int]]:
        """
        Find section boundaries by searching for a comment marker.

        Searches for lines containing the marker string.
        Returns (start_line, end_line) 1-based or None.
        """
        html = self.read_current()
        if not html:
            return None

        lines = html.split('\n')
        matches = []
        for i, line in enumerate(lines):
            if marker.lower() in line.lower():
                matches.append(i + 1)  # 1-based

        if not matches:
            return None

        # Return first match with some context (50 lines)
        start = matches[0]
        end = min(start + 50, len(lines))
        return (start, end)

    def search_in_html(self, query: str) -> list[dict]:
        """
        Search for a string/pattern in current HTML.
        Returns list of {line: int, content: str} matches.
        """
        html = self.read_current()
        if not html:
            return []

        lines = html.split('\n')
        results = []
        for i, line in enumerate(lines):
            if query.lower() in line.lower():
                results.append({
                    "line": i + 1,
                    "content": line.strip()[:120],
                })

        return results

    def update_scores(self, version: int, scores: dict) -> None:
        """Update scores for a specific version."""
        for v in self.versions:
            if v["version"] == version:
                v["scores"] = scores
                return

    def get_best_version(self) -> Optional[dict]:
        """Get version with highest overall score."""
        if not self.versions:
            return None

        scored = [v for v in self.versions if v.get("scores", {}).get("overall")]
        if not scored:
            return self.versions[-1]  # Return latest if no scores

        return max(scored, key=lambda v: v["scores"]["overall"])

    def rollback(self, version: Optional[int] = None) -> dict:
        """
        Rollback to a specific version (or best version if not specified).
        Makes a copy as new version to preserve history.

        Returns new version info.
        """
        if version:
            target = None
            for v in self.versions:
                if v["version"] == version:
                    target = v
                    break
            if not target:
                return {"error": f"Version {version} not found"}
        else:
            target = self.get_best_version()
            if not target:
                return {"error": "No versions to rollback to"}

        # Read the target version's HTML
        target_path = Path(target["path"])
        if not target_path.exists():
            return {"error": f"Version file not found: {target_path}"}

        html = target_path.read_text(encoding='utf-8')

        # Save as new version (preserves history)
        new_version = self.save_html(html, target.get("scores"))
        logger.info(f"Rolled back to v{target['version']} → saved as v{new_version['version']}")
        return new_version

    def get_version_history(self) -> list[dict]:
        """Get summary of all versions with scores."""
        return [
            {
                "version": v["version"],
                "size_kb": v.get("size_kb", 0),
                "overall": v.get("scores", {}).get("overall"),
                "scores": v.get("scores", {}),
            }
            for v in self.versions
        ]

    def get_total_lines(self) -> int:
        """Get total line count of current HTML."""
        html = self.read_current()
        if not html:
            return 0
        return len(html.split('\n'))

    def validate_syntax(self) -> dict:
        """
        Basic HTML/JS syntax validation.

        Returns {valid: bool, issues: [str]}
        """
        html = self.read_current()
        if not html:
            return {"valid": False, "issues": ["No HTML file"]}

        issues = []

        # Check for basic HTML structure
        if '<!DOCTYPE' not in html and '<!doctype' not in html:
            issues.append("Missing DOCTYPE declaration")
        if '<html' not in html:
            issues.append("Missing <html> tag")
        if '</html>' not in html:
            issues.append("Missing closing </html> tag")
        if '<head' not in html:
            issues.append("Missing <head> tag")
        if '<body' not in html:
            issues.append("Missing <body> tag")

        # Check for unclosed script tags
        script_opens = html.count('<script')
        script_closes = html.count('</script>')
        if script_opens != script_closes:
            issues.append(f"Mismatched script tags: {script_opens} opens vs {script_closes} closes")

        # Check for unclosed style tags
        style_opens = html.count('<style')
        style_closes = html.count('</style>')
        if style_opens != style_closes:
            issues.append(f"Mismatched style tags: {style_opens} opens vs {style_closes} closes")

        # Check for common JS issues
        # Unmatched braces (rough check)
        js_match = re.search(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
        if js_match:
            js_code = js_match.group(1)
            opens = js_code.count('{')
            closes = js_code.count('}')
            if opens != closes:
                issues.append(f"Potential unmatched braces in JS: {opens} opens vs {closes} closes")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
        }
