export interface Diagnostics {
  active_profile: string;
  synthesis_model: string;
  vlm_model: string;
  total_ram_gb?: number;
}

export interface ModelOption {
  id: string;
  label: string;
  provider: string;
  recommended_for: string;
  speed: string;
  quality: string;
  notes: string;
  available: boolean;
}

export interface ModelsResponse {
  default: string;
  models: ModelOption[];
}

export interface TemplateSummary {
  id: string;
  name: string;
  source_type: string;
  is_default: boolean;
  layout_count: number;
  layout_names: string[];
}

export interface QAIssue {
  slide: number;
  severity: string;
  category: string;
  message: string;
}

export interface QAReport {
  passed: boolean;
  reasons: string[];
  issues: QAIssue[];
  slide_images: string[];
}

export interface GenerateResult {
  output_path: string;
  qa_report?: QAReport | null;
}

export interface JobStatusResponse {
  job_id: string;
  status: "queued" | "running" | "done" | "failed";
  stage?: string | null;
  error?: string | null;
}
