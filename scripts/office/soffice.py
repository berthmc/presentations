#!/usr/bin/env python3
"""Headless LibreOffice conversion wrapper."""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert office documents via soffice")
    parser.add_argument("input_file")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--convert-to", dest="convert_to", default="pdf")
    args = parser.parse_args()
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        print("soffice not found", file=sys.stderr)
        return 1
    src = Path(args.input_file)
    outdir = src.parent
    subprocess.run(
        [soffice, "--headless", "--convert-to", args.convert_to, "--outdir", str(outdir), str(src)],
        check=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
