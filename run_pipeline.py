#!/usr/bin/env python3
"""
CLI entrypoint for the V2 orchestrator pipeline.

Reads a technical specification (markdown/plain text), optionally loads style
reference images, and runs the orchestrator until the QA loop converges.

Usage:
    python run_pipeline.py spec.md --assets ./references --output output
    python run_pipeline.py spec.md --resume
"""

import argparse
import asyncio
import base64
import logging
import mimetypes
import sys
from pathlib import Path

from dotenv import load_dotenv

REQUIRED_KEYS = ("ANTHROPIC_API_KEY", "GEMINI_API_KEY", "FAL_KEY")
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def load_reference_assets(assets_dir: Path) -> dict[str, str]:
    """Encode every image in assets_dir as a base64 data URI keyed by filename."""
    references: dict[str, str] = {}
    for path in sorted(assets_dir.iterdir()):
        if path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        mime = mimetypes.guess_type(path.name)[0] or "image/png"
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        references[path.name] = f"data:{mime};base64,{encoded}"
    return references


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a playable ad from a specification.")
    parser.add_argument("spec", type=Path, help="path to the specification (.md/.txt)")
    parser.add_argument("--assets", type=Path, help="directory with style reference images")
    parser.add_argument("--output", type=Path, default=Path("output"), help="output directory")
    parser.add_argument("--memory", type=Path, default=Path("memory"), help="generation memory directory")
    parser.add_argument("--resume", action="store_true", help="reuse output/output_v1.html and only run the QA loop")
    parser.add_argument("--verbose", action="store_true", help="log every orchestrator turn")
    return parser.parse_args(argv)


async def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    load_dotenv()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    import os

    missing = [key for key in REQUIRED_KEYS if not os.getenv(key)]
    if missing:
        print(f"Missing API keys: {', '.join(missing)}. Copy .env.example to .env.", file=sys.stderr)
        return 2

    if not args.spec.is_file():
        print(f"Specification not found: {args.spec}", file=sys.stderr)
        return 2

    references = None
    if args.assets:
        if not args.assets.is_dir():
            print(f"Assets directory not found: {args.assets}", file=sys.stderr)
            return 2
        references = load_reference_assets(args.assets)
        print(f"Loaded {len(references)} reference image(s) from {args.assets}")

    from playable_agents.orchestrator import run_orchestrator

    result = await run_orchestrator(
        spec_text=args.spec.read_text(encoding="utf-8"),
        reference_assets=references,
        output_dir=str(args.output),
        memory_dir=str(args.memory),
        resume=args.resume,
    )

    if not result.get("success"):
        print(f"Pipeline failed: {result.get('error', 'unknown error')}", file=sys.stderr)
        return 1

    print(f"HTML: {result.get('html_path')}")
    print(f"QA iterations: {result.get('iterations')}")
    print(f"Scores: {result.get('scores')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
