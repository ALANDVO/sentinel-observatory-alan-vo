export interface SlideOut {
  id: string;
  position: number;
  slide_type: string;
  title: string | null;
  body_text: string | null;
  speaker_notes: string | null;
  chart_data?: Record<string, unknown> | null;
  table_data?: Record<string, unknown> | null;
}

export interface DeckOut {
  id: string;
  title: string;
  topic: string | null;
  source_type: string;
  status: string;
  slide_count: number;
  template_id?: string | null;
  created_at: string;
  slides: SlideOut[];
}

export interface DeckSummary {
  id: string;
  title: string;
  source_type: string;
  status: string;
  slide_count: number;
  created_at: string;
}

export interface DeckListResponse {
  total: number;
  items: DeckSummary[];
}

export interface TemplateOut {
  id: string;
  name: string;
  description: string | null;
  theme_color: string | null;
  slide_count: number;
  layout_names: string[];
  placeholder_map: Record<string, unknown>;
  is_builtin: string;
  created_at: string;
}

export interface TemplateListResponse {
  total: number;
  items: TemplateOut[];
}

export interface EvaluationOut {
  id: string;
  deck_id: string;
  eval_type: string;
  information_density_score: number | null;
  bullet_brevity_score: number | null;
  hierarchy_balance_score: number | null;
  readability_grade: number | null;
  mece_alignment_score: number | null;
  overall_cognitive_score: number | null;
  numeric_claims_found: number | null;
  claims_verified: number | null;
  data_fidelity_precision: number | null;
  data_fidelity_recall: number | null;
  attribution_pass: string | null;
  attribution_diagnostics: Array<{
    check_name: string;
    code: string;
    severity: string;
    message: string;
  }> | null;
  prompt_audit_pass: string | null;
  prompt_audit_findings: Array<Record<string, unknown>> | null;
  llm_advisory: string | null;
  llm_provider_used: string | null;
  raw_result: Record<string, unknown> | null;
  created_at: string;
}

export interface EvaluationListResponse {
  total: number;
  items: EvaluationOut[];
}

export interface UserInfo {
  sub: string;
  email: string | null;
  preferred_username: string | null;
  roles: string[];
  demo: boolean;
}

export interface OIDCConfig {
  issuer: string;
  client_id: string;
  authorization_endpoint: string;
  token_endpoint: string;
  jwks_uri: string;
  end_session_endpoint: string;
}

export interface SlideNarrationOut {
  slide_id: string;
  position: number;
  transcript: string;
  word_count: number;
  duration_seconds: number;
  words_per_minute?: number;
}

export interface DeckNarrationOut {
  deck_id: string;
  voice: string;
  words_per_minute?: number;
  total_duration_seconds: number;
  total_words: number;
  slides: SlideNarrationOut[];
}

