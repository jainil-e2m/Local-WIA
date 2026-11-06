import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useSearchParams } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, Download, Lock, RotateCcw, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ComboboxField } from "@/components/ui/field-menu";
import { useLocationSuggestions } from "@/hooks/useLocationSuggestions";
import { AiAssistantPicker } from "@/components/intake/AiAssistantPicker";
import { CompetitorRepeater } from "@/components/intake/CompetitorRepeater";
import { ProfileRepeater } from "@/components/intake/ProfileRepeater";
import { inputClass, labelClass, RequiredMark } from "@/components/intake/fields";
import {
  filledCompetitorRows,
  filledProfileRows,
  hasCompetitorErrors,
  hasProfileErrors,
  markCompetitorRowsTouched,
  markProfileRowsTouched,
  type CompetitorRow,
  type ProfileRow,
} from "@/components/intake/rows";
import { QueryReview } from "@/components/review/QueryReview";
import { useAuditRun } from "@/hooks/useAuditRun";
import { useQueryReview } from "@/hooks/useQueryReview";
import { clientPdfDownloadUrl, type AuditType } from "@/services/api/audits";
import {
  DEFAULT_AI_ASSISTANTS,
  INTAKE_PROFILES,
  looksLikeRealEstate,
  REAL_ESTATE_PLATFORMS,
  SOCIAL_PLATFORMS,
} from "@/data/auditIntake";
import type { Tool } from "@/data/tools";

const fade = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -16 },
  transition: { duration: 0.35 },
};

/**
 * Inline audit runner: intake form → SSE-tracked progress → done. Which fields the
 * form collects is decided by the product's entry in `INTAKE_PROFILES`, not by
 * conditionals scattered through the markup. Locked (form disabled) while the tool
 * is in development.
 */
export function AuditPanel({ tool, auditType }: { tool: Tool; auditType: AuditType }) {
  const locked = tool.status !== "live";
  const { phase, percent, stage, business, auditId, detail, run, resume, refresh, reset } =
    useAuditRun(auditType);
  const intake = INTAKE_PROFILES[auditType];

  /* ── Addressing a run ──────────────────────────────────────────────────
     A run's id lives in the URL, not just in this component's state. That is
     what lets someone leave a run parked on its query review, come back later
     — or arrive from History — and pick up the same run. */
  const [searchParams, setSearchParams] = useSearchParams();
  const runParam = searchParams.get("run");

  useEffect(() => {
    if (!runParam || runParam === auditId) return;
    void resume(runParam);
  }, [runParam, auditId, resume]);

  /** Publish the id so a refresh, a copied link or a back-navigation still finds it. */
  useEffect(() => {
    if (!auditId || auditId === runParam) return;
    setSearchParams((params) => {
      params.set("run", auditId);
      return params;
    });
  }, [auditId, runParam, setSearchParams]);

  const review = useQueryReview({
    auditId,
    active: phase === "awaiting_review",
    onConfirmed: (id) => void refresh(id),
  });

  /**
   * Who this run is for. A run started in this session has it from the intake
   * form; one resumed by id has to read it off the persisted detail, because the
   * person confirming the queries may never have filled that form in.
   */
  const runBusiness =
    business ??
    (detail
      ? { name: detail.business_name?.trim() || "Audit in progress", url: detail.domain ?? "" }
      : null);

  const startOver = () => {
    setSearchParams((params) => {
      params.delete("run");
      return params;
    });
    reset();
  };

  const [name, setName] = useState("");
  const [url, setUrl] = useState("");

  // Business identity. AI SEO uses it for the Knowledge Graph entity lookup and
  // YouTube grounding; AI Presence uses it to localise every assistant prompt.
  const [country, setCountry] = useState("");
  const [stateRegion, setStateRegion] = useState("");
  const [city, setCity] = useState("");
  const [businessType, setBusinessType] = useState("");
  const [socialRows, setSocialRows] = useState<ProfileRow[]>([]);

  // AI Presence only.
  const [targetKeyword, setTargetKeyword] = useState("");
  const [competitorRows, setCompetitorRows] = useState<CompetitorRow[]>([]);
  const [realEstateRows, setRealEstateRows] = useState<ProfileRow[]>([]);
  const [assistants, setAssistants] = useState<string[]>(DEFAULT_AI_ASSISTANTS);
  const [assistantsInvalid, setAssistantsInvalid] = useState(false);

  /**
   * The real-estate profile fields are worth asking about only for a real-estate
   * business, and the business type is free text — so this reads the typed value
   * rather than a category the form never asked for.
   */
  const showRealEstate = intake.presence && looksLikeRealEstate(businessType);

  /* ── Location autosuggest ──────────────────────────────────────────────
     Suggestions narrow as the form is filled: states are scoped to a
     recognised country, cities to a recognised state. Typed text is always
     kept — the dataset does not know every place, and an unlisted one must
     still be auditable, which is also why these are comboboxes and not
     dropdowns. */

  const { countryMatch, stateMatch, countrySuggestions, stateSuggestions, citySuggestions } =
    useLocationSuggestions({ country, state: stateRegion, city });

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (locked) return;
    const trimmedName = name.trim();
    const trimmedUrl = url.trim();
    if (!trimmedName || !trimmedUrl) return;
    const normalizedUrl = /^https?:\/\//i.test(trimmedUrl) ? trimmedUrl : `https://${trimmedUrl}`;

    if (!intake.identity) {
      run(trimmedName, normalizedUrl);
      return;
    }

    const trimmedCountry = country.trim();
    const trimmedState = stateRegion.trim();
    const trimmedCity = city.trim();
    const trimmedBusinessType = businessType.trim();
    if (!trimmedCountry || !trimmedState || !trimmedBusinessType) return;
    // AI Presence builds every assistant prompt around "city, state, country", so
    // its API refuses a blank city. AI SEO does the opposite — see below.
    if (intake.cityRequired && !trimmedCity) return;

    if (!intake.presence) {
      // Blank rows are dropped rather than treated as errors — adding a row and
      // changing your mind should not block the audit.
      if (hasProfileErrors(SOCIAL_PLATFORMS, socialRows)) {
        setSocialRows(markProfileRowsTouched(socialRows));
        return;
      }
      run(trimmedName, normalizedUrl, {
        country: trimmedCountry,
        state: trimmedState,
        // Omit rather than send "" — the backend treats an absent city as "no city
        // known" and drops it from the Knowledge Graph query, whereas a blank
        // string would have to be padded and could skew that lookup.
        city: trimmedCity || undefined,
        businessType: trimmedBusinessType,
        socialProfiles: filledProfileRows(socialRows).map((row) => ({
          platform: row.platform,
          url: row.url.trim(),
        })),
      });
      return;
    }

    if (showRealEstate && hasProfileErrors(REAL_ESTATE_PLATFORMS, realEstateRows)) {
      setRealEstateRows(markProfileRowsTouched(realEstateRows));
      return;
    }
    if (hasCompetitorErrors(competitorRows)) {
      setCompetitorRows(markCompetitorRowsTouched(competitorRows));
      return;
    }
    if (!assistants.length) {
      setAssistantsInvalid(true);
      return;
    }

    // Each real-estate platform is its own top-level key rather than a list entry.
    const realEstateProfiles: Record<string, string> = {};
    if (showRealEstate) {
      for (const row of filledProfileRows(realEstateRows)) {
        const option = REAL_ESTATE_PLATFORMS.find((entry) => entry.id === row.platform);
        if (option) realEstateProfiles[option.payloadKey] = row.url.trim();
      }
    }

    run(trimmedName, normalizedUrl, {
      country: trimmedCountry,
      state: trimmedState,
      city: trimmedCity,
      businessType: trimmedBusinessType,
      aiAssistants: assistants,
      targetKeywords: targetKeyword.trim() ? [targetKeyword.trim()] : [],
      competitors: filledCompetitorRows(competitorRows).map((row) => ({
        brandName: row.brandName.trim(),
        domainUrl: row.domainUrl.trim(),
      })),
      realEstateProfiles,
    });
  };

  return (
    <div className="w-full px-6 py-14 sm:px-10">
      <AnimatePresence mode="wait">
        {/* The intake carries no heading of its own: the tool's <h1> sits directly
            above this panel on the page, so a "Run a <tool> audit" line only
            repeats it. The form is named via aria-label instead. */}
        {phase === "idle" && (
          <motion.form
            key="intake"
            {...fade}
            onSubmit={submit}
            aria-label={`Run a ${tool.name} audit`}
            className="mx-auto max-w-xl"
          >
            <div className="space-y-5">
              <div>
                <label htmlFor={`${tool.id}-business-name`} className={labelClass}>
                  Business Name
                  <RequiredMark />
                </label>
                <input
                  id={`${tool.id}-business-name`}
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Wahha Design"
                  required
                  disabled={locked}
                  className={inputClass}
                />
              </div>
              <div>
                <label htmlFor={`${tool.id}-business-url`} className={labelClass}>
                  Business URL
                  <RequiredMark />
                </label>
                <input
                  id={`${tool.id}-business-url`}
                  type="text"
                  inputMode="url"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="wahhadesign.com"
                  required
                  disabled={locked}
                  className={inputClass}
                />
              </div>

              {intake.identity && (
                <>
                  <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
                    <div>
                      <label htmlFor={`${tool.id}-country`} className={labelClass}>
                        Country
                        <RequiredMark />
                      </label>
                      <ComboboxField
                        id={`${tool.id}-country`}
                        value={country}
                        suggestions={countrySuggestions}
                        onChange={(next) => {
                          setCountry(next);
                          // A different country invalidates whatever state and
                          // city were chosen under the previous one.
                          setStateRegion("");
                          setCity("");
                        }}
                        onSelect={(suggestion) => {
                          setCountry(suggestion.value);
                          setStateRegion("");
                          setCity("");
                        }}
                        placeholder="United States"
                        required
                        disabled={locked}
                      />
                    </div>
                    <div>
                      <label htmlFor={`${tool.id}-state`} className={labelClass}>
                        State / Region
                        <RequiredMark />
                      </label>
                      <ComboboxField
                        id={`${tool.id}-state`}
                        value={stateRegion}
                        suggestions={stateSuggestions}
                        onChange={(next) => {
                          setStateRegion(next);
                          setCity("");
                        }}
                        onSelect={(suggestion) => {
                          setStateRegion(suggestion.value);
                          setCity("");
                        }}
                        placeholder="Texas"
                        required
                        disabled={locked}
                        emptyHint={
                          countryMatch
                            ? "No match — you can still type it in."
                            : "Pick a country first for suggestions."
                        }
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
                    <div>
                      <label htmlFor={`${tool.id}-city`} className={labelClass}>
                        City
                        {intake.cityRequired ? (
                          <RequiredMark />
                        ) : (
                          <span className="text-white/30"> (optional)</span>
                        )}
                      </label>
                      <ComboboxField
                        id={`${tool.id}-city`}
                        value={city}
                        suggestions={citySuggestions}
                        onChange={setCity}
                        onSelect={(suggestion) => {
                          setCity(suggestion.value);
                          // A city implies its state. Written directly rather than
                          // through the state field's own handler, which clears the
                          // city — that would erase the selection being made.
                          const impliedState = suggestion.data?.state;
                          if (impliedState) setStateRegion(impliedState);
                        }}
                        placeholder="Austin"
                        required={intake.cityRequired}
                        disabled={locked}
                        emptyHint={
                          countryMatch
                            ? "No match — you can still type it in."
                            : "Pick a country first for suggestions."
                        }
                      />
                    </div>
                    <div>
                      <label htmlFor={`${tool.id}-business-type`} className={labelClass}>
                        Business Type
                        <RequiredMark />
                      </label>
                      <input
                        id={`${tool.id}-business-type`}
                        type="text"
                        value={businessType}
                        onChange={(e) => setBusinessType(e.target.value)}
                        placeholder="Marketing Agency"
                        required
                        disabled={locked}
                        className={inputClass}
                      />
                    </div>
                  </div>

                  {intake.presence && (
                    <div>
                      <label htmlFor={`${tool.id}-target-keyword`} className={labelClass}>
                        Target Keyword <span className="text-white/30">(optional)</span>
                      </label>
                      <input
                        id={`${tool.id}-target-keyword`}
                        type="text"
                        value={targetKeyword}
                        onChange={(e) => setTargetKeyword(e.target.value)}
                        placeholder="best marketing agency in Austin"
                        disabled={locked}
                        className={inputClass}
                      />
                    </div>
                  )}

                  {intake.presence && (
                    <CompetitorRepeater
                      idPrefix={`${tool.id}-competitor`}
                      rows={competitorRows}
                      onRowsChange={setCompetitorRows}
                      disabled={locked}
                    />
                  )}

                  {intake.socialProfiles && (
                    <ProfileRepeater
                      idPrefix={`${tool.id}-social`}
                      noun="Social"
                      legend="Social Profiles"
                      options={SOCIAL_PLATFORMS}
                      rows={socialRows}
                      onRowsChange={setSocialRows}
                      disabled={locked}
                    />
                  )}

                  {showRealEstate && (
                    <ProfileRepeater
                      idPrefix={`${tool.id}-real-estate`}
                      noun="Real estate"
                      legend="Real Estate Platforms"
                      options={REAL_ESTATE_PLATFORMS}
                      rows={realEstateRows}
                      onRowsChange={setRealEstateRows}
                      disabled={locked}
                    />
                  )}

                  {intake.presence && (
                    <AiAssistantPicker
                      idPrefix={tool.id}
                      selected={assistants}
                      onChange={(next) => {
                        setAssistants(next);
                        if (next.length) setAssistantsInvalid(false);
                      }}
                      disabled={locked}
                      invalid={assistantsInvalid}
                    />
                  )}
                </>
              )}
            </div>

            <div className="mt-8 flex flex-col items-center gap-3">
              <Button type="submit" variant={locked ? "locked" : "primary"} disabled={locked}>
                Run Audit
                {locked && <Lock className="h-4 w-4" />}
              </Button>
              {locked && (
                <p className="text-sm text-white/50">Your E2M team is building this right now.</p>
              )}
            </div>
          </motion.form>
        )}

        {phase === "running" && runBusiness && (
          <motion.div key="progress" {...fade} className="mx-auto max-w-xl text-center">
            <span className="inline-flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.2em] text-brand-teal">
              <span
                className="h-1.5 w-1.5 rounded-full bg-brand-teal animate-pulse-ring"
                aria-hidden
              />
              Audit in progress
            </span>
            <h2 className="mt-4 text-3xl font-extrabold tracking-tight">{runBusiness.name}</h2>
            <p className="mt-1.5 text-[15px] text-white/55">{runBusiness.url}</p>

            <div
              className="mt-9 h-2.5 w-full overflow-hidden rounded-full bg-white/10"
              role="progressbar"
              aria-valuenow={percent}
              aria-valuemin={0}
              aria-valuemax={100}
            >
              <motion.div
                className="h-full rounded-full"
                style={{ background: "linear-gradient(90deg, #f69d2f, #48c7b1)" }}
                animate={{ width: `${percent}%` }}
                transition={{ ease: "easeOut", duration: 0.3 }}
              />
            </div>
            <div className="mt-3 flex items-center justify-between text-sm">
              <span className="text-white/60">{stage}</span>
              <span className="font-bold text-white/85">{percent}%</span>
            </div>

            {/* The stage line above comes from the service. This line answers the
                question it raises — "how long am I sitting here?" — and it is
                accurate rather than aspirational: the run id is in the URL, so
                closing the tab and reopening the link resumes this same run. */}
            <p className="mt-8 text-xs text-white/35">
              A full audit takes several minutes. You can close this tab — the run keeps going, and
              this link brings you back to it.
            </p>
          </motion.div>
        )}

        {phase === "awaiting_review" && auditId && (
          <motion.div key="review" {...fade}>
            <QueryReview
              sections={review.sections}
              total={review.total}
              fetchStatus={review.fetchStatus}
              error={review.error}
              confirming={review.confirming}
              onRetry={review.retry}
              onAddQuery={review.addQuery}
              onUpdateQueryText={review.updateQueryText}
              onRemoveQuery={review.removeQuery}
              onConfirm={review.confirm}
            />
          </motion.div>
        )}

        {(phase === "completed" || phase === "partial") && runBusiness && auditId && (
          <motion.div key="complete" {...fade} className="mx-auto max-w-xl text-center">
            {/* A partial run is presented as the success it is. Every product here
                reports partial completion for outcomes that are routine rather than
                wrong — a bounded crawl finishing at its cap, one external data
                source declining, a check with no applicable population. On-Page
                reports it on essentially every run, so an alert icon and a warning
                line fired on all of them, which trained the reader to ignore both.
                The distinction is not lost: History still filters and labels
                Partial, and the report itself carries the coverage disclosure. */}
            <CheckCircle2 className="mx-auto h-12 w-12 text-brand-teal" aria-hidden />
            <h2 className="mt-4 text-3xl font-extrabold tracking-tight">Audit complete</h2>
            <p className="mt-2 text-[15px] text-white/55">
              {runBusiness.name} · {runBusiness.url}
            </p>
            <div className="mt-8 flex flex-wrap justify-center gap-3">
              {clientPdfDownloadUrl(detail) && (
                <a
                  href={clientPdfDownloadUrl(detail)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/[0.07] px-5 py-3 text-[12px] font-bold uppercase tracking-[0.12em] text-white/85 transition-colors hover:bg-white/[0.15]"
                >
                  <Download className="h-4 w-4" />
                  Download PDF
                </a>
              )}
            </div>
            <Button variant="ghost" size="sm" onClick={startOver} className="mt-6">
              <RotateCcw className="h-4 w-4" />
              Run another audit
            </Button>
          </motion.div>
        )}

        {(phase === "failed" || phase === "error") && (
          <motion.div key="error" {...fade} className="mx-auto max-w-xl text-center">
            <XCircle className="mx-auto h-12 w-12 text-red-300" aria-hidden />
            <h2 className="mt-4 text-2xl font-extrabold tracking-tight">
              {phase === "failed" ? "Audit failed" : "Something went wrong"}
            </h2>
            <p className="mt-2 text-[15px] text-white/55">
              {detail?.failure_reason ||
                (phase === "failed"
                  ? "The audit ended before a complete report could be produced."
                  : "We could not start the audit. Give it another go.")}
            </p>
            <div className="mt-8 flex flex-wrap justify-center gap-3">
              <Button variant="ghost" size="sm" onClick={startOver}>
                <RotateCcw className="h-4 w-4" />
                Run another audit
              </Button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
