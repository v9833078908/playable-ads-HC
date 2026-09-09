"""
Memory Manager — Generation memory for Orchestrator V2

Saves successful generation patterns and searches past experience.
First version: markdown files + full-text search.
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger('MemoryManager')


class MemoryManager:
    """Manages generation memory: save patterns, search past experience."""

    def __init__(self, memory_dir: str = "memory"):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)

    def save_memory(
        self,
        genre: str,
        scores: dict,
        successful_patterns: list[str],
        failed_approaches: list[str],
        improvement_log: list[dict],
        iterations: int,
    ) -> str:
        """
        Save generation experience to a markdown file.

        Args:
            genre: Game genre (car-wash, merge, etc.)
            scores: Final scores dict {overall, atmosphere, ui, ...}
            successful_patterns: List of patterns that worked well
            failed_approaches: List of approaches that didn't work
            improvement_log: List of {iteration, score, action} dicts
            iterations: Total number of iterations

        Returns:
            Path to saved memory file
        """
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        filename = f"{genre}_{timestamp}.md"
        filepath = self.memory_dir / filename

        overall = scores.get("overall", 0)

        # Build markdown
        lines = [
            f"# {genre.title().replace('-', ' ')} Generation — {datetime.now().strftime('%Y-%m-%d')}",
            "",
            f"## Result: score {overall}, iterations: {iterations}",
            "",
        ]

        if successful_patterns:
            lines.append("## Successful Patterns")
            for pattern in successful_patterns:
                lines.append(f"- {pattern}")
            lines.append("")

        if failed_approaches:
            lines.append("## Failed Approaches (don't repeat)")
            for approach in failed_approaches:
                lines.append(f"- {approach}")
            lines.append("")

        if improvement_log:
            lines.append("## Improvement Log")
            for entry in improvement_log:
                iteration = entry.get("iteration", "?")
                score = entry.get("score", "?")
                action = entry.get("action", "unknown")
                lines.append(f"- iteration {iteration} → {score}: {action}")
            lines.append("")

        # Score breakdown
        lines.append("## Scores")
        for category, score in scores.items():
            if category != "overall":
                lines.append(f"- {category}: {score}")
        lines.append(f"- **overall: {overall}**")
        lines.append("")

        content = "\n".join(lines)
        filepath.write_text(content, encoding='utf-8')

        logger.info(f"Saved memory: {filepath} (score {overall})")
        return str(filepath)

    def search_memory(
        self,
        query: str,
        genre: Optional[str] = None,
        min_score: float = 6.0,
        top_k: int = 3,
    ) -> list[dict]:
        """
        Search past generation memories by full-text search.

        Args:
            query: Search query string
            genre: Optional genre filter
            min_score: Minimum overall score to include
            top_k: Number of results to return

        Returns:
            List of {file, score, relevant_sections} dicts
        """
        if not self.memory_dir.exists():
            return []

        results = []
        query_lower = query.lower()
        query_words = query_lower.split()

        for filepath in sorted(self.memory_dir.glob("*.md"), reverse=True):
            # Genre filter
            if genre and not filepath.name.startswith(genre.lower().replace(" ", "-")):
                continue

            content = filepath.read_text(encoding='utf-8')
            content_lower = content.lower()

            # Extract score from content
            file_score = self._extract_score(content)
            if file_score < min_score:
                continue

            # Simple relevance: count matching query words
            relevance = sum(1 for word in query_words if word in content_lower)
            if relevance == 0 and not genre:
                continue  # Skip files with no matching words (unless genre match)

            # Extract relevant sections
            sections = self._extract_relevant_sections(content, query_words)

            results.append({
                "file": str(filepath),
                "score": file_score,
                "relevance": relevance,
                "sections": sections,
            })

        # Sort by relevance then score
        results.sort(key=lambda r: (r["relevance"], r["score"]), reverse=True)
        return results[:top_k]

    def get_best_practices(self, genre: str) -> Optional[str]:
        """
        Get a combined summary of best practices for a genre.

        Reads all memory files for the genre, combines successful patterns
        and failed approaches.

        Returns formatted string or None if no memories.
        """
        memories = self.search_memory(query=genre, genre=genre, min_score=5.0, top_k=5)

        if not memories:
            return None

        successful = set()
        failed = set()

        for mem in memories:
            for section in mem.get("sections", []):
                if "successful" in section.lower() or "worked" in section.lower():
                    # Extract bullet points
                    for line in section.split('\n'):
                        line = line.strip()
                        if line.startswith('- '):
                            successful.add(line[2:])
                elif "failed" in section.lower() or "don't" in section.lower():
                    for line in section.split('\n'):
                        line = line.strip()
                        if line.startswith('- '):
                            failed.add(line[2:])

        if not successful and not failed:
            return None

        result = ""
        if successful:
            result += "Proven patterns from past generations:\n"
            for s in list(successful)[:10]:
                result += f"- {s}\n"

        if failed:
            result += "\nAvoid these approaches (failed before):\n"
            for f in list(failed)[:5]:
                result += f"- {f}\n"

        return result

    def _extract_score(self, content: str) -> float:
        """Extract overall score from memory file content."""
        import re
        match = re.search(r'score\s+(\d+\.?\d*)', content[:200])
        if match:
            return float(match.group(1))
        return 0.0

    def _extract_relevant_sections(self, content: str, query_words: list[str]) -> list[str]:
        """Extract sections of content that are relevant to query."""
        sections = content.split("\n## ")
        relevant = []

        for section in sections:
            section_lower = section.lower()
            if any(word in section_lower for word in query_words):
                # Take first 500 chars of matching section
                relevant.append("## " + section[:500].strip())

        # Always include "Successful Patterns" and "Failed Approaches" sections
        for section in sections:
            header = section.split('\n')[0].lower()
            if ("successful" in header or "failed" in header) and section not in relevant:
                relevant.append("## " + section[:500].strip())

        return relevant[:5]

    def list_memories(self, genre: Optional[str] = None) -> list[dict]:
        """List all memory files, optionally filtered by genre."""
        if not self.memory_dir.exists():
            return []

        result = []
        for filepath in sorted(self.memory_dir.glob("*.md"), reverse=True):
            if genre and not filepath.name.startswith(genre.lower().replace(" ", "-")):
                continue

            content = filepath.read_text(encoding='utf-8')
            score = self._extract_score(content)

            result.append({
                "file": filepath.name,
                "score": score,
                "size": filepath.stat().st_size,
            })

        return result
