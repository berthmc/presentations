#!/usr/bin/env python3
"""Create a thumbnail grid from a presentation (requires markitdown + Pillow)."""

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract text overview of a PPTX via markitdown")
    parser.add_argument("pptx_path")
    parser.add_argument("output_prefix", nargs="?", default="thumbnails")
    args = parser.parse_args()
    path = Path(args.pptx_path)
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        return 1
    result = subprocess.run(
        [sys.executable, "-m", "markitdown", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    out = Path(f"{args.output_prefix}.txt")
    out.write_text(result.stdout or result.stderr, encoding="utf-8")
    print(f"Wrote text overview to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
