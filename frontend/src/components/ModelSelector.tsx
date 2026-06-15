import { useEffect, useState } from "react";
import { getModels } from "../api/client";
import type { ModelOption } from "../types";

interface Props {
  value: string;
  onChange: (value: string) => void;
}

function formatAdvisory(model: ModelOption | null): string {
  if (!model) {
    return "Auto selects the best local model for your hardware profile, with Gemini as fallback when Ollama is unavailable.";
  }
  const speedLabel = model.speed === "fast" ? "Fast" : model.speed === "slow" ? "Slower" : "Medium speed";
  const qualityLabel =
    model.quality === "high" ? "Higher quality" : model.quality === "basic" ? "Basic quality" : "Good quality";
  return `${speedLabel}, ${qualityLabel}. ${model.notes}`;
}

export function ModelSelector({ value, onChange }: Props) {
  const [models, setModels] = useState<ModelOption[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getModels()
      .then((payload) => setModels(payload.models))
      .catch((err: Error) => setError(err.message));
  }, []);

  const selectedModel = value === "auto" ? null : models.find((model) => model.id === value) ?? null;

  return (
    <div className="field">
      <label htmlFor="synthesis-model">Synthesis model</label>
      <select id="synthesis-model" value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="auto">Auto (recommended)</option>
        {models.map((model) => (
          <option key={model.id} value={model.id} disabled={!model.available}>
            {model.label}
            {!model.available ? " (not available)" : ""}
          </option>
        ))}
      </select>
      {error && <p className="field-help error">Model catalog unavailable: {error}</p>}
      <p className="field-help">{formatAdvisory(selectedModel)}</p>
      {selectedModel && (
        <p className="field-help subtle">Recommended for: {selectedModel.recommended_for}</p>
      )}
    </div>
  );
}
