/* The API's types, all generated from backend/openapi.json (schema.d.ts). Nothing here describes a shape by hand: each
   line gives a screen's name to a generated type, or picks a part of one. */
export type * from './schema';
export type { StrategistCard as Card } from './schema';

import type { Changes, ContextItem, Entry, ItemDecision, BatchDecision, StoredBriefV1, StoredBriefV2, StoredBriefV3, StoredBriefV4 } from './schema';

/** A brief of any contract version; `schema_version` tells them apart. */
export type StoredBrief = StoredBriefV1 | StoredBriefV2 | StoredBriefV3 | StoredBriefV4;

/* The context system (Phase L). */
export type ItemKind = ContextItem['kind'];
export type ItemStatus = ContextItem['status'];
export type Visibility = ContextItem['visibility'];
export type Permission = NonNullable<ContextItem['permission']>;
export type Sensitivity = NonNullable<Changes['sensitivity']>;
export type DecisionAction = ItemDecision['action'];
export type DecisionBody = ItemDecision;
export type BatchBody = BatchDecision;
export type ItemChanges = Changes;
export type EntryBody = Entry;
