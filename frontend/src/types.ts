export interface Diagnostics {
  active_profile: string;
  synthesis_model: string;
  vlm_model: string;
  total_ram_gb?: number;
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
