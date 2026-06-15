import { useEffect, useState } from "react";
import { getModels } from "../api/client";
import type { ModelOption } from "../types";

interface Props {
  value: string;
  onChange: (value: string) => void;
  allowCloud: boolean;
}

function formatAdvisory(model: ModelOption | null, allowCloud: boolean): string {
  if (!model) {
    return allowCloud
      ? "Auto selects the best local model for your hardware profile, with Gemini as fallback when Ollama fails."
      : "Auto uses local Ollama only. Enable cloud AI below to allow Gemini fallback.";
  }
  const speedLabel = model.speed === "fast" ? "Fast" : model.speed === "slow" ? "Slower" : "Medium speed";
  const qualityLabel =
    model.quality === "high" ? "Higher quality" : model.quality === "basic" ? "Basic quality" : "Good quality";
  return `${speedLabel}, ${qualityLabel}. ${model.notes}`;
}

function isGeminiModel(model: ModelOption): boolean {
  return model.provider === "gemini" || model.id.startsWith("gemini");
}

export function ModelSelector({ value, onChange, allowCloud }: Props) {
  const [models, setModels] = useState<ModelOption[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getModels()
      .then((payload) => setModels(payload.models))
      .catch((err: Error) => setError(err.message));
  }, []);

  const selectedModel = value === "auto" ? null : models.find((model) => model.id === value) ?? null;
  const geminiSelected = selectedModel ? isGeminiModel(selectedModel) : false;

  return (
    <div className="field">
      <label htmlFor="synthesis-model">Synthesis model</label>
      <select id="synthesis-model" value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="auto">Auto (recommended)</option>
        {models.map((model) => {
          const cloudBlocked = isGeminiModel(model) && !allowCloud && !geminiSelected;
          return (
            <option
              key={model.id}
              value={model.id}
              disabled={!model.available || cloudBlocked}
              title={cloudBlocked ? "Enable cloud AI below to use Gemini models" : undefined}
            >
              {model.label}
              {!model.available ? " (not available)" : ""}
              {cloudBlocked ? " (enable cloud AI)" : ""}
            </option>
          );
        })}
      </select>
      {error && <p className="field-help error">Model catalog unavailable: {error}</p>}
      <p className="field-help">{formatAdvisory(selectedModel, allowCloud)}</p>
      {selectedModel && (
        <p className="field-help subtle">Recommended for: {selectedModel.recommended_for}</p>
      )}
    </div>
  );
}
