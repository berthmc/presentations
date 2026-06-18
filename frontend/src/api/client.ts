import type { Diagnostics, GenerateResult, JobStatusResponse, ModelsResponse, TemplateSummary } from "../types";
import { parseApiError } from "./errors";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api";
const JOB_POLL_INTERVAL_MS = 2000;

const STAGE_LABELS: Record<string, string> = {
  research: "Researching…",
  profile: "Profiling layouts…",
  plan: "Generating plan…",
  assemble: "Assembling slides…",
  inspect: "Running QA…",
};

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(parseApiError(response.status, detail, response.statusText));
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
    const detail = await response.text();
    throw new Error(parseApiError(response.status, detail, "Template upload failed"));
  }
  return response.json();
}

export function deleteTemplate(id: string): Promise<{ deleted: string }> {
  return request(`/templates/${id}`, { method: "DELETE" });
}

export function setDefaultTemplate(id: string): Promise<TemplateSummary> {
  return request(`/templates/${id}/default`, { method: "PATCH" });
}

export function generateDeck(
  payload: {
    brief: string;
    mode: string;
    title?: string;
    run_qa: boolean;
    template_id?: string | null;
    synthesis_model?: string | null;
    source_context?: string | null;
    allow_cloud?: boolean;
  },
  onProgress?: (message: string) => void,
): Promise<GenerateResult> {
  return enqueueAndPollGeneration(payload, onProgress);
}

async function enqueueAndPollGeneration(
  payload: {
    brief: string;
    mode: string;
    title?: string;
    run_qa: boolean;
    template_id?: string | null;
    synthesis_model?: string | null;
    source_context?: string | null;
    allow_cloud?: boolean;
  },
  onProgress?: (message: string) => void,
): Promise<GenerateResult> {
  const startResponse = await fetch(`${API_BASE}/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!startResponse.ok) {
    const detail = await startResponse.text();
    throw new Error(parseApiError(startResponse.status, detail, startResponse.statusText));
  }

  const start = (await startResponse.json()) as { job_id: string; status: string };
  onProgress?.("Queued…");

  while (true) {
    const job = await request<JobStatusResponse>(`/jobs/${start.job_id}`);
    if (job.stage) {
      onProgress?.(STAGE_LABELS[job.stage] ?? `Stage: ${job.stage}`);
    } else if (job.status === "queued") {
      onProgress?.("Queued…");
    } else if (job.status === "running") {
      onProgress?.("Generating…");
    }

    if (job.status === "done") {
      return request<GenerateResult>(`/jobs/${start.job_id}/result`);
    }
    if (job.status === "failed") {
      throw new Error(job.error ?? "Generation failed");
    }
    await sleep(JOB_POLL_INTERVAL_MS);
  }
}

export async function ingestPdf(file: File): Promise<{ source_context: string; filename?: string }> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${API_BASE}/ingest/pdf`, { method: "POST", body: form });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(parseApiError(response.status, detail, "PDF extraction failed"));
  }
  const body = (await response.json()) as { source_context: string; filename?: string; text?: string };
  return {
    source_context: body.source_context ?? body.text ?? "",
    filename: body.filename,
  };
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
