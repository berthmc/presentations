#!/usr/bin/env python3
"""Duplicate a slide or create one from a layout in an unpacked PPTX directory."""

import argparse
import shutil
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Add or duplicate a slide in unpacked PPTX")
    parser.add_argument("input_dir")
    parser.add_argument("slide_or_layout")
    args = parser.parse_args()
    target = Path(args.input_dir)
    source = Path(args.slide_or_layout)
    if not target.is_dir():
        print(f"Directory not found: {target}", file=sys.stderr)
        return 1
    if not source.exists():
        print(f"Slide/layout not found: {source}", file=sys.stderr)
        return 1
    slides = sorted(target.glob("ppt/slides/slide*.xml"))
    next_idx = len(slides) + 1
    dest = target / "ppt" / "slides" / f"slide{next_idx}.xml"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source if source.is_file() else slides[0], dest)
    print(f'<p:sldId id="{256 + next_idx}" r:id="rId{next_idx}"/>')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
