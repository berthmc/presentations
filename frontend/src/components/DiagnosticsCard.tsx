import { useEffect, useState } from "react";
import { getDiagnostics } from "../api/client";
import type { Diagnostics } from "../types";

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
      <h2>Hardware Profile</h2>
      {error && <p className="status error">Diagnostics unavailable: {error}</p>}
      {!error && !data && <p className="status">Loading diagnostics…</p>}
      {data && (
        <dl className="diagnostics-grid">
          <div>
            <dt>Profile</dt>
            <dd>{data.active_profile}</dd>
          </div>
          <div>
            <dt>Synthesis model</dt>
            <dd>{data.synthesis_model}</dd>
          </div>
          <div>
            <dt>VLM model</dt>
            <dd>{data.vlm_model}</dd>
          </div>
          <div>
            <dt>RAM</dt>
            <dd>{data.total_ram_gb ?? "n/a"} GB</dd>
          </div>
        </dl>
      )}
    </section>
  );
}
