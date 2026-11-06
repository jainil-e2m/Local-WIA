export interface SavedSchedule {
  calendar_entry_id: string;
  asset_id: string;
  asset_content_hash: string;
  pack_id: string;
  pack_manifest_hash: string;
  scheduled_for: string;
  status: string;
  effective_status: string;
  revision: number;
  display_timezone: string;
  format: "email" | "carousel" | "reel";
  slot_key: string;
  title: string;
  pack_title: string;
  week_id: string;
  warnings: string[];
  overdue: boolean;
}
export interface StoredAsset {
  asset_id: string;
  slot_key: string;
  ordinal: number;
  asset_type: "email" | "carousel" | "reel";
  content_hash: string | null;
  content_body: { document: Record<string, any> } | null;
  schedule: Pick<
    SavedSchedule,
    | "calendar_entry_id"
    | "asset_id"
    | "asset_content_hash"
    | "pack_manifest_hash"
    | "scheduled_for"
    | "status"
    | "revision"
    | "display_timezone"
  >[];
}
export interface StoredPack {
  pack_id: string;
  title: string;
  week_id: string;
  source_brief_id: string;
  manifest_hash: string | null;
  approval_status: string;
  created_at: string;
  assets: StoredAsset[];
  blockers: string[];
  schedule_blockers: string[];
  can_approve: boolean;
  can_schedule: boolean;
  can_generate: boolean;
  validation_result?: { passed: boolean; review: { findings: string[] } };
}
export interface CalendarConfig {
  worker_ready?: boolean;
  enabled: boolean;
  display_timezone: string;
  server_time: string;
  can_schedule: boolean;
  packs_enabled: boolean;
  can_generate: boolean;
  live_generation_enabled: boolean;
}
export interface CalendarPage {
  items: SavedSchedule[];
  next_cursor: number | null;
  display_timezone: string;
  server_time: string;
}
