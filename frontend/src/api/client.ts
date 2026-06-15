import type { Diagnostics, GenerateResult, ModelsResponse, TemplateSummary } from "../types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || response.statusText);
  }
  return response.json() as Promise<T>;
}

export function getDiagnostics(): Promise<Diagnostics> {
  return request("/diagnostics");
}

export function getModels(): Promise<ModelsResponse> {
  return request("/models");
}

export function listTemplates(): Promise<{ templates: TemplateSummary[] }> {
  return request("/templates");
}

export async function registerTemplate(
  name: string,
  file: File,
  isDefault: boolean,
): Promise<TemplateSummary> {
  const form = new FormData();
  form.append("name", name);
  form.append("is_default", String(isDefault));
  form.append("file", file);
  const response = await fetch(`${API_BASE}/templates`, { method: "POST", body: form });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

export function deleteTemplate(id: string): Promise<{ deleted: string }> {
  return request(`/templates/${id}`, { method: "DELETE" });
}

export function setDefaultTemplate(id: string): Promise<TemplateSummary> {
  return request(`/templates/${id}/default`, { method: "PATCH" });
}

export function generateDeck(payload: {
  brief: string;
  mode: string;
  title?: string;
  run_qa: boolean;
  template_id?: string | null;
  synthesis_model?: string | null;
}): Promise<GenerateResult> {
  return request("/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function ingestPdf(file: File): Promise<{ text: string }> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${API_BASE}/ingest/pdf`, { method: "POST", body: form });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json() as Promise<{ text: string }>;
}

export function qaSlideUrl(imagePath: string): string {
  const normalized = imagePath.replace(/\\/g, "/");
  const parts = normalized.split("/");
  const filename = parts[parts.length - 1] ?? "";
  const stem = parts[parts.length - 2] ?? "";
  return `${API_BASE}/qa/slides/${encodeURIComponent(stem)}/${encodeURIComponent(filename)}`;
}

export function downloadUrl(outputPath: string): string {
  const filename = outputPath.replace(/\\/g, "/").split("/").pop() ?? "";
  return `${API_BASE}/download/${encodeURIComponent(filename)}`;
}
