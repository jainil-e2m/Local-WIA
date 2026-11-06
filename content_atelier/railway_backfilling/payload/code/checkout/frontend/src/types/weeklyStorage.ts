export interface StoredWeek { week_id: string; week_start: string; week_end: string; status: string; active_run_id: string | null }
export interface StoredAngle {
  can_approve?: boolean;
  angle_id: string; run_id: string; content_hash: string; moment_ids: string[];
  supersedes_id?: string | null; workflow?: string; has_replacement?: boolean;
  content_body: { title: string; argument: string; audience: string; tension: string; take: string; mechanism: string; reader_decision: string; qualifiers: string[]; risks: string[]; source_assertions: string[]; inference: string | null };
  base_score: number | null; adjusted_score: number | null; selection_status: string; approval_status: string;
  first_generated_at: string; selected_cta: { text?: string } | null;
  matching_result: { status: string; workflow?: string; max_historical_cosine?: number; history_count?: number; historical_risk?: number; current_batch_flags?: { angle_id: string; cosine: number }[]; partial_history_ids?: string[]; history?: { angle_id: string; title?: string; argument?: string; week_start?: string; approval_status?: string; cosine: number; age_days: number; risk: number }[] } | null;
}
export interface CandidateFamily { original_id: string; replacement_id: string | null; targeted: boolean; disposition: string; explanation: string }
export interface ComparisonScenario {
  cutoff: number; counts: Record<string, number>; selected_ids: string[];
  families: (CandidateFamily & { selected_id: string | null; original_reasons: string[]; replacement_reasons: string[] | null })[];
  current_batch_flags: Record<string, { angle_id: string; cosine: number }[]>;
}
export interface ComparisonReport { status: string; families: CandidateFamily[]; scenarios: ComparisonScenario[]; threshold_selection_pending: boolean }
export interface WeekReview {
  approval_cutoff?: number | null;
  week: StoredWeek; angles: StoredAngle[];
  comparisons?: { run_id: string; run_status: string; completion_state: string; report: ComparisonReport | null }[];
  runs: { run_id: string; status: string; current_message: string | null; error_summary: string | null; has_partial_failures: boolean }[];
  jobs: { job_id: string; run_id: string; stage: string; status: string; current_message: string | null; completed_units: number | null; total_units: number | null; attempt_count: number; error_summary: string | null; heartbeat_at: string | null; result_refs: { coverage_notes?: string[] } | null }[];
  events: { event_id: string; message: string; created_at: string; severity: string }[];
  transcripts: { transcript_id: string; title: string; source_url: string | null; occurred_at: string | null }[];
}
export interface MomentEvidence { moment: { moment_body: { quote: string; context_summary: string; qualifications: string[]; sensitivity: string } }; passages: { passage_id: string; text: string; title: string; speaker: string | null; start_ms: number | null; end_ms: number | null; roles: string[] }[] }
