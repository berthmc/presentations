#!/usr/bin/env python3
"""Unpack a PPTX to a directory of XML files."""

import argparse
import shutil
import zipfile
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Unpack PPTX archive")
    parser.add_argument("input_pptx")
    parser.add_argument("output_dir")
    args = parser.parse_args()
    src = Path(args.input_pptx)
    dest = Path(args.output_dir)
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(src, "r") as archive:
        archive.extractall(dest)
    print(f"Unpacked {src} -> {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
