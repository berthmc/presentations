"""Verify enriched template analysis for the VI EC corporate template."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from presentations.ingest.pptx_layout import generate_layout_map
from presentations.llm.synthesis import _build_user_prompt
from presentations.core.schemas import GenerationMode

TEMPLATE = Path("documentation/briefs/VI_EC_Corporate_PPT_Template_2026.pptx")
OUTPUT = Path("debug_scripts/template_enrichment_verify.txt")


def main() -> int:
    if not TEMPLATE.exists():
        print(f"Template missing: {TEMPLATE}", file=sys.stderr)
        return 1

    profile = generate_layout_map(TEMPLATE)
    roles = Counter(entry.role for entry in profile.layouts.values())
    lines = [
        f"Template: {TEMPLATE}",
        f"Layouts: {len(profile.layouts)}",
        f"Roles: {dict(sorted(roles.items()))}",
        f"Theme fonts: {profile.theme.get('fonts')}",
        f"Theme accent count: {len(profile.theme.get('accents', {}))}",
        "",
        "Sample enriched layouts:",
    ]
    for idx in sorted(profile.layouts.keys())[:5]:
        entry = profile.layouts[idx]
        lines.append(f"- [{idx}] {entry.name} role={entry.role} picture={entry.has_picture}")
        lines.append(f"  summary: {entry.summary}")

    prompt = _build_user_prompt(
        brief="Target length: 8 slides\nTopic: MiFID II investor briefing",
        layout=profile,
        mode=GenerationMode.TEMPLATE,
    )
    lines.extend(
        [
            "",
            f"Prompt length: {len(prompt)} chars",
            f"Brand block present: {'Brand identity' in prompt}",
            f"Summary fields present: {'\"summary\"' in prompt}",
        ]
    )

    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"roles": dict(roles), "output": str(OUTPUT)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
