export interface BriefFields {
  topic: string;
  audience: string;
  goal: string;
  tone: string;
  slideCount: string;
  keyPoints: string;
}

export const EXAMPLE_BRIEF: BriefFields = {
  topic: "Impact of MiFID II on EU retail investors",
  audience: "EU retail investors with basic markets knowledge",
  goal: "Explain key MiFID II requirements and how they protect investors",
  tone: "Professional, objective, British English",
  slideCount: "8",
  keyPoints:
    "Transparency rules\nBest execution\nProduct governance\nInvestor protection measures",
};

export function composeBrief(fields: BriefFields): string {
  const lines: string[] = [];

  if (fields.topic.trim()) {
    lines.push(`Topic: ${fields.topic.trim()}`);
  }
  if (fields.audience.trim()) {
    lines.push(`Audience: ${fields.audience.trim()}`);
  }
  if (fields.goal.trim()) {
    lines.push(`Goal: ${fields.goal.trim()}`);
  }
  if (fields.tone.trim()) {
    lines.push(`Tone: ${fields.tone.trim()}`);
  }
  if (fields.slideCount.trim()) {
    lines.push(`Target length: ${fields.slideCount.trim()} slides`);
  }
  if (fields.keyPoints.trim()) {
    lines.push("Key points:");
    fields.keyPoints
      .trim()
      .split("\n")
      .forEach((line) => {
        const trimmed = line.trim();
        if (trimmed) {
          lines.push(`- ${trimmed}`);
        }
      });
  }

  return lines.join("\n");
}
