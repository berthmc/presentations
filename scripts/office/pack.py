#!/usr/bin/env python3
"""Repack an unpacked PPTX directory."""

import argparse
import shutil
import zipfile
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Pack directory into PPTX")
    parser.add_argument("input_dir")
    parser.add_argument("output_pptx")
    parser.add_argument("--original", default=None)
    args = parser.parse_args()
    src_dir = Path(args.input_dir)
    out = Path(args.output_pptx)
    if out.exists():
        out.unlink()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        for file_path in sorted(src_dir.rglob("*")):
            if file_path.is_file():
                archive.write(file_path, file_path.relative_to(src_dir).as_posix())
    print(f"Packed {src_dir} -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
