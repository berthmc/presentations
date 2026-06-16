import { useEffect, useState } from "react";
import { getDiagnostics } from "../api/client";
import type { Diagnostics } from "../types";

function modelBadgeKind(model: string): "local" | "cloud" | "neutral" {
  const lower = model.toLowerCase();
  if (lower.includes("gemini") || lower.includes("cloud") || lower.includes("vertex")) {
    return "cloud";
  }
  if (lower.includes("ollama") || lower.includes("local") || lower.includes("llama") || lower.includes("mistral")) {
    return "local";
  }
  return "neutral";
}

function SignalTile({
  label,
  value,
  badge,
}: {
  label: string;
  value: string;
  badge?: { text: string; kind: "local" | "cloud" | "neutral" };
}) {
  return (
    <article className="signal-tile">
      {badge && (
        <span className={`signal-tile__badge signal-tile__badge--${badge.kind}`}>{badge.text}</span>
      )}
      <span className="signal-tile__label">{label}</span>
      <span className="signal-tile__value">{value}</span>
    </article>
  );
}

export function DiagnosticsCard() {
  const [data, setData] = useState<Diagnostics | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getDiagnostics()
      .then(setData)
      .catch((err: Error) => setError(err.message));
  }, []);

  return (
    <section className="md3-card">
      <header className="section-header">
        <h2>Hardware Profile</h2>
        {data && (
          <span className="chip chip--profile">{data.active_profile}</span>
        )}
        {!data && !error && <span className="section-header__meta">Loading…</span>}
      </header>

      {error && <p className="status error">Diagnostics unavailable: {error}</p>}

      {!error && !data && (
        <div className="skeleton-grid" aria-hidden="true">
          <div className="skeleton-tile" />
          <div className="skeleton-tile" />
          <div className="skeleton-tile" />
          <div className="skeleton-tile" />
        </div>
      )}

      {data && (
        <div className="signal-grid">
          <SignalTile label="Profile" value={data.active_profile} badge={{ text: "active", kind: "neutral" }} />
          <SignalTile
            label="Synthesis model"
            value={data.synthesis_model}
            badge={{
              text: modelBadgeKind(data.synthesis_model),
              kind: modelBadgeKind(data.synthesis_model),
            }}
          />
          <SignalTile
            label="VLM model"
            value={data.vlm_model}
            badge={{
              text: modelBadgeKind(data.vlm_model),
              kind: modelBadgeKind(data.vlm_model),
            }}
          />
          <SignalTile
            label="RAM"
            value={data.total_ram_gb != null ? `${data.total_ram_gb} GB` : "n/a"}
            badge={{ text: "system", kind: "neutral" }}
          />
        </div>
      )}
    </section>
  );
}
