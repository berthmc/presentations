#!/usr/bin/env node
/**
 * Build MD3-compliant presentations from scratch using pptxgenjs.
 * Reads JSON spec from stdin; writes .pptx to outputPath.
 */
import fs from "node:fs";
import path from "node:path";
import pptxgen from "pptxgenjs";

function readStdin() {
  return new Promise((resolve, reject) => {
    let data = "";
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", (chunk) => (data += chunk));
    process.stdin.on("end", () => resolve(data));
    process.stdin.on("error", reject);
  });
}

function addTitleSlide(pres, slideSpec, theme) {
  const slide = pres.addSlide();
  const colors = theme.colors;
  slide.background = { color: colors.primary };
  const title = slideSpec.mappings.find((m) => m.ph_idx === 0)?.content || slideSpec.title || "Title";
  const subtitle = slideSpec.mappings.find((m) => m.ph_idx === 1)?.content || "";
  slide.addText(title, {
    x: 0.7,
    y: 1.8,
    w: 8.6,
    h: 1.2,
    fontSize: theme.fonts.titleSize,
    fontFace: theme.fonts.titleFont,
    color: colors.onPrimary,
    bold: true,
    margin: 0,
  });
  if (subtitle) {
    slide.addText(subtitle, {
      x: 0.7,
      y: 3.1,
      w: 8.6,
      h: 0.8,
      fontSize: theme.fonts.sectionSize,
      fontFace: theme.fonts.bodyFont,
      color: colors.onPrimary,
      margin: 0,
    });
  }
}

function addContentSlide(pres, slideSpec, theme) {
  const slide = pres.addSlide();
  const colors = theme.colors;
  slide.background = { color: colors.surfaceContainer };
  const title = slideSpec.mappings.find((m) => m.ph_idx === 0)?.content || "Section";
  const bodyMapping = slideSpec.mappings.find((m) => m.ph_idx === 1);
  const bodyLines = bodyMapping ? bodyMapping.content.split("\n").filter(Boolean) : [];

  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0,
    y: 0,
    w: 10,
    h: 0.9,
    fill: { color: colors.primary },
    line: { color: colors.primary, width: 0 },
  });
  slide.addText(title, {
    x: 0.5,
    y: 0.15,
    w: 9,
    h: 0.6,
    fontSize: theme.fonts.sectionSize,
    fontFace: theme.fonts.titleFont,
    color: colors.onPrimary,
    bold: true,
    margin: 0,
  });

  const bulletRuns = bodyLines.map((line, idx) => ({
    text: line.replace(/^[-•]\s*/, ""),
    options: { bullet: true, breakLine: idx < bodyLines.length - 1 },
  }));
  if (bulletRuns.length) {
    slide.addText(bulletRuns, {
      x: 0.7,
      y: 1.3,
      w: 8.6,
      h: 3.8,
      fontSize: theme.fonts.bodySize,
      fontFace: theme.fonts.bodyFont,
      color: colors.onSurface,
      valign: "top",
    });
  }
}

function addTwoColumnSlide(pres, slideSpec, theme) {
  const slide = pres.addSlide();
  const colors = theme.colors;
  slide.background = { color: colors.surface };
  const title = slideSpec.mappings.find((m) => m.ph_idx === 0)?.content || "Overview";
  const left = slideSpec.mappings.find((m) => m.ph_idx === 1)?.content || "";
  const right = slideSpec.mappings.find((m) => m.ph_idx === 2)?.content || "";

  slide.addText(title, {
    x: 0.5,
    y: 0.35,
    w: 9,
    h: 0.7,
    fontSize: theme.fonts.sectionSize,
    fontFace: theme.fonts.titleFont,
    color: colors.onSurface,
    bold: true,
    margin: 0,
  });

  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5,
    y: 1.2,
    w: 4.3,
    h: 3.9,
    fill: { color: colors.surfaceContainer },
    line: { color: colors.outline, width: 1 },
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 5.2,
    y: 1.2,
    w: 4.3,
    h: 3.9,
    fill: { color: colors.surfaceContainer },
    line: { color: colors.outline, width: 1 },
  });

  slide.addText(left, {
    x: 0.7,
    y: 1.4,
    w: 3.9,
    h: 3.5,
    fontSize: theme.fonts.bodySize,
    fontFace: theme.fonts.bodyFont,
    color: colors.onSurface,
    valign: "top",
  });
  slide.addText(right, {
    x: 5.4,
    y: 1.4,
    w: 3.9,
    h: 3.5,
    fontSize: theme.fonts.bodySize,
    fontFace: theme.fonts.bodyFont,
    color: colors.onSurface,
    valign: "top",
  });
}

async function main() {
  const raw = await readStdin();
  const payload = JSON.parse(raw);
  const { deckSpec, theme, outputPath } = payload;

  const pres = new pptxgen();
  pres.layout = theme.layout || "LAYOUT_16x9";
  pres.author = "PPTX Engine";
  pres.title = deckSpec.title || "Presentation";

  for (const slideSpec of deckSpec.slides) {
    const layoutIndex = slideSpec.layout_index ?? 0;
    if (layoutIndex === 0) {
      addTitleSlide(pres, slideSpec, theme);
    } else if (layoutIndex === 2) {
      addTwoColumnSlide(pres, slideSpec, theme);
    } else {
      addContentSlide(pres, slideSpec, theme);
    }
  }

  const out = path.resolve(outputPath);
  fs.mkdirSync(path.dirname(out), { recursive: true });
  await pres.writeFile({ fileName: out });
  process.stdout.write(JSON.stringify({ outputPath: out }));
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
