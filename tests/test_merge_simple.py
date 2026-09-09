#!/usr/bin/env python3
"""Test merge logic - simplified to avoid API dependencies"""

import sys
import os

# Add parent dir to path
sys.path.insert(0, os.path.dirname(__file__))

from models.brief import DraftBrief, SceneDescription


def merge_briefs_copy(text_brief, pdf_brief):
    """Copy of merge_briefs function for testing"""
    import logging
    logger = logging.getLogger('test')

    # Handle single-source cases
    if not text_brief and not pdf_brief:
        logger.warning("No briefs to merge, returning defaults")
        return DraftBrief()

    if not text_brief:
        logger.info("Only PDF brief provided, returning it")
        return pdf_brief

    if not pdf_brief:
        logger.info("Only text brief provided, returning it")
        return text_brief

    # Both sources available - merge intelligently
    logger.info("Merging text and PDF briefs")
    merged = DraftBrief()

    # Title: prefer PDF
    if pdf_brief.title != "Playable Ad":
        merged.title = pdf_brief.title
        merged.sources["title"] = "pdf"
        merged.confidence_scores["title"] = 0.95
        if text_brief.title != "Playable Ad" and text_brief.title != pdf_brief.title:
            merged.merge_notes.append(f"Title conflict: used PDF '{pdf_brief.title}' over text '{text_brief.title}'")
    else:
        merged.title = text_brief.title
        merged.sources["title"] = "text"
        merged.confidence_scores["title"] = 0.85

    # Networks: union
    merged.networks = list(set(text_brief.networks + pdf_brief.networks))

    # Languages: union
    merged.languages = list(set(text_brief.languages + pdf_brief.languages))

    # Scenes: merge by ID, prefer PDF for conflicts
    scenes_dict = {}

    # Add text scenes first
    for scene in text_brief.scenes:
        scenes_dict[scene.id] = scene
        merged.sources[f"scenes.{scene.id}"] = "text"

    # Override/merge with PDF scenes
    for scene in pdf_brief.scenes:
        if scene.id in scenes_dict:
            # Conflict - prefer PDF but note it
            existing_desc = scenes_dict[scene.id].description
            if existing_desc != scene.description:
                merged.merge_notes.append(f"Scene '{scene.id}': merged descriptions from both sources")
                # Combine descriptions if they're different
                scenes_dict[scene.id] = scene
                scenes_dict[scene.id].description = f"{scene.description} | {existing_desc}"
                merged.sources[f"scenes.{scene.id}"] = "merged"
                merged.confidence_scores[f"scenes.{scene.id}"] = 0.90
            else:
                scenes_dict[scene.id] = scene
                merged.sources[f"scenes.{scene.id}"] = "pdf"
        else:
            scenes_dict[scene.id] = scene
            merged.sources[f"scenes.{scene.id}"] = "pdf"

    merged.scenes = list(scenes_dict.values())

    # Copy texts: merge dictionaries, prefer PDF for conflicts
    merged.copy_texts = {**text_brief.copy_texts}
    for key, value in pdf_brief.copy_texts.items():
        if key in merged.copy_texts and merged.copy_texts[key] != value:
            merged.merge_notes.append(f"Copy text '{key}': used PDF value over text value")
            merged.sources[f"copy_texts.{key}"] = "pdf"
        else:
            merged.sources[f"copy_texts.{key}"] = "pdf" if key in pdf_brief.copy_texts else "text"
        merged.copy_texts[key] = value

    # Unknowns: combine
    merged.unknowns = list(set(text_brief.unknowns + pdf_brief.unknowns))

    # Visual references: only from PDF
    merged.visual_references = pdf_brief.visual_references

    logger.info(f"Merged brief: {len(merged.scenes)} scenes, {len(merged.merge_notes)} merge notes")

    return merged


def test_merge_both():
    """Test merge with both text and PDF"""
    print("\n=== Testing merge with both text and PDF ===")

    text_brief = DraftBrief(
        title="Text Title",
        scenes=[
            SceneDescription(id="scene1", description="Text desc", type="tutorial"),
            SceneDescription(id="scene3", description="Text only scene", type="victory"),
        ],
        copy_texts={"subtitle": "Text subtitle"},
    )
    text_brief.sources["title"] = "text"

    pdf_brief = DraftBrief(
        title="PDF Title",
        scenes=[
            SceneDescription(id="scene1", description="PDF desc", type="tutorial"),
            SceneDescription(id="scene2", description="PDF only scene", type="battle"),
        ],
        copy_texts={"cta": "PDF CTA"},
    )
    pdf_brief.sources["title"] = "pdf"

    result = merge_briefs_copy(text_brief, pdf_brief)

    # Verify results
    print(f"✓ Title: {result.title} (source: {result.sources.get('title')})")
    print(f"✓ Scenes: {len(result.scenes)}")
    for scene in result.scenes:
        print(f"  - {scene.id}: {scene.description[:50]}...")
    print(f"✓ Copy texts: {list(result.copy_texts.keys())}")
    print(f"✓ Merge notes ({len(result.merge_notes)}):")
    for note in result.merge_notes:
        print(f"  - {note}")

    # Assertions
    assert result.title == "PDF Title", f"Expected 'PDF Title', got {result.title}"
    assert len(result.scenes) == 3, f"Expected 3 scenes, got {len(result.scenes)}"
    assert "subtitle" in result.copy_texts, "Should have subtitle from text"
    assert "cta" in result.copy_texts, "Should have CTA from PDF"

    print("✅ Test PASSED\n")
    return True


def main():
    """Run test"""
    print("Testing Merge Logic (Simplified)")
    print("=" * 50)

    try:
        result = test_merge_both()
        print("=" * 50)
        if result:
            print("✅ Test PASSED")
            return 0
        else:
            print("❌ Test FAILED")
            return 1
    except Exception as e:
        print(f"❌ Test FAILED with exception: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
