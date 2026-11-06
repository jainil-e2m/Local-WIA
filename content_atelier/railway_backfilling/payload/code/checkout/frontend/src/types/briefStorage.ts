export interface BriefEvidence {
  evidence_id: string; excerpt: string; title: string; transcript_id: string | null; passage_id: string | null;
  start: number | null; end: number | null; start_ms: number | null; speaker: string | null; source_url: string | null;
  role: string; qualifications: string[]; claim_status: string; sensitivity: string; public_use: boolean; attribution_verified: boolean;
}
export interface BriefNumericFact { value: string; unit: string; timeframe: string; subject: string; evidence_id: string; source_quote: string }
export interface BriefClaim { claim_id: string; text: string; kind: string; evidence_ids: string[]; source_status: string; qualifications: string[]; quote: string | null; public_quote: boolean; numeric_facts: BriefNumericFact[] }
export interface BriefFormat { reader_job: string; direction: string; outline: string[]; evidence_ids: string[] }
export interface BriefDocument {
  title: string; angle_statement: string; audience: string; reader_decision: string; reader_promise: string;
  positioning: string | null; why_now: string; core_insight: string; message_spine: string[]; audience_pain: string;
  narrative: string[]; evidence_boundaries: string[]; claims: BriefClaim[]; differentiation: string; prior_differences: Record<string,string>;
  voice: string[]; email: BriefFormat; carousel_reader_job: string; carousel: { number: number; direction: string; evidence_ids: string[] }[];
  reels: BriefFormat[]; cta: { text: string }; creative_direction: string[]; accessibility: string[]; distribution: string[];
  evaluation_signals: string[]; similarity_review: string; claims_requiring_consent: string[];
  open_questions: { question_id: string; text: string; required: boolean; answer: string | null }[]; sources: string[]; handoff_checklist: string[];
}
export interface StoredBrief {
  brief_id: string; week_id: string; angle_id: string; content_hash: string; approval_status: string; can_approve: boolean; can_edit: boolean; can_review: boolean; can_consume: boolean; has_replacement: boolean;
  blockers: string[]; selected_evidence: BriefEvidence[]; content_body: { document: BriefDocument; review: { locked_fields: string[]; findings: {severity:string; message:string}[]; clearances: Record<string,unknown> } };
  prior_content_context: { angle_id: string; argument: string; approval_status: string; cosine: number | null; briefs: {brief_id:string;approval_status:string}[]; publications: {status:string}[] }[];
  research_gaps: {items: string[]; coverage: Record<string,unknown>};
}
export interface BriefResearch {
  status: string; run_id?: string; jobs: { job_id: string; stage: string; status: string; current_message: string | null; error_summary: string | null; completed_units: number | null; total_units: number | null }[];
  dossier: { evidence: BriefEvidence[]; gaps: string[]; coverage: Record<string,unknown> } | null;
}
