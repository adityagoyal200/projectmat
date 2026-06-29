export interface SheetSummary {
  total_rows: number;
  errors: number;
  warnings: number;
}

export interface ValidationIssue {
  sheet_name?: string;
  row_number?: number;
  column_name?: string;
  code?: string;
  severity: 'error' | 'warning';
  message: string;
}

export interface ImportBatchResponse {
  id: number;
  status: string;
  can_proceed: boolean;
  sheet_summaries: Record<string, SheetSummary>;
  issues: ValidationIssue[];
}

export interface Candidate {
  id: number;
  registration_number: string;
  name: string;
  email?: string;
}

export interface Mentor {
  id: number;
  name: string;
  email: string;
  phone?: string | null;
  project?: {
    id: number;
    title: string;
  } | null;
}

export interface Project {
  id: number;
  title: string;
  mentor?: {
    id?: number;
    name: string;
    email?: string;
    phone?: string | null;
  } | null;
}

export interface ScoreComponents {
  embedding_similarity: number;
  readiness: number;
  growth_potential: number;
  interest: number;
  prerequisite_overlap: number;
  resume_experience: number;
  preference_signal: number;
  preliminary_score: number;
  llm_evaluated: boolean;
}

export interface ScoreBreakdown {
  scoring_version: string;
  formula: string;
  weights: Record<string, number>;
  weighted_contributions: Record<string, number>;
  prerequisite_detail: string;
  resume_experience_detail: string;
  preference_detail: string;
  embedding_detail: string;
  llm_scoring_rationale: string;
  llm_provider?: string | null;
  llm_model?: string | null;
}

export interface MatchRecommendation {
  rank?: number;
  project_id?: number;
  project_title?: string;
  candidate_id?: number;
  candidate_name?: string;
  registration_number?: string;
  mentor_name?: string;
  mentor_email?: string | null;
  mentor_phone?: string | null;
  final_score: number;
  score_components: ScoreComponents;
  score_breakdown: ScoreBreakdown;
  explanation: string;
  technical_readiness: string;
  growth_potential: string;
  interest_alignment: string;
}

export interface StudentRecommendationsResponse {
  candidate_name: string;
  registration_number: string;
  recommendations: MatchRecommendation[];
}

export interface ProjectRecommendationsResponse {
  project_id: number;
  project_title: string;
  recommendations: MatchRecommendation[];
}

export interface LlmPreviewResult {
  provider: string;
  model?: string | null;
  llm_enabled: boolean;
  configured: boolean;
  skipped: boolean;
  skip_reason?: string | null;
  error?: string | null;
  http_status?: number | null;
  prompt_preview?: string | null;
  raw_response: string;
  response_length: number;
}

export interface HealthDetails {
  status?: string;
  database?: string;
  environment?: string;
  llm?: {
    enabled: boolean;
    provider: string;
    configured: boolean;
  };
  error?: string;
}

// ── Batch score matrix ────────────────────────────────────────────────────────

export interface ImportBatchListItem {
  id: number;
  status: string;
  created_at: string;
  candidate_count: number;
  project_count: number;
}

export interface BatchStudentSummary {
  candidate_id: number;
  candidate_name: string;
  registration_number: string;
}

export interface BatchProjectSummary {
  project_id: number;
  project_title: string;
  mentor_name: string;
  mentor_email?: string | null;
}

export interface PairScore {
  candidate_id: number;
  project_id: number;
  embedding_similarity: number;
  prerequisite_overlap: number;
  resume_experience: number;
  preference_signal: number;
  preliminary_score: number;
}

export interface BatchScoreMatrixResponse {
  batch_id: number;
  students: BatchStudentSummary[];
  projects: BatchProjectSummary[];
  scores: PairScore[];
  cached: boolean;
  computed_at?: string | null;
  note: string;
}
