"""Content pack contract version 2 (Phase NP; the content-packs plan, sections 4.1, 4.2 and 5.3 to 5.6).

A pack is what WIA posts from for one approved idea: **one email, three Reels (story, stance, b-roll text) and one
carousel** (D43a), each Reel and the carousel with its caption, finished after Gate 2 inside a fidelity loop (D43b).

**The v4 leaf shape.** Each piece keeps brief contract v4's leaf names (`briefs/contracts_v4.py`) with the pack's extra
fields beside them, so that:
- a Gate 2 lock translates by a fixed table where only the Reel index changes (`translate_lock`);
- the brief's deterministic checks run on the pack unchanged (`v4_body`);
- comparing and reverting work leaf by leaf, by the same dotted paths the Gate 2 editor writes (`briefs/paths.py`), here
  relative to the piece's `content` (its leaves; `brief_copy` holds the brief's): `caption.hook`, `slides[2].text`, `subject_options[0]`.

**Where things live.** One `content_packs` row per pack version, its pack-level fields in `content_body` (`PackBody`);
one `content_assets` row per piece (`slot_key` is the piece key), its envelope in `content_body` (`Piece`). A person's
edit, a revert, a text-changing attestation and "Finish again" each make a new version (`packs/model.py`).

**What a model returns.** The finisher returns `FinishOutput`, the check `CheckOutput`, the repair `RepairOutput`; each
is sent to the model as its plain wire schema (`wire_schema`: no length bounds, patterns or titles, which Anthropic's
structured output refuses) and validated here in full.

This module is the frozen contract both build tracks share (plan section 8): change it only with both.
"""
from __future__ import annotations

import re
import warnings
from typing import Literal

from pydantic import Field, model_validator

from ..calendar.contracts import Mutation
from ..contracts import Contract, Text

# `register` is v4's field name; as in briefs/contracts_v4.py it shadows ABCMeta.register only on the class.
warnings.filterwarnings("ignore", message='Field name "register"', category=UserWarning)

VERSION = "content_pack_v2"
HANDOFF_VERSION = "brief_handoff_v2"

# Piece keys. The app's tabs follow the mock WIA saw on 20 October (Email, Carousel, Reel 1, Reel 2, Reel 3); the exported
# document follows the v2 document's order (Email, Reel 1 to 3, Carousel).
PIECE_KEYS = ("email", "carousel", "reel_1", "reel_2", "reel_3")
TAB_ORDER = PIECE_KEYS
EXPORT_ORDER = ("email", "reel_1", "reel_2", "reel_3", "carousel")
# Reels are ordered story, stance, b-roll text and mapped from the brief by their kind, never by position (section 4.2).
REEL_KINDS = ("story", "stance", "broll_text")
KEY_KIND = {"reel_1": "story", "reel_2": "stance", "reel_3": "broll_text"}
# Round 2 (WIA's feedback of 26 October 2026; finisher v3, writer v5.3): Reel 1 is the central story, Reels 2 and 3 each a
# premise of its own; how a Reel is made (`production`: face to camera, or on-screen text over b-roll) is a production
# choice, never its kind. A pack under finisher v3 has these kinds; an earlier pack keeps story, stance and b-roll text.
PREMISE_KINDS = ("central", "second", "third")
KEY_PREMISE = {"reel_1": "central", "reel_2": "second", "reel_3": "third"}
KIND_KEY = {**{k: v for v, k in KEY_KIND.items()}, **{k: v for v, k in KEY_PREMISE.items()}}
PRODUCTIONS = ("face_to_camera", "on_screen_text")
CHANNEL = {"email": "email", "carousel": "carousel", "reel_1": "reel", "reel_2": "reel", "reel_3": "reel"}
LABELS = {"email": "Email", "carousel": "Carousel", "reel_1": "Reel 1", "reel_2": "Reel 2", "reel_3": "Reel 3"}
KIND_LABELS = {"story": "face to camera (story)", "stance": "face to camera (stance)", "broll_text": "b-roll text",
               "central": "central story", "second": "second premise", "third": "third premise"}
ORDINAL = {k: i for i, k in enumerate(PIECE_KEYS, 1)}

# The pack run's stages, in order (section 5.1). Each depends on the one before; repair and re-check finish without a call
# when nothing was flagged, and every model stage finishes without a call in the `assemble` mode.
STAGES = ("pack_assemble", "pack_finish", "pack_check", "pack_repair", "pack_recheck", "pack_finalize")
# NP-7's person-started passes (the post-recording pass, finishing again with a permission). Registered with the budget
# now, so a week's frozen stage list never refuses them (NP.B5).
LATER_STAGES = ("pack_caption", "pack_refinish")
# A person-started pass (NP-7) runs the same six steps with its own writer step in the finisher's place: the post-recording
# pass (NP.B14) writes a Reel's caption and covers from what Whitney said; finishing again with a permission (NP.B15) is the
# finisher with the granted facts as evidence.
PASSES = {"caption": "pack_caption", "refinish": "pack_refinish"}
# Every stage a v2 run can have, in order (the order a run's jobs are listed in).
ALL_STAGES = ("pack_assemble", "pack_finish", *LATER_STAGES, "pack_check", "pack_repair", "pack_recheck", "pack_finalize")
MODEL_STAGES = ("pack_finish", "pack_check", "pack_repair", "pack_recheck", *LATER_STAGES)
# The writer stages use models.pack_writer (Opus 5.5); the check stages models.pack_review (Sonnet 5.5).
WRITER_STAGES = ("pack_finish", "pack_repair", "pack_caption", "pack_refinish")
REVIEW_STAGES = ("pack_check", "pack_recheck")
RUN_SCOPE = "pack_generation"

# packs.finish_mode (section 5.4): finish (default); missing_only (the brief's copy verbatim, only a missing Reel kind
# written); assemble (no model call; a missing kind shows as "not written").
FINISH_MODES = ("finish", "missing_only", "assemble")
# Where a piece's copy came from: the brief verbatim, the brief finished, written by the finisher (a kind the brief
# lacked), or not written (a missing kind in the assemble mode, which blocks Ready).
ORIGINS = ("brief", "finished", "written", "not_written")
# The prompt profiles (settings prompts.profile.pack_*), each a released file in prompt_templates/ (E.B17). Every released
# profile stays selectable, so a pack made under an earlier one replays; the last of each stage is the default. v2 (NP.X3's
# stop rule): the paid proof's written stance Reel added an order and an outcome the sources do not state, so the finisher
# keeps the supporting example's own order and outcome and the check flags an added one; the carousel's close asks for
# nothing when the brief keeps Instagram without an offer.
# v3 of the check (NP-7): the approved brief's WIA perspective is among its sources, so a stance line the team approved is
# not flagged, and widening one moment into a standing practice is unsupported (the paid proof's two misses, NP.X5).
# Round 2 (WIA's feedback of 26 October 2026): finisher v3 writes the central story and two premises of their own, with E2M's
# craft and editorial guide and the hooks it weighed; check v4 adds an editorial reading (what a fact implies in public, how
# strong each piece is, premises that overlap); repair v2 fixes the editorial notes as well as the fidelity flags.
# Round 2's second pass: finisher v4 (and refinish v3) plan from the card's whole call (packs/call.py) and write Reels 2 and 3
# from the turns behind their premises; plan v2 reads the call.
RELEASED = {"pack_finish": ("2026-10-25.pack-finish.v1", "2026-10-25.pack-finish.v2", "2026-10-27.pack-finish.v3",
                            "2026-10-27.pack-finish.v4"),
            "pack_check": ("2026-10-25.pack-check.v1", "2026-10-25.pack-check.v2", "2026-10-26.pack-check.v3",
                           "2026-10-27.pack-check.v4"),
            "pack_repair": ("2026-10-25.pack-repair.v1", "2026-10-27.pack-repair.v2"),
            "pack_caption": ("2026-10-26.pack-caption.v1",),
            "pack_refinish": ("2026-10-26.pack-refinish.v1", "2026-10-27.pack-refinish.v2", "2026-10-27.pack-refinish.v3")}
# Round 2's profiles are released but selected by setting (production-settings.json), as writer v5.1 was: the code's
# defaults stay the last profiles before them, so every pack made earlier, and its saved answers, replays unchanged.
ROUND_TWO = ("2026-10-27.pack-finish.v3", "2026-10-27.pack-check.v4", "2026-10-27.pack-repair.v2", "2026-10-27.pack-refinish.v2",
             "2026-10-27.pack-finish.v4", "2026-10-27.pack-refinish.v3")
PROFILES = {stage: [p for p in released if p not in ROUND_TWO][-1] for stage, released in RELEASED.items()}
TEMPLATES = {"2026-10-25.pack-finish.v1": "pack_finish.v1.md", "2026-10-25.pack-finish.v2": "pack_finish.v2.md",
             "2026-10-25.pack-check.v1": "pack_check.v1.md", "2026-10-25.pack-check.v2": "pack_check.v2.md",
             "2026-10-26.pack-check.v3": "pack_check.v3.md", "2026-10-25.pack-repair.v1": "pack_repair.v1.md",
             "2026-10-26.pack-caption.v1": "pack_caption.v1.md", "2026-10-26.pack-refinish.v1": "pack_refinish.v1.md",
             "2026-10-27.pack-finish.v3": "pack_finish.v3.md", "2026-10-27.pack-check.v4": "pack_check.v4.md",
             "2026-10-27.pack-repair.v2": "pack_repair.v2.md",
             # Finishing again with a permission under Round 2 is finisher v3's prompt in its refinish mode.
             "2026-10-27.pack-refinish.v2": "pack_finish.v3.md",
             # Finisher v3's first call: the plan (each Reel's premise and production, the openings weighed).
             "2026-10-27.pack-plan.v1": "pack_plan.v1.md",
             "2026-10-27.pack-finish.v4": "pack_finish.v4.md", "2026-10-27.pack-refinish.v3": "pack_finish.v4.md",
             "2026-10-27.pack-plan.v2": "pack_plan.v2.md"}
# The check profiles whose sources carry the approved brief's WIA perspective (an earlier profile's request is unchanged, so
# its saved answers still replay).
PERSPECTIVE_CHECKS = ("2026-10-26.pack-check.v3", "2026-10-27.pack-check.v4")
# Round 2's profiles: the finisher that writes premises, the check with an editorial reading, the repair that fixes both.
PREMISE_FINISHERS = ("2026-10-27.pack-finish.v3", "2026-10-27.pack-refinish.v2", "2026-10-27.pack-finish.v4",
                     "2026-10-27.pack-refinish.v3")
# A premise finisher runs in two calls inside its step: the plan, then the writing (the writing answer is at the provider's
# grammar limit, so the premises and the openings weighed come from the plan's own small answer).
PLAN_PROFILE = "2026-10-27.pack-plan.v1"
PLAN_FOR = {"2026-10-27.pack-finish.v3": "2026-10-27.pack-plan.v1", "2026-10-27.pack-refinish.v2": "2026-10-27.pack-plan.v1",
            "2026-10-27.pack-finish.v4": "2026-10-27.pack-plan.v2", "2026-10-27.pack-refinish.v3": "2026-10-27.pack-plan.v2"}
# The finishers that read the card's whole call (packs/call.py).
CALL_FINISHERS = ("2026-10-27.pack-finish.v4", "2026-10-27.pack-refinish.v3")
EDITORIAL_CHECKS = ("2026-10-27.pack-check.v4",)
EDITORIAL_REPAIRS = ("2026-10-27.pack-repair.v2",)
# What the editorial reading names (check v4). Those that could misrepresent WIA, a client or a result block Ready until a
# person edits the line or keeps it with a reason; the craft notes are warnings the repair works on first.
EDITORIAL_ISSUES = {
    "misleading_implication": "blocking",   # what a prospect would infer is wrong, or unfair to WIA or the client
    "missing_context": "blocking",          # e.g. the performance of work WIA inherited, without saying it was inherited
    "lead_quality": "blocking",             # more inquiries beside ghosting or lost bookings, implying poor leads
    "unsupported_causation": "blocking",    # a cause the source shows only as a sequence
    "generalization": "blocking",           # a blanket claim about the industry or other agencies
    "not_for_public": "blocking",           # true, but not WIA's or the client's to share
    "technical_aside": "warning",           # the argument rests on a passing technical explanation
    "agency_comparison": "warning",         # WIA praised by comparison with other agencies
    "slogan": "warning",                    # a manufactured line, a motto, a dramatic contrast
    "repetition": "warning",                # a phrase or line repeated across pieces
    "premise_overlap": "warning",           # a Reel's premise repeats another Reel's story or point
    "broad_lesson": "warning",              # a generic principle where the specific decision should be
    "weak_hook": "warning",                 # an opening that is vague, manufactured or withholds the subject
    "format_rearranged": "warning",         # another piece's sentences rearranged, not written for this format
    "weak_takeaway": "warning",             # nothing worth having for an owner
    "cta_fit": "warning",                   # a CTA that does not fit the pillar or the piece
}

# The state of a pack version, derived on read (section 4.1); never stored.
STATES = ("finishing", "waiting", "in_review", "ready_to_publish", "superseded")
# The before-publishing note every client-permission item carries (the owner, 24 October: never a gate).
CLIENT_OKAY_NOTE = "Before posting: WIA confirms the client's okay"


# ---- the pieces, in the v4 leaf shape ----------------------------------------------------------------------------------

class CaptionV2(Contract):
    hook: Text
    body: Text
    ending: Text


class SendHeaderV2(Contract):
    date: Text
    send_time: Text
    recipients: Text


class EmailCopy(Contract):
    """The email: v4's leaves, and the pack's CTA kind (reply or link; never "DM" in an email)."""
    job: str
    register: Literal["written"]
    send_header: SendHeaderV2
    subject_options: list[Text] = Field(min_length=1, max_length=4)
    preview: Text
    opening: Text
    body: Text
    ending: Text
    offer_descriptor: str | None
    cta: Literal["reply", "link", "none"]


class ReelCopy(Contract):
    """A Reel: v4's leaves, and the pack's working title (never the creative direction), two cover alternates, its CTA and
    the caption's last lines with no offer ask for weeks it is not the offer post."""
    kind: Literal["story", "stance", "broll_text", "central", "second", "third"]
    job: str
    register: Literal["spoken", "on_screen"]
    # Round 2 (finisher v3): how it is made, its own premise, its takeaway, why it differs from the other Reels and where
    # its material is in the calls. Direction, never copy; absent on a Reel made before finisher v3.
    production: Literal["face_to_camera", "on_screen_text"] | None = None
    premise: str | None = None
    takeaway: str | None = None
    distinct_because: str | None = None
    timestamps: list[str] | None = None
    title: Text
    cover_text: Text
    cover_alternates: list[Text] = Field(max_length=2)
    on_screen_hook: Text
    spoken_opening: str | None
    script: str | None
    screens: list[Text] | None = Field(default=None, max_length=3)
    beats: list[Text] = Field(max_length=8)
    personal_lines: list[Text] = Field(max_length=6)
    read_time_seconds: int = Field(ge=5, le=180)
    source: Literal["existing_clip", "new_script"]
    caption: CaptionV2 | None
    offer_descriptor: str | None
    cta: Literal["none", "soft", "offer"]
    no_offer_ending: str | None


class SlideV2(Contract):
    number: int = Field(ge=1, le=12)
    job: str
    text: Text


class CarouselCopy(Contract):
    job: str
    register: Literal["written"]
    title: Text
    slides: list[SlideV2] = Field(min_length=1, max_length=12)
    caption: CaptionV2 | None
    offer_descriptor: str | None
    cta: Literal["none", "soft", "offer"]
    no_offer_ending: str | None


COPY_MODELS = {"email": EmailCopy, "carousel": CarouselCopy, "reel": ReelCopy}

# The leaves a person may edit, per channel (section 5.6's PATCH), as path prefixes relative to the piece's content. Direction
# (kind, job, register, beats, read time, source) is not copy; the CTA kinds are the brief's decision.
EDITABLE = {
    "email": ("send_header", "subject_options", "preview", "opening", "body", "ending"),
    "reel": ("title", "cover_text", "cover_alternates", "on_screen_hook", "spoken_opening", "script", "screens", "caption",
             "personal_lines", "no_offer_ending"),
    "carousel": ("title", "slides", "caption", "no_offer_ending"),
}
# Inside an editable prefix only these leaves are copy: a slide's text, never its number or job.
SLIDE_LEAF = re.compile(r"^slides\[\d{1,2}\]\.text$")


class Lock(Contract):
    """A line a person wrote: kept word for word by every model step (R56). `origin` is where it was written."""
    path: Text
    author: Text
    delegated: bool
    at: str | None
    origin: Literal["gate_two", "pack"]


class Resolution(Contract):
    by: Text
    at: Text
    delegated: bool
    note: str | None = None


class Finding(Contract):
    """A finding stored on a piece: the fidelity loop's (section 5.5). Deterministic findings are recomputed on every read
    and edit (packs/checks.py) and are never stored here.

    A finding on a written Reel blocks Ready until a person edits its sentence (`cleared`) or attests it is true
    (`attested`, R57). A finding on a piece the brief had never stays open: finalize puts the brief's sentence back."""
    finding_id: Text
    kind: Literal["fidelity", "editorial"]
    verdict: Literal["unsupported", "guardrail", "editorial"]
    path: str | None
    sentence: Text
    why: str
    severity: Literal["blocking", "warning"]
    status: Literal["open", "cleared", "attested", "kept"]
    resolution: Resolution | None = None
    # An editorial finding's issue (EDITORIAL_ISSUES); a person keeps the line with a reason (`kept`) or edits it.
    issue: str | None = None


class Change(Contract):
    """One change a step made to a piece's copy, for "What the finisher changed" and the record."""
    path: Text
    kind: Literal["finished", "written", "repaired", "put_back", "restored_lock", "kept_brief_carousel", "missed_patch",
                  "edited", "reverted", "recorded", "captioned"]
    before: str | None = None
    after: str | None = None
    note: str | None = None


class Piece(Contract):
    """One `content_assets.content_body`."""
    version: Literal["content_pack_v2"]
    key: Literal["email", "carousel", "reel_1", "reel_2", "reel_3"]
    channel: Literal["email", "carousel", "reel"]
    label: Text
    origin: Literal["brief", "finished", "written", "not_written"]
    not_written_reason: str | None = None
    brief_key: str | None
    content: dict | None
    brief_copy: dict | None
    locks: list[Lock]
    findings: list[Finding]
    changes: list[Change]


# ---- the pack ----------------------------------------------------------------------------------------------------------

class Done(Contract):
    """A before-publishing note marked done, or a client quote cleared: who, when, and the reference they gave."""
    by: Text
    at: Text
    delegated: bool
    reference: str | None = None
    note: str | None = None


class BeforePublishingNote(Contract):
    """Carried from Gate 2 with its answer (P1 to P5), or added by the pack. A client's permission is a note for whoever
    posts the piece, never a gate (`client_permission`)."""
    id: Text
    text: Text
    kind: Text
    required: bool
    answer: str | None
    client_permission: bool
    done: Done | None = None


class ClientQuote(Contract):
    """A client's words used in copy, listed for the client's okay before posting (section 4.3: a note, not a gate)."""
    quote_id: Text
    piece: Text
    quote: Text
    speaker: str | None
    evidence_id: str | None
    cleared: Done | None = None


class Provenance(Contract):
    brief_id: Text
    approved_hash: Text
    brief_schema: Text
    handoff_version: Text
    run_id: Text
    mode: Literal["live", "replay", "synthetic"]
    finish_mode: Literal["finish", "missing_only", "assemble"]
    profiles: dict
    models: dict
    knowledge_base_version: str | None
    approved_by: str | None
    approval_delegated: bool


class ChangeRecord(Contract):
    """Why this version exists (the versions list)."""
    kind: Literal["generated", "edit", "revert", "attest", "clearance", "finish_again", "recorded_take", "refinish"]
    by: Text
    at: Text
    delegated: bool
    pieces: list[str] = Field(default_factory=list)
    paths: list[str] = Field(default_factory=list)
    note: str | None = None


class Grant(Contract):
    """A "stronger with permission" item a person granted, or a fact they stated (NP.B15): evidence for the finisher and the
    check, recorded as attested with the person and date (R57). `item_id` names the granted item (S1...) and `item` keeps
    its text as it read when granted, when it is one."""
    item_id: str | None = None
    item: str | None = None
    statement: Text
    by: Text
    at: Text
    delegated: bool


class PackBody(Contract):
    """One `content_packs.content_body`: the pack-level fields of section 4.2. Caveats live here, never in copy (R54)."""
    version: Literal["content_pack_v2"]
    title: Text
    brief_id: Text
    week_id: Text
    angle_id: Text
    pillar: str | None
    rank: int | None
    message_spine: str | None
    cta: dict
    # The piece the finisher works from first (the brief's anchor, remapped to the pack's keys; section 4.2).
    anchor: str | None = None
    before_publishing: list[BeforePublishingNote]
    client_quotes: list[ClientQuote]
    stronger_with_permission: list[str]
    pack_notes: list[str]
    change_notes: list[str]
    fidelity: dict
    change: ChangeRecord
    provenance: Provenance
    granted: list[Grant] = Field(default_factory=list)
    # What Whitney said on each recorded take (NP.B14), by piece: a source for every later check of that Reel's caption.
    recorded_takes: dict[str, str] = Field(default_factory=dict)
    # Round 2 (finisher v3): the openings and premises weighed for each piece, the one chosen and why.
    creative_choices: list[dict] = Field(default_factory=list)
    # Finisher v4: the call's turns behind Reels 2 and 3, by piece key (packs/call.py), which the checks read as sources.
    premise_material: dict = Field(default_factory=dict)


# ---- what the models return --------------------------------------------------------------------------------------------

class FinishEmail(Contract):
    subject_options: list[Text] = Field(min_length=2, max_length=4)
    preview: Text
    opening: Text
    body: Text
    ending: Text
    offer_descriptor: str | None
    cta: Literal["reply", "link", "none"]


class FinishReel(Contract):
    kind: Literal["story", "stance", "broll_text"]
    title: Text
    job: Text
    cover_text: Text
    cover_alternates: list[Text] = Field(max_length=2)
    on_screen_hook: Text
    spoken_opening: str | None
    script: str | None
    screens: list[Text] | None
    beats: list[Text] = Field(min_length=1, max_length=8)
    caption: CaptionV2
    personal_lines: list[Text] = Field(max_length=6)
    read_time_seconds: int = Field(ge=5, le=180)
    cta: Literal["none", "soft", "offer"]
    no_offer_ending: str | None
    offer_descriptor: str | None


class FinishSlide(Contract):
    number: int = Field(ge=1, le=12)
    text: Text


class FinishCarousel(Contract):
    title: Text
    slides: list[FinishSlide] = Field(min_length=7, max_length=12)
    caption: CaptionV2
    cta: Literal["none", "soft", "offer"]
    no_offer_ending: str | None
    offer_descriptor: str | None


class FinishQuote(Contract):
    piece: Literal["email", "carousel", "reel_1", "reel_2", "reel_3"]
    quote: Text
    speaker: Text


class FinishOutput(Contract):
    """What the finisher returns (pack_finish.v1): the whole pack in the v4 leaf shape, three Reels of the three kinds."""
    email: FinishEmail
    reels: list[FinishReel] = Field(min_length=3, max_length=3)
    carousel: FinishCarousel
    client_quotes: list[FinishQuote]
    stronger_with_permission: list[str]
    pack_notes: list[str]
    change_notes: list[str]

    @model_validator(mode="after")
    def three_kinds(self):
        """The composition (D43a): story, stance and b-roll text, in that order; a face-to-camera Reel has its script, a
        b-roll Reel one to three screens and no script. A breach is a schema problem, so the one repair call fixes it."""
        if [r.kind for r in self.reels] != list(REEL_KINDS):
            raise ValueError("reels must be exactly story, stance and broll_text, in that order")
        for r in self.reels:
            if r.kind == "broll_text" and (not r.screens or len(r.screens) > 3 or r.script):
                raise ValueError("the broll_text Reel has one to three screens and a null script")
            if r.kind != "broll_text" and not (r.script or "").strip():
                raise ValueError(f"the {r.kind} Reel needs its whole script")
        return self


class CheckStatement(Contract):
    piece: Literal["email", "carousel", "reel_1", "reel_2", "reel_3"]
    text: Text
    verdict: Literal["supported", "unsupported", "guardrail"]
    source: str
    why: str
    in_moment: bool | None


class CheckOutput(Contract):
    """What the fidelity check returns (pack_check.v1): every statement about the real event, each with its verdict."""
    statements: list[CheckStatement]


class Patch(Contract):
    piece: Literal["email", "carousel", "reel_1", "reel_2", "reel_3"]
    old: Text
    new: str


class RepairOutput(Contract):
    """What the repair returns (pack_repair.v1): patches for the flagged sentences only."""
    patches: list[Patch]


class CaptionOutput(Contract):
    """What the post-recording pass returns (pack_caption.v1): one Reel's caption and three cover options, written from what
    Whitney said on the recorded take."""
    cover_text: Text
    cover_alternates: list[Text] = Field(min_length=2, max_length=2)
    caption: CaptionV2
    no_offer_ending: str | None
    notes: list[str]


class FinishReelV3(Contract):
    """A Reel as finisher v3 writes it: v2's leaves with its place in the theme (central, second, third). Its premise,
    takeaway, why it differs and its times come from the plan (PlanOutput), and how it is made from its shape (a script, or
    one to three screens): the provider's grammar for this answer is at its limit, so the writing answer stays v2's size."""
    kind: Literal["central", "second", "third"]
    title: Text
    job: Text
    cover_text: Text
    cover_alternates: list[Text] = Field(max_length=2)
    on_screen_hook: Text
    spoken_opening: str | None
    script: str | None
    screens: list[Text] | None
    beats: list[Text] = Field(min_length=1, max_length=8)
    caption: CaptionV2
    personal_lines: list[Text] = Field(max_length=6)
    read_time_seconds: int = Field(ge=5, le=180)
    cta: Literal["none", "soft", "offer"]
    no_offer_ending: str | None
    offer_descriptor: str | None


class FinishOutputV3(Contract):
    """What finisher v3 writes after its plan: the whole pack, the Reels as the central story and two premises of their own."""
    email: FinishEmail
    reels: list[FinishReelV3] = Field(min_length=3, max_length=3)
    carousel: FinishCarousel
    client_quotes: list[FinishQuote]
    stronger_with_permission: list[str]
    pack_notes: list[str]
    change_notes: list[str]

    @model_validator(mode="after")
    def three_premises(self):
        if [r.kind for r in self.reels] != list(PREMISE_KINDS):
            raise ValueError("reels must be exactly central, second and third, in that order")
        for r in self.reels:
            if r.screens and r.script:
                raise ValueError(f"the {r.kind} Reel has a script and screens: a face-to-camera Reel has its script and no "
                                 "screens; an on-screen text Reel has one to three screens and a null script")
            if not (r.script or "").strip() and not 1 <= len(r.screens or []) <= 3:
                raise ValueError(f"the {r.kind} Reel needs its whole script, or one to three screens")
        if not (self.reels[0].script or "").strip():
            raise ValueError("Reel 1 (central) is face to camera: it needs its whole script")
        return self


class PlanReel(Contract):
    """One Reel as the plan sets it: its place, how it is made, its own premise, takeaway, why it differs, its times, and the
    openings weighed for it."""
    kind: Literal["central", "second", "third"]
    production: Literal["face_to_camera", "on_screen_text"]
    premise: Text
    takeaway: Text
    distinct_because: Text
    timestamps: list[Text] = Field(max_length=4)
    openings: list[Text] = Field(min_length=2, max_length=4)
    opening: Text
    why: Text


class PlanOpening(Contract):
    """The openings weighed for the email's subject or carousel slide 1, the one chosen and why."""
    piece: Literal["email", "carousel"]
    openings: list[Text] = Field(min_length=2, max_length=4)
    opening: Text
    why: Text


class PlanOutput(Contract):
    """What finisher v3's plan returns (pack-plan.v1; WIA's section 8: develop the direction, then write): each Reel's premise
    and production, and the openings weighed for every piece. The writing call follows it."""
    reels: list[PlanReel] = Field(min_length=3, max_length=3)
    openings: list[PlanOpening] = Field(max_length=2)

    @model_validator(mode="after")
    def three_premises(self):
        if [r.kind for r in self.reels] != list(PREMISE_KINDS):
            raise ValueError("reels must be exactly central, second and third, in that order")
        if self.reels[0].production != "face_to_camera":
            raise ValueError("Reel 1 (central) is face_to_camera")
        return self


class EditorialNote(Contract):
    """One thing the editorial reading found (check v4): a line that reads wrongly in public, or a piece that is not yet strong."""
    piece: Literal["email", "carousel", "reel_1", "reel_2", "reel_3"]
    text: Text
    issue: Literal[tuple(EDITORIAL_ISSUES)]
    why: Text


class PieceReading(Contract):
    """How strong one piece is, and whether it would justify publication on its own."""
    piece: Literal["email", "carousel", "reel_1", "reel_2", "reel_3"]
    strength: Literal["strong", "acceptable", "weak"]
    why: Text


class CheckOutputV4(Contract):
    """What check v4 returns: v3's statements, the editorial notes and a reading of each piece."""
    statements: list[CheckStatement]
    editorial: list[EditorialNote]
    pieces: list[PieceReading]


OUTPUTS = {"pack_finish": FinishOutput, "pack_check": CheckOutput, "pack_recheck": CheckOutput, "pack_repair": RepairOutput,
           "pack_caption": CaptionOutput, "pack_refinish": FinishOutput}
# A profile whose answer differs from its stage's first one (Round 2). Every earlier profile keeps OUTPUTS[stage], so its
# schema, and its saved answers, are unchanged.
PROFILE_OUTPUTS = {"2026-10-27.pack-finish.v3": FinishOutputV3, "2026-10-27.pack-check.v4": CheckOutputV4,
                   "2026-10-27.pack-refinish.v2": FinishOutputV3, "2026-10-27.pack-plan.v1": PlanOutput,
                   "2026-10-27.pack-finish.v4": FinishOutputV3, "2026-10-27.pack-refinish.v3": FinishOutputV3,
                   "2026-10-27.pack-plan.v2": PlanOutput}


def output_model(stage: str, profile: str | None = None):
    """The answer model of a stage under a prompt profile."""
    return PROFILE_OUTPUTS.get(profile) or OUTPUTS[stage]

_UNSUPPORTED = ("pattern", "minLength", "maxLength", "title", "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum",
                "default")


def _plain(node):
    """A schema node without the keywords Anthropic refuses. Property names are data, never keywords: a field named `title`
    (a Reel's working title) stays."""
    if isinstance(node, dict):
        out = {}
        for k, v in node.items():
            if k in ("properties", "$defs"):
                out[k] = {name: _plain(sub) for name, sub in v.items()}
            elif k not in _UNSUPPORTED:
                out[k] = _plain(v)
        if out.get("minItems", 0) > 1:
            out.pop("minItems")
        out.pop("maxItems", None)
        return out
    return [_plain(v) for v in node] if isinstance(node, list) else node


def wire_schema(stage: str, profile: str | None = None) -> dict:
    """A stage's answer schema as sent to the model: the full schema without length bounds, patterns, numeric bounds and
    titles (Anthropic's structured output refuses them; plan section 5.4). The answer is still validated in full."""
    return _plain(output_model(stage, profile).model_json_schema())


# ---- the API's request bodies ------------------------------------------------------------------------------------------

class PackCreate(Mutation):
    """Create or retry the pack for an approved v4 brief (POST /briefs/{id}/pack)."""
    expected_brief_hash: str | None = Field(default=None, max_length=128)
    # A pattern, not a Literal: typing caches Literal["replay", "live"] and Literal["live", "replay"] as one object, so the
    # published enum's order would depend on which module was imported first.
    mode: str | None = Field(default=None, pattern=r"^(replay|live)$")


class PackEdit(Mutation):
    """A person's edit of one piece: {path: new value}, paths relative to the piece's content (section 5.6). `reason` (Round 2,
    WIA's section 9) is why, in the person's words: it stays with the edit and the weekly learning loop reads it."""
    expected_manifest_hash: str = Field(min_length=1, max_length=128)
    changes: dict[str, object] = Field(min_length=1, max_length=40)
    reason: str | None = Field(default=None, max_length=1000)


class PackRevert(Mutation):
    """Use the brief's line for these paths of one piece."""
    expected_manifest_hash: str = Field(min_length=1, max_length=128)
    paths: list[str] = Field(min_length=1, max_length=40)


class PackClearance(Mutation):
    """Mark a before-publishing note done (P1 to P5, N1...) or a client quote cleared (Q1...): the client's okay, a quote
    cleared, a fact checked. Never a gate; recorded with person, date and reference."""
    expected_manifest_hash: str = Field(min_length=1, max_length=128)
    item_id: str = Field(min_length=1, max_length=40)
    reference: str | None = Field(default=None, max_length=1000)
    note: str | None = Field(default=None, max_length=2000)


class PackAttest(Mutation):
    """Attest that a flagged sentence is true (R57): it clears the finding, recorded as attested. On an editorial finding
    (Round 2) the statement is why the line is fine as it is: the finding is kept, never a fact."""
    expected_manifest_hash: str = Field(min_length=1, max_length=128)
    statement: str = Field(min_length=3, max_length=2000)


class PackFinishAgain(Mutation):
    """Finish the pack again: a new run with no new instruction, every person's line kept (section 4.5)."""
    expected_manifest_hash: str = Field(min_length=1, max_length=128)


class PackRecordedTake(Mutation):
    """The post-recording pass (NP.B14): what Whitney said on a face-to-camera Reel's recorded take. It becomes the Reel's
    script word for word, locked as the person's, and the caption and covers are written from it."""
    expected_manifest_hash: str = Field(min_length=1, max_length=128)
    said: str = Field(min_length=40, max_length=20000)


class PackGrantIn(Contract):
    """One granted item (S1, S2... in the order the pack lists "stronger with permission") or a stated fact (no item), in the
    person's own words."""
    item_id: str | None = Field(default=None, pattern=r"^S\d{1,2}$")
    statement: str = Field(min_length=3, max_length=2000)


class PackRefinish(Mutation):
    """Finish again with a permission (NP.B15): the finisher re-runs with the granted items and stated facts as evidence
    (attested, R57), keeping every person's line."""
    expected_manifest_hash: str = Field(min_length=1, max_length=128)
    grants: list[PackGrantIn] = Field(min_length=1, max_length=10)


class PackDecisionV2(Mutation):
    """Ready to publish (bound to the manifest) or back to review."""
    expected_manifest_hash: str = Field(min_length=1, max_length=128)
    decision: Literal["ready_to_publish", "in_review"]
    note: str | None = Field(default=None, max_length=4000)


class PackMarkPublished(Mutation):
    """A piece marked published: its date, channel and final text, recorded through capture outside the pack's copy."""
    published_on: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    channel: Literal["email", "instagram", "facebook"]
    final_text: str = Field(min_length=1, max_length=40000)
    url: str | None = Field(default=None, max_length=2000)


# ---- helpers both tracks use -------------------------------------------------------------------------------------------

def channel_of(key: str) -> str:
    return CHANNEL[key]


def stages_for(pass_kind: str | None = None) -> tuple[str, ...]:
    """A run's stages: the six of a pack run, with a pass's own writer step in the finisher's place."""
    if not pass_kind:
        return STAGES
    return (STAGES[0], PASSES[pass_kind], *STAGES[2:])


def is_editable(channel: str, path: str) -> bool:
    """Whether a person may edit this path of a piece of this channel."""
    head = re.split(r"[.\[]", path, maxsplit=1)[0]
    if head not in EDITABLE[channel]:
        return False
    if head == "slides":
        return bool(SLIDE_LEAF.match(path))
    return True


_BRIEF_PATH = re.compile(r"^format_plan\.(email|carousel|reels\[(\d{1,2})\])(?:\.(.+)|(\[.+))?$")


def translate_lock(brief_path: str) -> tuple[str, str | None] | None:
    """A Gate 2 lock path (0-based, as briefs/paths.py writes it) as (brief piece key, path in the piece's copy), or None
    when it is not in the format plan. The brief piece key is the hand-off's (`reel_1` for reels[0]); the pack maps it to
    its own key by the Reel's kind. A lock on a whole piece returns a None path; a lock on the whole format plan returns
    ("*", None)."""
    if brief_path == "format_plan":
        return "*", None
    m = _BRIEF_PATH.match(brief_path)
    if not m:
        return None
    piece = f"reel_{int(m.group(2)) + 1}" if m.group(2) is not None else m.group(1)
    rest = m.group(3) or (m.group(4) or "")
    return piece, (rest or None)
