from __future__ import annotations

import json
import uuid
from collections.abc import Callable

import httpx

from .angle_profiles import (
    BRIEF_PROFILES,
    IDENTITY_PROFILES,
    demote_internal_cards,
    card_reference_problems,
    tidy_non_card_references,
    conversation_problems,
    demote_same_conversation,
    order_packet,
    card_contract,
    card_schema,
    repair_user,
    resolve_card_references,
    scene_references,
    strategist_angle_prompt,
    uses_cards,
    uses_scene_references,
)
from .card_contracts import WeeklyAngleCards, WeeklyAngleCardsV5, WeeklyAngleCardsV7, card_point, is_card_response
from .config import Settings
from .contracts import AngleResponse, MomentResponse, signature_from_fields
from .knowledge_base import KnowledgeBase
from .ingest import discover_week
from .models import Angle, Moment, Quality, RunManifest, StageArtifact
from .prompts import PROMPT_VERSION, angle_prompt, moment_prompt, weekly_moment_prompt
from .llm import FakeProvider, LlmRuns, ModelProvider, RoutingError, StageCaller, live_provider
from .scoring import rank
from .store import JsonStore, canonical_hash
from .strategy_contracts import (
    StrategicAngleResponse,
    StrategicCompactMomentResponse,
    StrategicMomentResponse,
    StrategicRefinementResponse,
    is_strategic_angle_response,
    is_strategic_moment_response,
)
from .weekly import LIVE_COMPACT_VERSION, load_compact_week, meeting_inventory


def uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


# Failures of the verifier's model pass that leave the week its deterministic ledgers (plan 4.11).
MODEL_PASS_UNAVAILABLE = (httpx.HTTPError, RoutingError, ValueError, TypeError, KeyError)


class Pipeline:
    def __init__(self, settings: Settings, provider: ModelProvider | None = None, *, runs: LlmRuns | None = None):
        self.settings = settings
        self.store = JsonStore(settings.data_root)
        self._provider_override = provider
        self.provider: ModelProvider = provider or FakeProvider(dimensions=settings.embedding_dimensions)
        # Every model call goes through the llm module (0.B4): request, cache, dispatch, cost, validation, one repair, and
        # an llm_runs row. The file runner records to a file beside its artifacts; the SQL worker passes the database's.
        self.runs = runs if runs is not None else LlmRuns(file=settings.data_root / "llm_runs.jsonl")
        self.calls = StageCaller(self, self.runs)
        self._kb_versions: dict[str, str] = {}
        self._compact_refs: dict[str, str] = {}
        self._packet_prefix: str | None = None
        self._knowledge_base: KnowledgeBase | None = None
        # The context-assembly service's database (L.B5): the SQL worker sets a connection factory and the run date;
        # the file-backed runner leaves both unset and uses the file knowledge base.
        self.context_connection = None
        self.context_date = None
        # The window's strategy brief for strategist v7 (E.B28): frozen with the SQL run, assembled at run start here.
        self._strategy_brief: dict | None = None

    def _select_provider(self, mode: str) -> None:
        if mode == "live":
            if not self.settings.live_enabled:
                raise RuntimeError("Live mode requires CONTENT_ATELIER_LIVE=true")
            self.settings.validate_live()
        if self._provider_override is not None:
            self.provider = self._provider_override
        elif mode != "live":
            self.provider = FakeProvider(dimensions=self.settings.embedding_dimensions)
        else:
            self.provider = live_provider(self.settings, on_response=self.calls.save_raw_response, runs=self.runs)

    def knowledge_base(self, mode: str) -> KnowledgeBase | None:
        """Load the knowledge base when the selected angle profile needs one; placeholders only for fake runs."""
        if not uses_cards(self.settings.angle_prompt_profile):
            return None
        return self.context("strategist", mode)

    def context(self, stage: str, mode: str):
        """One stage's context from the assembly service (L.B5)."""
        from .knowledge import held_out
        from .knowledge.assembly import assemble
        kb = assemble(stage, root=self.settings.knowledge_base_root, connection=self.context_connection,
                      on=self.context_date, allow_placeholders=mode == "fake")
        if mode == "live":
            held_out.check_live(kb.text)
        self._kb_versions[stage] = kb.refs().get("version")
        return kb

    # The context stage each call stage reads, for the llm_runs record (0.B4).
    CONTEXT_OF_STAGE = {"angle_generation": "strategist", "angle_refinement": "strategist", "card_verification": "verifier",
                        "moment_extraction": "extraction"}

    def kb_version_for(self, stage: str) -> str | None:
        return self._kb_versions.get(self.CONTEXT_OF_STAGE.get(stage, stage))

    def angle_input_refs(self, knowledge_base: KnowledgeBase | None) -> dict | None:
        if knowledge_base is None:
            return None
        return {"angle_prompt_profile": self.settings.angle_prompt_profile,
                "angle_model": self.settings.model_for("angle_generation"),
                "knowledge_base": knowledge_base.refs()}

    # The stage-call engine lives in the llm module; these keep the names the SQL worker, scripts and experiments use.
    @property
    def _attempt_paths(self):
        return self.calls.attempt_paths

    @property
    def _cost_context(self):
        return self.calls.cost_context

    @property
    def _dispatched(self):
        return self.calls.dispatched

    def _save_raw_response(self, fingerprint: str, raw: dict) -> None:
        self.calls.save_raw_response(fingerprint, raw)

    def _record_cost(self, fingerprint: str, *, raw: dict | None = None, validation_status: str) -> None:
        self.calls.record_cost(fingerprint, raw=raw, validation_status=validation_status)

    def load_week(self, week_index: int):
        self._compact_refs, self._packet_prefix = {}, None
        if self.settings.llm_payload_format == "compact_weekly":
            transcripts, source_packet, self._compact_refs, self._packet_prefix = load_compact_week(
                self.settings.transcript_root, week_index, self.store
            )
        else:
            transcripts = discover_week(self.settings.transcript_root, week_index)
            source_packet = [span.model_dump(mode="json") for transcript in transcripts for span in transcript.spans]
        for transcript in transcripts:
            # Same raw bytes may previously have been stored with the legacy
            # representation. Keep the lossless source view in its own namespace.
            source_area = "sources/compact_weekly" if self._compact_refs else "sources"
            self.store.write_json(
                f"{source_area}/week{week_index}/{transcript.source_id.replace(':', '_')}/{transcript.content_hash}.json",
                transcript.model_dump(mode="json"),
            )
        snapshot = {"transcripts": [t.model_dump(mode="json") for t in transcripts]}
        snapshot_hash = canonical_hash(snapshot)
        self.store.write_json(f"cycles/week{week_index}/snapshots/{snapshot_hash}.json", snapshot)
        self.store.write_json(f"cycles/week{week_index}/sources.json", snapshot, overwrite=True)
        return transcripts, source_packet

    def plan(self, week_index: int, mode: str = "plan") -> RunManifest:
        knowledge_base = self.knowledge_base(mode)
        transcripts, _ = self.load_week(week_index)
        run = RunManifest(
            run_id=uid("run"),
            week_index=week_index,
            source_root=str(self.settings.transcript_root),
            source_ids=[t.source_id for t in transcripts],
            prompt_profile=LIVE_COMPACT_VERSION if self._compact_refs else PROMPT_VERSION,
            model_id=self.settings.model_for("angle_generation"),
            embedding_profile=f"{self.settings.embedding_model}:{self.settings.embedding_dimensions}",
            mode=mode,
            execution_scope="full" if self.settings.embeddings_enabled else "generation_only",
            input_refs=self.angle_input_refs(knowledge_base),
        )
        self.store.write_model(f"experiments/default/runs/{run.run_id}/manifest.json", run)
        return run

    def run(self, week_index: int, *, mode: str = "fake", run_id: str | None = None) -> dict:
        if mode == "plan":
            return self.plan(week_index).model_dump(mode="json")
        if mode not in {"fake", "live", "replay"}:
            raise ValueError("mode must be plan, fake, live or replay")
        if uses_cards(self.settings.angle_prompt_profile) and self.settings.embeddings_enabled:
            raise ValueError("The strategist card profile has no self-scores to rank; run it generation-only")
        from .angle_profiles import check_live_profile
        check_live_profile(self.settings.angle_prompt_profile, mode)
        self._select_provider(mode)
        # Load before any model call: a missing or placeholder knowledge base must not cost an extraction.
        knowledge_base = self._knowledge_base = self.knowledge_base(mode)
        transcripts, source_packet = self.load_week(week_index)
        refs = self.angle_input_refs(knowledge_base)
        if knowledge_base is not None and self.settings.angle_prompt_profile in BRIEF_PROFILES:
            # Strategist v7 reads the window's strategy brief (E.B28); the file runner assembles it from the same knowledge base.
            from datetime import date

            from .cycle import strategy_brief
            self._strategy_brief = strategy_brief.assemble(knowledge_base, root=self.settings.knowledge_base_root,
                                                           on=self.context_date or date.today())
            refs = {**refs, "strategy_brief": self._strategy_brief}
        run = RunManifest(
            run_id=run_id or uid("run"),
            week_index=week_index,
            source_root=str(self.settings.transcript_root),
            source_ids=[t.source_id for t in transcripts],
            prompt_profile=LIVE_COMPACT_VERSION if self._compact_refs else PROMPT_VERSION,
            model_id=self.settings.model_for("angle_generation"),
            embedding_profile=f"{self.settings.embedding_model}:{self.settings.embedding_dimensions}",
            mode=mode,
            execution_scope="full" if self.settings.embeddings_enabled else "generation_only",
            input_refs=refs,
        )
        run_dir = f"experiments/default/runs/{run.run_id}"
        if self.store.path(f"{run_dir}/manifest.json").exists():
            raise ValueError("Run ID already exists; use a new report run to preserve original artifacts")
        self.store.write_model(f"{run_dir}/manifest.json", run)
        try:
            result = self._execute(run, run_dir, transcripts, source_packet)
        except Exception:
            run.status = "failed"
            self.store.write_model(f"{run_dir}/manifest.json", run, overwrite=True)
            raise
        run.status = "completed" if self.settings.embeddings_enabled else "generation_completed"
        self.store.write_model(f"{run_dir}/manifest.json", run, overwrite=True)
        return result

    def _execute(self, run: RunManifest, run_dir: str, transcripts, source_packet: list[dict] | str) -> dict:
        if isinstance(source_packet, str):
            system, user = weekly_moment_prompt(source_packet, meeting_inventory(self._compact_refs))
            self.store.write_json(f"{run_dir}/weekly_packet.json", {"artifact_directory": self._packet_prefix})
        else:
            system, user = moment_prompt(source_packet)
        source_identity = [{"source_id": t.source_id, "revision": t.content_hash} for t in transcripts]
        moment_input_hash = canonical_hash({"system": system, "user": user, "source": source_identity})
        moment_artifact = self._call_json(
            "moment_extraction",
            run,
            run_dir,
            system,
            user,
            moment_input_hash,
            StrategicCompactMomentResponse.model_json_schema() if self._compact_refs else StrategicMomentResponse.model_json_schema(),
            validate=lambda output: self._extraction_partition(output, run.run_id, transcripts),
        )
        validation = self._extraction_partition(moment_artifact.output, run.run_id, transcripts)
        # Only moments that bind are evidence; unverified records stay in moment_validation.json, never proof.
        moments = validation.moments
        self.store.write_json(f"{run_dir}/moments.json", [m.model_dump(mode="json") for m in moments])
        self.store.write_json(f"{run_dir}/moment_validation.json", {
            **validation.summary(), "request_fingerprint": moment_artifact.request_fingerprint,
            "revalidated_from_attempt": moment_artifact.metadata.get("revalidated_from_attempt")}, overwrite=True)
        # Stage 2 can inspect actual surrounding turns, not only a model summary.
        knowledge_base = self._knowledge_base
        if knowledge_base is not None:
            angle_version = self.settings.angle_prompt_profile
            angle_artifact, angle_output, angles, _repair = self.generate_cards(run, run_dir, moments, transcripts, knowledge_base,
                                                                                strategy_brief=self._strategy_brief)
        else:
            angle_version = self.settings.angle_prompt_profile
            angle_system, angle_user = angle_prompt(self._moment_packet(moments, transcripts), [], angle_version)
            angle_input_hash = canonical_hash(
                {"system": angle_system, "user": angle_user, "moment_ids": [m.moment_id for m in moments]}
            )
            angle_schema = StrategicAngleResponse.model_json_schema()
            angle_artifact = self._call_json(
                "angle_generation",
                run,
                run_dir,
                angle_system,
                angle_user,
                angle_input_hash,
                angle_schema,
                validate=lambda output: self._parse_angles(output, run.run_id, moments),
                prompt_version=angle_version,
            )
            angle_output = angle_artifact.output
            angles = self._parse_angles(angle_artifact.output, run.run_id, moments, artifact=angle_artifact)
        self.store.write_json(f"{run_dir}/candidates.json", [a.model_dump(mode="json") for a in angles])
        self._write_discovery_outputs(run_dir, angle_output, angles, moments)
        if is_card_response(angle_artifact.output):
            self.store.write_json(f"{run_dir}/review.json", {
                "run_id": run.run_id,
                "status": "generation_completed",
                "execution_scope": "generation_only",
                "angle_prompt_profile": angle_version,
                "candidate_angle_ids": [a.angle_id for a in angles],
                "visible_angle_ids": [],
                "angle_count": len(angles),
                "embeddings_enabled": False,
                "embedding_requests": 0,
                "similarity_status": "not_run",
                "quality_scores_status": "not_requested_card_profile_ranks_instead",
                "internal_insight_count": len(angle_artifact.output["internal_insights"]),
                "considered_not_selected_count": len(angle_artifact.output["considered_not_selected"]),
                "coverage": "meeting_bounds_acknowledged" if self._compact_refs else "span_ids_acknowledged",
                "source_span_count": sum(len(t.spans) for t in transcripts),
                "delivered_span_count": sum(len(t.spans) for t in transcripts),
                "coverage_is_proof_of_comprehension": False,
            })
            return {"run_id": run.run_id, "week_index": run.week_index, "moments": len(moments), "angles": len(angles),
                    "visible": 0, "mode": run.mode, "execution_scope": "generation_only", "embedding_requests": 0,
                    "similarity_status": "not_run", "angle_prompt_profile": angle_version}
        if not self.settings.embeddings_enabled:
            self.store.write_json(
                f"{run_dir}/review.json",
                {
                    "run_id": run.run_id,
                    "status": "generation_completed",
                    "execution_scope": "generation_only",
                    "candidate_angle_ids": [a.angle_id for a in angles],
                    "visible_angle_ids": [],
                    "angle_count": len(angles),
                    "embeddings_enabled": False,
                    "embedding_requests": 0,
                    "similarity_status": "not_run",
                    "recency_adjustment_status": "not_run",
                    "quality_scores_status": "model_self_scores_not_human_calibrated",
                    "internal_insight_count": len(angle_artifact.output.get("internal_insights", [])),
                    "research_required_angle_ids": [a.angle_id for a in angles if a.strategy and a.strategy.evidence_readiness == "research_required"],
                    "coverage": "meeting_bounds_acknowledged" if self._compact_refs else "span_ids_acknowledged",
                    "source_span_count": sum(len(t.spans) for t in transcripts),
                    "processed_span_count": None if self._compact_refs else len(moment_artifact.output["processed_span_ids"]),
                    "delivered_span_count": sum(len(t.spans) for t in transcripts),
                    "processed_meeting_count": len(moment_artifact.output["processed_meetings"]) if self._compact_refs else None,
                    "coverage_is_proof_of_comprehension": False,
                    "processed_moment_count": len(angle_artifact.output["processed_moment_ids"]),
                },
            )
            return {
                "run_id": run.run_id,
                "week_index": run.week_index,
                "moments": len(moments),
                "angles": len(angles),
                "visible": 0,
                "mode": run.mode,
                "execution_scope": "generation_only",
                "embedding_requests": 0,
                "similarity_status": "not_run",
            }
        for angle in angles:
            artifact = self._embedding(angle, run, run_dir)
            angle.embedding = artifact.output["vector"]
        history = self._load_history(run)
        ranked = rank(
            angles,
            history,
            threshold=self.settings.similarity_threshold,
            visible_threshold=self.settings.visible_threshold,
            half_life=self.settings.recency_half_life_days,
            max_penalty=self.settings.max_recency_penalty,
        )
        self.store.write_json(f"{run_dir}/angles.json", [a.model_dump(mode="json") for a in ranked])
        self.store.write_json(
            f"{run_dir}/review.json",
            {
                "run_id": run.run_id,
                "visible_angle_ids": [a.angle_id for a in ranked if a.status == "visible"],
                "angle_count": len(ranked),
                "coverage": "acknowledged",
                "source_span_count": sum(len(t.spans) for t in transcripts),
                "processed_span_count": None if self._compact_refs else len(moment_artifact.output["processed_span_ids"]),
                "delivered_span_count": sum(len(t.spans) for t in transcripts),
                "processed_moment_count": len(angle_artifact.output["processed_moment_ids"]),
            },
        )
        return {
            "run_id": run.run_id,
            "week_index": run.week_index,
            "moments": len(moments),
            "angles": len(ranked),
            "visible": sum(a.status == "visible" for a in ranked),
            "mode": run.mode,
        }

    def _reuse(self, artifact: StageArtifact, run: RunManifest, run_dir: str) -> None:
        self.calls.reuse(artifact, run, run_dir)

    def _revalidate_saved(self, *args, **kwargs):
        return self.calls.revalidate_saved(*args, **kwargs)

    def _request_key(self, *, run: RunManifest, stage: str, endpoint: str, request: dict, input_hash: str | None = None) -> str:
        return self.calls.request_key(run=run, stage=stage, endpoint=endpoint, request=request, input_hash=input_hash)

    def _call_json(
        self,
        stage: str,
        run: RunManifest,
        run_dir: str,
        system: str,
        user: str,
        input_hash: str,
        schema: dict,
        *,
        validate: Callable[[dict], object],
        prompt_version: str | None = None,
        knowledge_base_version: str | None = None,
    ) -> StageArtifact:
        return self.calls.call_json(stage, run, run_dir, system, user, input_hash, schema, validate=validate,
                                    prompt_version=prompt_version, knowledge_base_version=knowledge_base_version)

    def _validate_vector(self, output: dict) -> None:
        self.calls.validate_vector(output, self.settings.embedding_dimensions)

    def _embedding(self, angle: Angle, run: RunManifest, run_dir: str) -> StageArtifact:
        return self.calls.embedding(angle, run, run_dir)

    @staticmethod
    def _coverage(expected: set[str], received: list[str], label: str) -> None:
        if len(received) != len(set(received)) or set(received) != expected:
            raise ValueError(f"{label} coverage must acknowledge every supplied ID exactly once")

    @staticmethod
    def _local_keys(records) -> None:
        keys = [record.local_key for record in records]
        if len(keys) != len(set(keys)):
            raise ValueError("Response local keys must be unique")

    def verify_cards(self, run: RunManifest, run_dir: str, angles: list[Angle], moments: list[Moment], transcripts,
                     *, strategy_brief: dict | None = None, team_practice=(), identities: list[dict] | None = None,
                     identity_ids: dict[str, list[str]] | None = None) -> dict[str, dict]:
        """E.B10: one evidence ledger per card. The deterministic pass always runs; the model pass runs when a
        verification model from another family is configured, through the same provider, plan and routing.

        With that model configured, a public card that fails rubric criterion 1 (the R40 check) also gets the critic's
        one reframe call. A reframe that the deterministic pass then accepts replaces the card in `angles`, in place and
        under a new angle ID; one that still fails leaves the card and its flags as they were. Either way the attempt is
        recorded on the ledger's critic.

        The model pass's prompt is the `prompts.profile.card_verification` setting: v3, or v4 with strategist v7's point tests
        (E.B30). With the cycle's strategy brief (E.B28), a card that undercuts an offer in force is flagged with the offer.

        With the cycle's identity records (Phase N8, frozen with a strategist v8 run), a card that names a person or account
        never to be named, or ties one to the published work it must never be linked to, is blocked; so is a client name or
        figure that only a team-practice scene carries (`team_practice`, D24). `identity_ids` maps a moment to the people and
        accounts of its call, so a do-not-link marker is caught on a card built on that call even when it names nobody.
        """
        from .cycle import verification
        root = self.settings.knowledge_base_root
        profile = getattr(self.settings, "card_verification_profile", verification.MODEL_PASS_PROFILE)
        scenes = {m["moment_id"]: m["source_evidence"] for m in self._moment_packet(moments, transcripts)}
        sensitivity = {m.moment_id: m.sensitivity for m in moments}
        kb = self.context("verifier", run.mode)
        # What the verifier used, for the run's record (L.B5).
        self.verifier_context = kb.refs()
        roster, rules = kb.roster, verification.rules_for(kb, root)
        # Whitney's belief statements: a card quoting one states WIA's view, not an invented quote (E.B10).
        document = getattr(kb, "document", None)
        beliefs = verification.belief_index(document(verification.BELIEF_DOCUMENT)) if document else None

        def check(card: dict) -> dict:
            return verification.verify_card(card, scenes, roster, rules, sensitivity=sensitivity, internal_terms=kb.internal_terms,
                                            beliefs=beliefs, published=getattr(kb, "published_points", None),
                                            strategy_brief=strategy_brief, identities=identities, team_practice=team_practice,
                                            identity_ids=identity_ids)

        positions = [i for i, a in enumerate(angles) if a.card]
        cards = [angles[i].card.model_dump(mode="json") for i in positions]
        ledgers = [check(c) for c in cards]
        verifier = self.settings.openrouter_verification_model
        if verifier and cards:
            verification.check_families(self.settings.model_for("angle_generation"), verifier)
            system, user, refs = verification.model_pass_prompt(cards, scenes, ledgers, kb.text, profile)
            try:
                artifact = self._call_json(
                    "card_verification", run, run_dir, system, user, canonical_hash({"system": system, "user": user}),
                    verification.model_pass_schema(profile), validate=lambda out: verification.check_model_pass(out, cards),
                    prompt_version=profile)
            except MODEL_PASS_UNAVAILABLE as error:
                # Plan 4.11: an outage, no compliant route or an unusable answer leaves the week its deterministic
                # ledgers, marked, instead of failing the run after the strategist call was paid. A plan or budget
                # refusal (PermissionError) and a replay cache miss still stop the run.
                if run.mode == "replay":
                    raise
                note = f"{type(error).__name__}: {error}"
                return {angles[i].angle_id: verification.mark_unavailable(ledger, note) for i, ledger in zip(positions, ledgers)}
            by_rank = {item["rank"]: item for item in artifact.output["cards"]}
            ledgers = [verification.merge_model_pass(ledger, by_rank.get(card["rank"], {}), refs, verifier, beliefs=beliefs,
                                                     card=card, scenes=scenes, roster=roster)
                       for card, ledger in zip(cards, ledgers)]
            for n, (index, card, ledger) in enumerate(zip(positions, cards, ledgers)):
                # One pass over the slate: at most one reframe call per card per run.
                if failures := verification.criterion_one_failures(ledger):
                    ledgers[n], repaired = self._reframe_card(run, run_dir, card, ledger, failures, scenes, kb.text,
                                                              lambda c, rank=card["rank"]: verification.merge_model_pass(
                                                                  check(c), by_rank.get(rank, {}), refs, verifier,
                                                                  beliefs=beliefs, card=c, scenes=scenes, roster=roster))
                    if repaired:
                        angles[index] = self._reframed_angle(angles[index], repaired, ledgers[n]["critic"]["repair"])
        return {angles[i].angle_id: ledger for i, ledger in zip(positions, ledgers)}

    def _reframe_card(self, run: RunManifest, run_dir: str, card: dict, ledger: dict, failures: list[dict], scenes,
                      knowledge_base_text: str, recheck: Callable[[dict], dict]) -> tuple[dict, dict | None]:
        """The critic's one reframe call for a card failing criterion 1; returns the ledger and the repaired card or None.

        Same stage, provider, run plan and routing as the model pass. An invalid response or an unavailable route is a
        failed attempt, recorded, and the card keeps its flags; plan, budget and replay errors still stop the run.
        """
        from .cycle import verification
        model = self.settings.openrouter_verification_model
        system, user = verification.reframe_prompt(card, scenes, ledger, knowledge_base_text)
        try:
            artifact = self._call_json(
                "card_verification", run, run_dir, system, user, canonical_hash({"system": system, "user": user}),
                verification.REFRAME_SCHEMA, validate=verification.check_reframe, prompt_version=verification.REFRAME_PROFILE)
        except MODEL_PASS_UNAVAILABLE as error:
            if run.mode == "replay":
                raise
            entry = verification.repair_entry(card, failures, result="still_failing", model=model,
                                              error=f"{type(error).__name__}: {error}")
            return verification.record_repair(ledger, entry), None
        after_card = verification.apply_reframe(card, artifact.output)
        after = recheck(after_card)
        result = verification.reframe_result(ledger, after)
        entry = verification.repair_entry(card, failures, result=result, model=model, after_card=after_card, artifact=artifact,
                                          after_ledger=after, reason=artifact.output["reason"])
        if result == "repaired":
            return verification.record_repair(after, entry), after_card
        return verification.record_repair(ledger, entry), None

    @staticmethod
    def _reframed_angle(angle: Angle, card: dict, repair: dict) -> Angle:
        """The repaired card as a new angle: new content, so a new ID; its moments, lineage and family are unchanged."""
        new = type(angle.card).model_validate(card)
        return angle.model_copy(update={
            "angle_id": "angle_" + canonical_hash({"reframe_of": angle.angle_id, "repair": repair["request_fingerprint"]})[:24],
            "title": new.title, "argument": card_point(card), "take": card_point(card),
            "mechanism": new.wia_in_action or card_point(card), "signature": signature_from_fields(new.model_dump(mode="json")),
            "card": new})

    @staticmethod
    def _moment_packet(moments: list[Moment], transcripts) -> list[dict]:
        spans = {span.span_id: span for transcript in transcripts for span in transcript.spans}
        revisions = {transcript.source_id: transcript.content_hash for transcript in transcripts}
        return [
            {
                **moment.model_dump(mode="json"),
                "source_evidence": [spans[span_id].model_dump(mode="json") for span_id in moment.context_span_ids],
                "source_revision_hashes": {source_id: revisions[source_id] for source_id in moment.source_ids},
                **(
                    {"source_metadata": {t.source_id: t.source_metadata for t in transcripts if t.source_id in moment.source_ids}}
                    if any(t.source_metadata for t in transcripts)
                    else {}
                ),
                "speaker_identity_status": "unverified_labels",
            }
            for moment in moments
        ]

    @staticmethod
    def _validate_current_contract(output: dict, schema: dict) -> None:
        contracts = (StrategicMomentResponse, StrategicCompactMomentResponse, StrategicAngleResponse, StrategicRefinementResponse,
                     WeeklyAngleCards, WeeklyAngleCardsV5, WeeklyAngleCardsV7)
        for contract in contracts:
            if schema.get("title") == contract.__name__:
                contract.model_validate(output)
                return

    def _write_discovery_outputs(self, run_dir: str, output: dict, angles: list[Angle], moments: list[Moment] = ()) -> None:
        if is_card_response(output):
            self.store.write_json(f"{run_dir}/angle_cards.json", [
                {"angle_id": a.angle_id, "source_family_id": a.source_family_id, **a.card.model_dump(mode="json")}
                for a in angles
            ])
            self.store.write_json(f"{run_dir}/angle_selection.json", self.card_selection(output, angles, moments))
            return
        if is_strategic_angle_response(output):
            self.store.write_json(f"{run_dir}/internal_insights.json", output["internal_insights"])
            self.store.write_json(f"{run_dir}/opportunities.json", [
                {"angle_id": a.angle_id, "source_family_id": a.source_family_id, **a.strategy.model_dump(mode="json")}
                for a in angles if a.strategy
            ])

    def _moment_response(self, output: dict, transcripts):
        """Response-level checks: schema, span coverage, unique keys. A failure here fails the whole extraction."""
        contract = StrategicMomentResponse if is_strategic_moment_response(output) else MomentResponse
        response = contract.model_validate(output)
        spans = {s.span_id: s for t in transcripts for s in t.spans}
        self._coverage(set(spans), response.processed_span_ids, "Span")
        self._local_keys(response.moments)
        if not response.moments and not response.coverage_notes:
            raise ValueError("An empty moment result requires an explanation")
        return response, spans

    @staticmethod
    def _check_moment_structure(draft, spans) -> None:
        anchors, context = draft.anchor_span_ids, draft.context_span_ids
        if any(x not in spans for x in anchors + context):
            raise ValueError("Moment references an unknown source span")
        if len(set(anchors)) != len(anchors) or len(set(context)) != len(context):
            raise ValueError("Moment source references must be unique")
        if not set(anchors).issubset(context):
            raise ValueError("Context must contain every anchor")
        if len({spans[x].source_id for x in anchors + context}) != 1:
            raise ValueError("A moment cannot combine different source conversations")
        ordinals = [spans[x].ordinal for x in context]
        if ordinals != list(range(min(ordinals), max(ordinals) + 1)):
            raise ValueError("Moment context must be contiguous and chronological")
        if [spans[x].ordinal for x in anchors] != sorted(spans[x].ordinal for x in anchors):
            raise ValueError("Moment anchors must be chronological")

    @staticmethod
    def _moment(draft, raw: dict, spans, transcripts) -> Moment:
        identity = canonical_hash({"source_revisions": {t.source_id: t.content_hash for t in transcripts}, "moment": raw})
        return Moment(
            moment_id=f"moment_{identity[:24]}",
            source_ids=sorted({spans[x].source_id for x in draft.anchor_span_ids}),
            anchor_span_ids=draft.anchor_span_ids,
            context_span_ids=draft.context_span_ids,
            quote=raw["quote"],
            context_summary=draft.context_summary,
            moment_type=draft.moment_type,
            proposition=draft.proposition,
            audience_relevance=draft.audience_relevance,
            qualifications=draft.qualifications,
            claim_status=draft.claim_status,
            sensitivity=draft.sensitivity,
            strength=draft.strength,
            reasons=draft.reasons,
            discovery=getattr(draft, "discovery", None),
        )

    def _extraction_partition(self, output: dict, run_id: str, transcripts):
        """The file-backed runner's extraction check, with the SQL weekly path's per-moment rule (E.B12a).

        Schema, coverage and key failures fail the week. Each moment is then checked alone: one that binds is kept, a
        whitespace or punctuation near-miss is repaired with the repair recorded, and the rest are unverified records
        that never reach the angle call. A response whose every proposed moment is unverified also fails, before the
        angle call is paid for: there is no evidence to generate from.
        """
        from .moment_validation import resolve_moment_references_partial

        resolved, unresolved = (resolve_moment_references_partial(output, self._compact_refs) if self._compact_refs
                                else (output, {}))
        result = self._partition_moments(resolved, run_id, transcripts, unresolved=unresolved)
        if result.unverified and not result.moments:
            raise ValueError("No proposed moment binds to its source, so there is no evidence for the angle call: "
                             + "; ".join(dict.fromkeys(u["reason"] for u in result.unverified)))
        return result

    def _parse_moments(self, output: dict, run_id: str, transcripts) -> list[Moment]:
        """Strict: any moment that does not bind fails the response (the sealed model experiments' validator; the
        file-backed runner and calibration use the per-moment rule, `_extraction_partition`)."""
        response, spans = self._moment_response(output, transcripts)
        result = []
        for draft in response.moments:
            self._check_moment_structure(draft, spans)
            if not any(draft.quote in spans[x].text for x in draft.anchor_span_ids):
                raise ValueError("Moment quote must match an existing anchor span")
            result.append(self._moment(draft, draft.model_dump(mode="json"), spans, transcripts))
        return result

    def _partition_moments(self, output: dict, run_id: str, transcripts, *, unresolved: dict[int, str] | None = None):
        """Per-moment (E.B12a): keep moments that bind, repair near-miss quotes, keep the rest as unverified records.

        Only a response-level failure (schema, coverage, keys) raises. `unresolved` lists moments whose
        compact references could not be resolved; they are unverified without further checks.
        """
        from .moment_validation import REPAIR_RULE, MomentPartition, repair_quote

        response, spans = self._moment_response(output, transcripts)
        result = MomentPartition()
        for index, draft in enumerate(response.moments):
            raw, repair = draft.model_dump(mode="json"), None
            try:
                if unresolved and index in unresolved:
                    raise ValueError(unresolved[index])
                self._check_moment_structure(draft, spans)
                if not any(draft.quote in spans[x].text for x in draft.anchor_span_ids):
                    repaired = repair_quote(draft.quote, [spans[x].text for x in draft.anchor_span_ids])
                    if repaired is None:
                        raise ValueError("Moment quote must match an existing anchor span")
                    raw["quote"], at = repaired
                    repair = {"local_key": draft.local_key, "rule": REPAIR_RULE, "original_quote": draft.quote,
                              "repaired_quote": raw["quote"], "anchor_span_id": draft.anchor_span_ids[at]}
            except ValueError as error:
                result.unverified.append({"local_key": draft.local_key, "reason": str(error), "usable_as_proof": False,
                                          "draft": draft.model_dump(mode="json")})
                continue
            result.moments.append(self._moment(draft, raw, spans, transcripts))
            if repair:
                result.repairs.append({**repair, "moment_id": result.moments[-1].moment_id})
        return result

    def generate_cards(self, run: RunManifest, run_dir: str, moments: list[Moment], transcripts, knowledge_base: KnowledgeBase,
                       *, extra_input: dict | None = None, seeds: list[dict] | None = None,
                       strategy_brief: dict | None = None, team_practice=(), identities: list[dict] | None = None,
                       ) -> tuple[StageArtifact, dict, list[Angle], dict | None]:
        """One strategist call; returns the artifact, the output with moment IDs, the parsed cards and any repair record.

        Profiles with scene references (version 4) cite S1, S2, ...; the server resolves them. Unknown or repeated
        references, and internal-only scenes in public items, get exactly one repair call instead of failing the run.

        Version 7 (E.B30): the packet lists human lines and counter-expected decisions first, the user message carries the
        window's strategy brief, and two public cards drawing on the same conversation are a problem for the same repair
        call; if the repaired slate still has some, the later-ranked card moves to the considered ideas (recorded).
        """
        profile = self.settings.angle_prompt_profile
        packet = self._moment_packet(moments, transcripts)
        v7 = profile in BRIEF_PROFILES
        v8 = profile in IDENTITY_PROFILES
        if v7:
            packet = order_packet(packet)
        system, user = strategist_angle_prompt(packet, knowledge_base, profile, seeds, strategy_brief,
                                               team_practice=team_practice, identities=identities)
        if getattr(knowledge_base, "situational", None):
            # The dated situational block (L.B5): WIA's plan and recent publishing, in the user message, not cached.
            user = user + "\n\n" + knowledge_base.situational
        schema, contract = card_schema(profile), card_contract(profile)
        base = {"system": system, "user": user, "moment_ids": [m.moment_id for m in moments],
                "knowledge_base": knowledge_base.refs(), **(extra_input or {})}
        if not uses_scene_references(profile):
            artifact = self._call_json("angle_generation", run, run_dir, system, user, canonical_hash(base), schema,
                                       validate=lambda out: self._parse_angles(out, run.run_id, moments), prompt_version=profile)
            return artifact, artifact.output, self._parse_angles(artifact.output, run.run_id, moments, artifact=artifact), None
        references = scene_references(packet)
        sensitivity = {m.moment_id: m.sensitivity for m in moments}
        conversations = {m.moment_id: list(m.source_ids) for m in moments}

        def check(out: dict, *, final: bool) -> list[str]:
            if final and v7:
                # After the one repair, the considered ideas' and insights' references are settled below; only a card's
                # reference problem fails the run.
                out = tidy_non_card_references(out, references, sensitivity)[0]
                if v8:
                    # Strategist v8: a card still on an internal-only scene becomes an internal insight below (N8).
                    out = demote_internal_cards(out, references, sensitivity)[0]
            problems = card_reference_problems(out, references, sensitivity)
            if v7 and not problems and not final:
                # One public card per client conversation (E.B29 change): the repair call fixes it, else it is demoted below.
                problems = conversation_problems(out, references, conversations)
            if problems:
                contract.model_validate(out)
                if final:
                    raise ValueError("Card scene references are still invalid after one repair: " + "; ".join(problems))
                return problems
            self._parse_angles(resolve_card_references(out, references), run.run_id, moments)
            return []

        artifact = self._call_json("angle_generation", run, run_dir, system, user, canonical_hash(base), schema,
                                   validate=lambda out: check(out, final=False), prompt_version=profile)
        repair = None
        if problems := check(artifact.output, final=False):
            first = artifact
            artifact = self._call_json(
                "angle_generation", run, run_dir, system, repair_user(user, first.output, problems, references),
                canonical_hash({**base, "repair_of": first.request_fingerprint, "problems": problems}), schema,
                validate=lambda out: check(out, final=True), prompt_version=f"{profile}.reference-repair")
            repair = {"problems": problems, "first_request_fingerprint": first.request_fingerprint,
                      "first_artifact_id": first.artifact_id, "repair_request_fingerprint": artifact.request_fingerprint}
            self.store.write_json(f"{run_dir}/angle_reference_repair.json", repair, overwrite=True)
        settled = artifact.output
        if v7 and repair is not None:
            settled, tidied = tidy_non_card_references(artifact.output, references, sensitivity)
            if tidied:
                repair = {**repair, "tidied_references": tidied}
                self.store.write_json(f"{run_dir}/angle_reference_repair.json", repair, overwrite=True)
            if v8:
                settled, demoted = demote_internal_cards(settled, references, sensitivity)
                if demoted:
                    repair = {**repair, "demoted_internal_cards": demoted}
                    self.store.write_json(f"{run_dir}/angle_reference_repair.json", repair, overwrite=True)
        output = resolve_card_references(settled, references)
        if v7 and conversation_problems(output, {}, conversations):
            output, moved = demote_same_conversation(output, {}, conversations)
            repair = {**(repair or {}), "demoted_same_conversation": moved}
            self.store.write_json(f"{run_dir}/angle_reference_repair.json", repair, overwrite=True)
        angles = self._parse_angles(output, run.run_id, moments, artifact=artifact)
        return artifact, output, angles, repair

    @staticmethod
    def card_selection(output: dict, angles: list[Angle], moments: list[Moment]) -> dict:
        """Week-level reasoning for the Gate 1 "why these" view: summary, ranking, insights and dropped ideas."""
        referenced = {mid for a in angles for mid in a.moment_ids}
        referenced |= {mid for item in output["internal_insights"] + output["considered_not_selected"] for mid in item["moment_ids"]}
        return {
            "week_summary": output["week_summary"],
            "ranked_angle_ids": [a.angle_id for a in sorted(angles, key=lambda a: a.card.rank)],
            "internal_insights": output["internal_insights"],
            "considered_not_selected": output["considered_not_selected"],
            "unreferenced_moment_ids": [m.moment_id for m in moments if m.moment_id not in referenced],
            # Version 5 (E.B21): the proposed week, pillar coverage and seed pairings, for the "why these" panel.
            **{key: output[key] for key in ("publishing_order", "pillar_notes", "seed_pairings") if key in output},
        }

    def _parse_cards(self, output: dict, run_id: str, moments: list[Moment], artifact: StageArtifact | None) -> list[Angle]:
        # The output names its own contract: version 5 adds the week-level fields (E.B21), version 7 the point (E.B30).
        v7 = any("point" in a for a in output.get("angles", []))
        response = (WeeklyAngleCardsV7 if v7 else WeeklyAngleCardsV5 if "publishing_order" in output
                    else WeeklyAngleCards).model_validate(output)
        moment_map = {m.moment_id: m for m in moments}

        def check(refs: list[str], label: str) -> None:
            if len(refs) != len(set(refs)) or any(ref not in moment_map for ref in refs):
                raise ValueError(f"{label} references unknown or duplicate moments")

        for insight in response.internal_insights:
            check(insight.moment_ids, "Internal insight")
        for idea in response.considered_not_selected:
            check(idea.moment_ids, "Considered idea")
        signatures = set()
        result = []
        for card in sorted(response.angles, key=lambda c: c.rank):
            check(card.moment_ids, "Angle")
            raw = card.model_dump(mode="json")
            signature = signature_from_fields(raw)
            if signature.casefold() in signatures:
                raise ValueError("Duplicate canonical angle arguments in the same response")
            signatures.add(signature.casefold())
            refs = card.moment_ids
            # Verify-before-publishing stays on the card; the Angle keeps only deterministic moment handling.
            qualifiers = list(dict.fromkeys(limit for ref in refs for limit in moment_map[ref].qualifications))
            risks = list(dict.fromkeys(f"handling: {moment_map[ref].sensitivity}; public reuse needs review" for ref in refs))
            identity = canonical_hash({"generation": artifact.request_fingerprint if artifact else "validation", "angle": raw})
            lineage = {"generated_at": artifact.created_at} if artifact else {}
            result.append(Angle(
                angle_id=f"angle_{identity[:24]}",
                run_id=artifact.run_id if artifact else run_id,
                title=card.title,
                argument=card_point(raw),
                audience=card.audience,
                tension="",
                take=card_point(raw),
                mechanism=card.wia_in_action or card_point(raw),
                reader_decision=None,
                moment_ids=refs,
                source_assertions=[],
                qualifiers=qualifiers,
                risks=risks,
                signature=signature,
                quality=None,
                base_score=None,
                card=card,
                source_family_id="source_family_" + canonical_hash(sorted({sid for ref in refs for sid in moment_map[ref].source_ids}))[:24],
                **lineage,
            ))
        return result

    def _parse_angles(
        self, output: dict, run_id: str, moments: list[Moment], *, artifact: StageArtifact | None = None
    ) -> list[Angle]:
        if is_card_response(output):
            return self._parse_cards(output, run_id, moments, artifact)
        strategic = is_strategic_angle_response(output)
        response = (StrategicAngleResponse if strategic else AngleResponse).model_validate(output)
        moment_map = {m.moment_id: m for m in moments}
        moment_ids = set(moment_map)
        self._coverage(moment_ids, response.processed_moment_ids, "Moment")
        self._local_keys(response.angles)
        internal = getattr(response, "internal_insights", [])
        for insight in internal:
            if len(insight.moment_ids) != len(set(insight.moment_ids)) or any(mid not in moment_ids for mid in insight.moment_ids):
                raise ValueError("Internal insight references unknown or duplicate moments")
        if not response.angles and not response.coverage_notes and not internal:
            raise ValueError("An empty angle result requires an explanation")
        signatures = set()
        result = []
        for draft in response.angles:
            raw = draft.model_dump(mode="json")
            refs = draft.moment_ids
            if any(x not in moment_ids for x in refs):
                raise ValueError("Angle references an unknown moment")
            if len(refs) != len(set(refs)):
                raise ValueError("Angle moment references must be unique")
            if any(not any(claim.startswith(f"[{ref}] ") for ref in refs) for claim in draft.source_assertions):
                raise ValueError("Every source assertion must start with a referenced [moment_id]")
            signature = signature_from_fields(raw)
            if signature.casefold() in signatures:
                raise ValueError("Duplicate canonical angle arguments in the same response")
            signatures.add(signature.casefold())
            if strategic:
                q = draft.quality
                quality = Quality(grounding=q.grounding, source_relevance=q.source_strength,
                    audience_fit=q.audience_resonance, specificity=q.distinctiveness,
                    editorial_usefulness=q.strategic_fit, reasons=q.reasons,
                    strategic_fit=q.strategic_fit, distinctiveness=q.distinctiveness,
                    audience_resonance=q.audience_resonance, source_strength=q.source_strength)
            else:
                quality = Quality.model_validate(draft.quality.model_dump())
            qualifiers = list(
                dict.fromkeys(draft.qualifiers + [limit for ref in refs for limit in moment_map[ref].qualifications])
            )
            risks = list(
                dict.fromkeys(
                    draft.risks + [f"handling: {moment_map[ref].sensitivity}; public reuse needs review" for ref in refs]
                )
            )
            identity = canonical_hash({"generation": artifact.request_fingerprint if artifact else "validation", "angle": raw})
            lineage = {"generated_at": artifact.created_at} if artifact else {}
            result.append(
                Angle(
                    angle_id=f"angle_{identity[:24]}",
                    run_id=artifact.run_id if artifact else run_id,
                    title=raw.get("title", ""),
                    argument=raw["core_perspective"] if strategic else raw["argument"],
                    audience=raw.get("audience", ""),
                    tension=raw.get("tension", ""),
                    take=raw["core_perspective"] if strategic else raw.get("take", ""),
                    mechanism=(raw["wia_expertise_in_action"] or raw["core_perspective"]) if strategic else raw.get("mechanism", ""),
                    reader_decision=raw.get("reader_decision", ""),
                    moment_ids=refs,
                    source_assertions=raw.get("source_assertions", []),
                    inference=raw.get("inference"),
                    qualifiers=qualifiers,
                    risks=risks,
                    signature=signature,
                    quality=quality,
                    base_score=quality.score(),
                    strategy=draft.model_copy(update={"qualifiers":qualifiers, "risks":risks}) if strategic else None,
                    source_family_id=("source_family_" + canonical_hash(sorted({sid for ref in refs for sid in moment_map[ref].source_ids}))[:24]) if strategic else None,
                    **lineage,
                )
            )
        return result

    def _load_history(self, run: RunManifest) -> list[Angle]:
        history = {}
        for path in (self.settings.data_root / "experiments").glob("**/angles.json"):
            if path.parent.name == run.run_id:
                continue
            try:
                manifest = RunManifest.model_validate_json((path.parent / "manifest.json").read_text(encoding="utf-8"))
                if (
                    manifest.status != "completed"
                    or manifest.week_index > run.week_index
                    or (manifest.mode == "fake") != (run.mode == "fake")
                    or manifest.embedding_profile != run.embedding_profile
                ):
                    continue
                for item in json.loads(path.read_text(encoding="utf-8")):
                    angle = Angle.model_validate(item)
                    history[angle.angle_id] = angle
            except (OSError, ValueError, TypeError):
                continue
        return [a for a in history.values() if a.embedding]
