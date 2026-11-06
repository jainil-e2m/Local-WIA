import React, { useCallback, useEffect, useRef, useState } from "react";
import { StoredPack, StoredAsset, CalendarConfig } from "../types/production";
import { storageRequest } from "../utils/weeklyStorage";
import {
  civilFields,
  civilInstant,
  productionChanged,
  requestId,
} from "../utils/production";
import { useModalBehavior } from "./useModalBehavior";
import { BriefEvidence } from "../types/briefStorage";

const button =
  "rounded-full border border-[#D8DFE8] px-4 py-2 text-sm disabled:opacity-40 hover:bg-[#F4F6FA]";
export function SchedulePicker({
  pack,
  asset,
  zone,
  onSaved,
}: {
  pack: StoredPack;
  asset?: StoredAsset;
  zone: string;
  onSaved: () => Promise<void>;
}) {
  const [open, setOpen] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const initial = asset?.schedule[0]?.scheduled_for;
  const [date, setDate] = useState(
    initial ? civilFields(initial, zone).date : "",
  );
  const [time, setTime] = useState(
    initial ? civilFields(initial, zone).time : "09:00",
  );
  const receipt = useRef<{ body: string; id: string } | null>(null);
  const saving = useRef(false);
  const expected = useRef(pack);
  const [conflict, setConflict] = useState(false);
  return (
    <div className="space-y-3">
      <button
        className={button}
        disabled={!pack.can_schedule || busy}
        onClick={() => {
          if (!open) {
            expected.current = pack;
            setConflict(false);
          }
          setOpen((v) => !v);
        }}
      >
        {asset
          ? asset.schedule.length
            ? "Reschedule"
            : "Schedule this piece"
          : "Schedule all five pieces"}
      </button>
      {open && (
        <form
          className="rounded-xl border bg-[#F7F8FB] p-4 space-y-3"
          onSubmit={async (e) => {
            e.preventDefault();
            if (saving.current) return;
            saving.current = true;
            setBusy(true);
            setError("");
            try {
              const instant = civilInstant(date, time, zone);
              const snapshot = expected.current;
              const selected = asset
                ? snapshot.assets.filter((a) => a.asset_id === asset.asset_id)
                : snapshot.assets;
              const items = selected.map((a) => ({
                asset_id: a.asset_id,
                expected_asset_hash: a.content_hash,
                scheduled_for: instant,
                display_timezone: zone,
                ...(a.schedule[0]
                  ? {
                      entry_id: a.schedule[0].calendar_entry_id,
                      expected_revision: a.schedule[0].revision,
                    }
                  : {}),
              }));
              const payload = {
                expected_pack_manifest_hash: snapshot.manifest_hash,
                whole_pack: !asset,
                items,
              };
              const body = JSON.stringify(payload);
              if (receipt.current?.body !== body)
                receipt.current = { body, id: requestId() };
              await storageRequest(`/packs/${pack.pack_id}/schedule`, "POST", {
                ...payload,
                request_id: receipt.current.id,
              });
              productionChanged();
              setOpen(false);
              receipt.current = null;
              await onSaved();
            } catch (err) {
              setError((err as Error).message);
              if ((err as Error & { status?: number }).status === 409) {
                setConflict(true);
                await onSaved();
              }
            } finally {
              setBusy(false);
              saving.current = false;
            }
          }}
        >
          <p className="text-sm">
            {asset
              ? asset.content_body?.document.title
              : "All five pieces will share this publishing time. Existing dates will be replaced."}
          </p>
          <div className="flex gap-3 flex-wrap">
            <label>
              Date{" "}
              <input
                aria-label="Publishing date"
                type="date"
                required
                value={date}
                disabled={busy}
                onChange={(e) => setDate(e.target.value)}
                className="border rounded p-2 block"
              />
            </label>
            <label>
              Time{" "}
              <input
                aria-label="Publishing time"
                type="time"
                required
                value={time}
                disabled={busy}
                onChange={(e) => setTime(e.target.value)}
                className="border rounded p-2 block"
              />
            </label>
          </div>
          <p className="text-xs text-slate-500">
            {zone} · Saved publishing plan. Content is not automatically posted.
          </p>
          {error && (
            <p role="alert" className="text-red-700">
              {error}
            </p>
          )}
          {conflict && (
            <button
              type="button"
              className={button}
              onClick={() => {
                expected.current = pack;
                receipt.current = null;
                setConflict(false);
                setError(
                  "Current schedule loaded. Review your chosen time and confirm again.",
                );
              }}
            >
              Use refreshed schedule state
            </button>
          )}
          <button className={button} disabled={busy || conflict}>
            {busy ? "Saving…" : "Confirm schedule"}
          </button>
        </form>
      )}
    </div>
  );
}

function AssetCopy({ asset }: { asset: StoredAsset }) {
  const d = asset.content_body?.document;
  if (!d) return <p>Copy has not been generated.</p>;
  return (
    <div className="space-y-3">
      {d.subject && <h4 className="font-semibold">{d.subject}</h4>}
      {d.preview_text && (
        <p className="text-sm text-slate-500">{d.preview_text}</p>
      )}
      {d.body && <p className="whitespace-pre-wrap">{d.body}</p>}
      {d.spoken_script && (
        <p className="whitespace-pre-wrap">{d.spoken_script}</p>
      )}
      {d.slides?.map((s: any) => (
        <div key={s.number} className="rounded-xl border p-3">
          <h4>
            {s.number}. {s.headline}
          </h4>
          <p className="whitespace-pre-wrap">{s.body}</p>
          {s.direction && (
            <p className="text-sm text-slate-500">{s.direction}</p>
          )}
        </div>
      ))}
      {d.caption && (
        <div>
          <h4 className="font-medium">Caption</h4>
          <p className="whitespace-pre-wrap">{d.caption}</p>
        </div>
      )}
      {d.visual_directions?.length > 0 && (
        <details>
          <summary>Production directions</summary>
          <ul>
            {d.visual_directions.map((v: string, i: number) => (
              <li key={i}>{v}</li>
            ))}
          </ul>
        </details>
      )}
      <p className="text-sm">
        <strong>CTA:</strong> {d.cta?.text || JSON.stringify(d.cta)}
      </p>
      <details className="rounded-xl bg-slate-50 p-3 text-sm">
        <summary>Claims and source boundaries</summary>
        {d.claims?.map((claim: any, index: number) => (
          <div key={index} className="mt-3">
            <p>{claim.text}</p>
            <p>Approved claim references: {claim.brief_claim_ids.join(", ")}</p>
            {claim.qualifications.map((value: string) => (
              <p key={value}>{value}</p>
            ))}
          </div>
        ))}
        <p className="mt-3">
          Evidence references:{" "}
          {d.evidence_ids?.join(", ") ||
            "No factual evidence references supplied"}
        </p>
      </details>
    </div>
  );
}

export function StoredPackDetail({
  packId,
  assetId,
  onClose,
}: {
  packId: string;
  assetId?: string;
  onClose: () => void;
}) {
  const modal = useModalBehavior(onClose);
  const [pack, setPack] = useState<StoredPack | null>(null),
    [config, setConfig] = useState<CalendarConfig | null>(null);
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [reason, setReason] = useState("");
  const [jobs, setJobs] = useState<any[]>([]),
    [costs, setCosts] = useState<unknown>(null);
  const [reviewed, setReviewed] = useState(false);
  const [evidence, setEvidence] = useState<BriefEvidence[] | null>(null);
  const pendingCancel = useRef(new Map<string, string>());
  const pendingDecision = useRef<{ body: string; id: string } | null>(null);
  const load = useCallback(async () => {
    const [p, c, progress] = await Promise.all([
      storageRequest<StoredPack>(`/packs/${packId}`),
      storageRequest<CalendarConfig>("/calendar/config"),
      storageRequest<{ jobs: any[]; costs: unknown }>(
        `/packs/${packId}/production`,
      ),
    ]);
    setPack(p);
    setConfig(c);
    setJobs(progress.jobs);
    setCosts(progress.costs);
  }, [packId]);
  useEffect(() => {
    let alive = true;
    const tick = () =>
      load()
        .then(() => {
          if (alive) setError("");
        })
        .catch((e) => {
          if (alive) setError(e.message);
        });
    void tick();
    const timer = window.setInterval(tick, 15000);
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, [load]);
  const act = async (path: string, body: unknown) => {
    setBusy(true);
    setError("");
    try {
      await storageRequest(path, "POST", body);
      productionChanged();
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="atelier-modal-overlay fixed inset-0 z-50 flex justify-center items-center p-4">
      <section
        ref={modal}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-label="Saved content pack"
        className="atelier-modal w-full max-w-4xl max-h-[90dvh] overflow-y-auto bg-white rounded-2xl p-6 space-y-5"
      >
        <div className="flex justify-between gap-4">
          <h2 className="font-editorial text-3xl">
            {pack?.title || "Saved content pack"}
          </h2>
          <button className={button} onClick={onClose}>
            Close
          </button>
        </div>
        {error && (
          <p role="alert" className="bg-red-50 text-red-800 p-3">
            {error}
          </p>
        )}
        {!pack && !error && <p role="status">Loading saved content…</p>}
        {pack && (
          <>
            <details className="rounded-xl border p-4">
              <summary>Approved brief and source evidence</summary>
              <p className="mt-3 text-sm">
                Source brief: {pack.source_brief_id}
              </p>
              <button
                className={button}
                onClick={async () => {
                  try {
                    const row = await storageRequest<{
                      selected_evidence: BriefEvidence[];
                    }>(`/briefs/${pack.source_brief_id}`);
                    setEvidence(row.selected_evidence);
                  } catch (error) {
                    setError((error as Error).message);
                  }
                }}
              >
                Inspect source passages
              </button>
              {evidence?.map((item) => (
                <article
                  key={item.evidence_id}
                  className="mt-3 border-l-2 pl-3 text-sm"
                >
                  <p className="font-medium">
                    {item.title} · {item.passage_id}
                  </p>
                  <blockquote className="whitespace-pre-wrap">
                    {item.excerpt}
                  </blockquote>
                  {item.qualifications.map((value) => (
                    <p key={value}>{value}</p>
                  ))}
                  <p>
                    Public use {item.public_use ? "confirmed" : "unconfirmed"} ·
                    Attribution{" "}
                    {item.attribution_verified ? "confirmed" : "unverified"}
                  </p>
                </article>
              ))}
            </details>
            {pack.validation_result?.review?.findings?.length ? (
              <div className="rounded-xl bg-amber-50 p-3">
                {pack.validation_result.review.findings.map(
                  (finding, index) => (
                    <p key={index}>{finding}</p>
                  ),
                )}
              </div>
            ) : null}
            <p>
              {pack.approval_status} · {pack.week_id} ·{" "}
              {pack.assets.filter((a) => a.schedule.length).length}/
              {pack.assets.length} pieces scheduled
            </p>
            {!!pack.schedule_blockers.length && (
              <div className="bg-amber-50 p-3 rounded-xl">
                {pack.schedule_blockers.map((v, i) => (
                  <p key={i}>{v}</p>
                ))}
              </div>
            )}
            {pack.can_approve && (
              <div className="space-y-3 border rounded-xl p-4">
                <label className="flex gap-2">
                  <input
                    type="checkbox"
                    checked={reviewed}
                    onChange={(e) => setReviewed(e.target.checked)}
                  />
                  I reviewed all five assets, their claims, qualifications and
                  CTA.
                </label>
                <input
                  className="border p-2 rounded w-full"
                  aria-label="Pack review note"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder="Review or rejection reason"
                />
                <button
                  disabled={busy || !reviewed}
                  className={button}
                  onClick={() => {
                    const body = {
                      expected_manifest_hash: pack.manifest_hash,
                      decision: "approved",
                      note: reason || null,
                    };
                    const key = JSON.stringify(body);
                    if (pendingDecision.current?.body !== key)
                      pendingDecision.current = { body: key, id: requestId() };
                    void act(`/packs/${packId}/decision`, {
                      ...body,
                      request_id: pendingDecision.current.id,
                    });
                  }}
                >
                  Approve exact pack
                </button>
                <button
                  disabled={busy || !reason.trim()}
                  className={button}
                  onClick={() => {
                    const body = {
                      expected_manifest_hash: pack.manifest_hash,
                      decision: "rejected",
                      note: reason,
                    };
                    const key = JSON.stringify(body);
                    if (pendingDecision.current?.body !== key)
                      pendingDecision.current = { body: key, id: requestId() };
                    void act(`/packs/${packId}/decision`, {
                      ...body,
                      request_id: pendingDecision.current.id,
                    });
                  }}
                >
                  Reject pack
                </button>
              </div>
            )}
            <SchedulePicker
              pack={pack}
              zone={config?.display_timezone || "Asia/Kolkata"}
              onSaved={async () => {
                try {
                  await load();
                } catch (e) {
                  setError((e as Error).message);
                }
              }}
            />
            {jobs.length > 0 && (
              <details>
                <summary>Production processing</summary>
                {jobs.map((j) => (
                  <div key={j.job_id} className="p-2 text-sm">
                    {j.stage} · {j.status}
                    <p>{j.current_message || j.error_summary}</p>
                    {pack.can_generate &&
                      ["failed", "waiting"].includes(j.status) && (
                        <button
                          disabled={busy}
                          className={button}
                          onClick={() =>
                            void act(`/jobs/${j.job_id}/retry`, {})
                          }
                        >
                          Retry saved stage
                        </button>
                      )}
                  </div>
                ))}
                {costs != null && (
                  <pre className="text-xs whitespace-pre-wrap">
                    {JSON.stringify(costs, null, 2)}
                  </pre>
                )}
              </details>
            )}
            {pack.assets
              .filter((a) => !assetId || a.asset_id === assetId)
              .map((a) => (
                <article
                  key={a.asset_id}
                  className="border rounded-xl p-4 space-y-4"
                >
                  <h3 className="font-editorial text-2xl">
                    {a.content_body?.document.title || a.slot_key}
                  </h3>
                  <AssetCopy asset={a} />
                  {a.schedule.map((s) => (
                    <div
                      key={s.calendar_entry_id}
                      className="bg-blue-50 p-3 rounded-xl"
                    >
                      <p>
                        Scheduled:{" "}
                        {new Date(s.scheduled_for).toLocaleString("en-IN", {
                          timeZone: config?.display_timezone || "Asia/Kolkata",
                        })}
                      </p>
                      {config?.can_schedule && (
                        <button
                          className={button}
                          disabled={busy}
                          onClick={() => {
                            if (!pendingCancel.current.has(s.calendar_entry_id))
                              pendingCancel.current.set(
                                s.calendar_entry_id,
                                requestId(),
                              );
                            void act(
                              `/calendar/${s.calendar_entry_id}/cancel`,
                              {
                                request_id: pendingCancel.current.get(
                                  s.calendar_entry_id,
                                ),
                                expected_revision: s.revision,
                              },
                            );
                          }}
                        >
                          Cancel schedule
                        </button>
                      )}
                    </div>
                  ))}
                  <SchedulePicker
                    key={a.asset_id}
                    pack={pack}
                    asset={a}
                    zone={config?.display_timezone || "Asia/Kolkata"}
                    onSaved={async () => {
                      try {
                        await load();
                      } catch (e) {
                        setError((e as Error).message);
                      }
                    }}
                  />
                </article>
              ))}
            {assetId && !pack.assets.some((a) => a.asset_id === assetId) && (
              <p role="alert">
                This asset is unavailable in the selected pack.
              </p>
            )}
          </>
        )}
      </section>
    </div>
  );
}

export function StoredPacks({
  weekId,
  scheduledOnly = false,
}: {
  weekId?: string;
  scheduledOnly?: boolean;
}) {
  const [packs, setPacks] = useState<StoredPack[]>([]),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<{
    packId: string;
    assetId?: string;
  } | null>(null);
  const load = useCallback(async () => {
    try {
      const all: StoredPack[] = [];
      let total = 1;
      while (all.length < total) {
        const p = new URLSearchParams({
          limit: "100",
          offset: String(all.length),
          ...(weekId ? { week_id: weekId } : {}),
        });
        const page = await storageRequest<{
          items: StoredPack[];
          total: number;
        }>(`/packs?${p}`);
        all.push(...page.items);
        total = page.total;
        if (!page.items.length && all.length < total)
          throw new Error("Pack list is incomplete. Retry.");
      }
      setPacks(all);
      setError("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [weekId]);
  useEffect(() => {
    void load();
    const timer = window.setInterval(load, 30000);
    window.addEventListener("atelier-production-changed", load);
    window.addEventListener("focus", load);
    return () => {
      clearInterval(timer);
      window.removeEventListener("atelier-production-changed", load);
      window.removeEventListener("focus", load);
    };
  }, [load]);
  const assets = packs
    .flatMap((p) =>
      p.assets.flatMap((a) => a.schedule.map((s) => ({ p, a, s }))),
    )
    .sort((a, b) => a.s.scheduled_for.localeCompare(b.s.scheduled_for));
  return (
    <section className="space-y-5">
      <h1 className="font-editorial text-3xl">
        {scheduledOnly ? "Scheduled Content" : "Content Packs"}
      </h1>
      <p className="text-sm text-slate-500">
        Saved backend content ·{" "}
        {scheduledOnly
          ? `${assets.length} scheduled pieces`
          : `${packs.length} packs`}
      </p>
      {loading && <p role="status">Loading stored content…</p>}
      {error && (
        <div role="alert" className="bg-amber-50 p-4">
          {error}{" "}
          {packs.length > 0 && "Previously loaded content may be out of date."}
          <button className={button} onClick={() => void load()}>
            Retry
          </button>
        </div>
      )}
      {!loading &&
        !error &&
        !(scheduledOnly ? assets.length : packs.length) && (
          <p className="border border-dashed rounded-xl p-8">
            {scheduledOnly
              ? "No scheduled content. Approve a real pack and save a publishing date."
              : "No stored packs. Open an approved brief to generate a pack."}
          </p>
        )}
      <div className="grid md:grid-cols-2 gap-4">
        {scheduledOnly
          ? assets.map(({ p, a, s }) => (
              <button
                key={s.calendar_entry_id}
                className="border rounded-2xl bg-white p-5 text-left space-y-2"
                onClick={() =>
                  setSelected({ packId: p.pack_id, assetId: a.asset_id })
                }
              >
                <p className="text-sm">
                  {a.slot_key} · {p.week_id}
                </p>
                <h2 className="font-editorial text-2xl">
                  {a.content_body?.document.title}
                </h2>
                <p>
                  {new Date(s.scheduled_for).toLocaleString("en-IN", {
                    timeZone: s.display_timezone,
                  })}{" "}
                  · {s.display_timezone}
                </p>
                <p className="text-sm">
                  {p.schedule_blockers.length ? "Needs review" : "Scheduled"}
                </p>
              </button>
            ))
          : packs.map((p) => (
              <button
                key={p.pack_id}
                className="border rounded-2xl bg-white p-5 text-left space-y-2"
                onClick={() => setSelected({ packId: p.pack_id })}
              >
                <h2 className="font-editorial text-2xl">{p.title}</h2>
                <p>
                  {p.approval_status} ·{" "}
                  {p.assets.filter((a) => a.schedule.length).length}/
                  {p.assets.length} scheduled
                </p>
                <p className="text-sm">{p.week_id}</p>
              </button>
            ))}
      </div>
      {selected && (
        <StoredPackDetail {...selected} onClose={() => setSelected(null)} />
      )}
    </section>
  );
}
