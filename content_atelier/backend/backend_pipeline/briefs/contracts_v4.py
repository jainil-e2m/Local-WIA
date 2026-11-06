"""Brief contract version 4 (E.B33; plan section 4.3, R59, R60; D30).

Version 3 wrote one caption for the whole brief, no on-screen hooks, no carousel title and no send header, and its writer
asked each Reel for "a distinct point", which produced the micro-lessons WIA rejected on 20 October. Version 4 is the brief
WIA reviewed that day, in the 13 October order:

- the brief: central point; strategic purpose and desired response; audience and reason to care; WIA perspective; the
  supporting example with its timestamps, its one moment's details and who did what; the narrative outline; CTA and
  essential boundaries (before publishing);
- then the finished copy of every asset (`format_plan`), each with its job (the format and creative approach): every Reel
  has a `kind` (story, stance, broll_text: the same idea through different doors), a cover, an on-screen hook, its own
  caption and, for b-roll, one to three `screens`; the carousel has a `title` and its own caption; the email has its send
  header (DATE, SEND TIME, RECIPIENTS, proposed for WIA to confirm). Every asset names its `register` and, where it names
  an offer, the offer's approved `offer_descriptor`. Two Reels are allowed when the idea does not support three (D30).

The ledger is v3's, built after writing (ledger_v3), over v4's copy fields; a fact an approver attested at a gate binds a
statement as `attested` (R57). The checks are v3's plus the first-touch rules (E.B34, briefs/first_touch.py) and the asset
checks (E.B24's extension, briefs/asset_checks.py). Field paths in findings and locks are dotted with 0-based list indexes
(`format_plan.reels[1].cover_text`, `format_plan.email.subject_options[0]`), the paths the Gate 2 editor writes.
"""
from __future__ import annotations

import warnings
from typing import Literal

from pydantic import Field, model_validator

from ..contracts import Contract, Text
from .contracts import NumericFact
from .contracts_v2 import ApprovedAngle, AudienceSection, BeforePublishing, BriefCTA, EvidenceRef, NarrativeOutline, SharpenedPoint, StoriesPlan
from .contracts_v3 import COPY, DIRECTION, Attestation, CaptionPlanV3, IntendedShiftV3, LedgerFlag, SlideV3

# `register` is the plan's field name (E.B33); on a model it shadows ABCMeta.register only on the class, never on an
# instance, so pydantic's warning about it is silenced here and every `register` field is declared required.
warnings.filterwarnings("ignore", message='Field name "register"', category=UserWarning)

SCHEMA_V4 = "brief_document_v4"
REEL_KINDS = ("story", "stance", "broll_text")
# How an asset is written (section 4.3): a face-to-camera script is spoken; b-roll screens and covers are on-screen text;
# the email, captions and carousel slides are written, clean and declarative.
REGISTERS = ("spoken", "on_screen", "written")
OFFER_DESCRIPTOR = ("Where this asset names an offer: that offer's approved descriptor, word for word from the offer "
                    "descriptors in the knowledge base; null when it names none")


class StrategicPurposeV4(Contract):
    pillar: Literal["ATTRACT", "WARM", "CONVERT"]
    content_type: Text
    why_now: Text = Field(description=DIRECTION + "Why this piece matters for WIA now")
    desired_response: Text = Field(description=DIRECTION + "What the ideal reader thinks afterwards, in their own words, "
                                                           "for example \"That's the kind of team I'd trust with my ad budget\"")


class Credit(Contract):
    """One beat of the story and who did it, as the call (or a fact Whitney attested) names them (first-touch rule 5)."""
    actor: Text = Field(description="Who did it: the client, her AI assistant, our strategist, Whitney, our team")
    did: Text = Field(description="What they did, in a few words")


class SupportingExampleV4(Contract):
    scene: Text = Field(description=COPY + "The one real moment, told as a short anonymised story")
    wia_move: Text = Field(description=COPY + "What WIA noticed, asked, decided or did")
    client_contribution: Text = Field(description=COPY + "What the owner contributed")
    timestamps: list[Text] = Field(max_length=6, description=DIRECTION + "Where the moment is in the call, as m:ss or "
                                                                          "m:ss to m:ss, each with what happens there")
    details: list[Text] = Field(max_length=2, description=DIRECTION + "The one or two concrete details the copy uses; "
                                                                      "never more than two")
    credits: list[Credit] = Field(min_length=1, max_length=4, description=DIRECTION + "Who did what, beat by beat, as "
                                                                                     "the call or an attested fact names them")


class ReelPlanV4(Contract):
    kind: Literal["story", "stance", "broll_text"] = Field(description="story: the moment, face to camera; stance: WIA's "
                                                                     "view of it, face to camera; broll_text: b-roll with "
                                                                     "one to three screens of on-screen text")
    job: Text = Field(description=DIRECTION + "What this Reel does for the reader: the same idea through its own door")
    register: Literal["spoken", "on_screen"] = Field(description="spoken for a face-to-camera Reel; on_screen for b-roll")
    cover_text: Text = Field(description=COPY + "The cover: a short, specific statement naming the concrete subject")
    on_screen_hook: Text = Field(description=COPY + "The text on screen in the first seconds, naming the concrete subject")
    spoken_opening: str | None = Field(description=COPY + "The first spoken line; null for b-roll")
    script: str | None = Field(description=COPY + "For a new face-to-camera script: the whole script, start to end, as "
                                                  "Whitney would say it. Null for b-roll and an existing clip")
    screens: list[Text] | None = Field(max_length=3, description=COPY + "For b-roll only: one to three screens of "
                                                                         "on-screen text telling the turn of the story; "
                                                                         "null otherwise")
    beats: list[Text] = Field(min_length=1, max_length=8, description=DIRECTION + "The beats in order; for an existing "
                                                                                 "clip, the exact start and end lines")
    personal_lines: list[Text] = Field(max_length=3, description=DIRECTION + "Lines of personal reaction in the script, "
                                                                            "for Whitney to keep or cut")
    read_time_seconds: int = Field(ge=5, le=180)
    source: Literal["existing_clip", "new_script"]
    caption: CaptionPlanV3 | None = Field(description=COPY + "This Reel's own caption; null only outside the caption channel")
    offer_descriptor: str | None = Field(description=OFFER_DESCRIPTOR)


class CarouselPlanV4(Contract):
    job: Text = Field(description=DIRECTION + "What the carousel does for the reader: it goes deeper than the Reels")
    register: Literal["written"] = Field(description="written: slides and captions are clean and declarative")
    title: Text = Field(description=COPY + "The carousel's title; slide 1 carries its promise")
    slides: list[SlideV3] = Field(min_length=7, max_length=12)
    caption: CaptionPlanV3 | None = Field(description=COPY + "The carousel's own caption; null only outside the caption channel")
    offer_descriptor: str | None = Field(description=OFFER_DESCRIPTOR)


class SendHeader(Contract):
    """Proposed for WIA to confirm; scheduling is downstream (section 4.3)."""
    date: Text = Field(description=DIRECTION + "DATE: the proposed send date, for WIA to confirm")
    send_time: Text = Field(description=DIRECTION + "SEND TIME: the proposed send time, for WIA to confirm")
    recipients: Text = Field(description=DIRECTION + "RECIPIENTS: the proposed list or segment, for WIA to confirm")


class EmailPlanV4(Contract):
    job: Text = Field(description=DIRECTION + "What the email does: it tells the whole story and stands alone")
    register: Literal["written"] = Field(description="written: the email reads like her sent emails, never spoken")
    send_header: SendHeader
    subject_options: list[Text] = Field(min_length=2, max_length=4, description=COPY + "Two to four subject lines, best "
                                                                                      "first")
    preview: Text = Field(description=COPY + "The preview text")
    opening: Text = Field(description=COPY + "The greeting and the opening scene")
    body: Text = Field(description=COPY + "The rest of the email in short flowing paragraphs separated by blank lines, "
                                          "with one bold key line; no bullet lists")
    ending: Text = Field(description=COPY + "The CTA paragraph and the sign-off")
    offer_descriptor: str | None = Field(description=OFFER_DESCRIPTOR)


class FormatPlanV4(Contract):
    reels: list[ReelPlanV4] = Field(max_length=3)
    carousel: CarouselPlanV4 | None
    email: EmailPlanV4 | None
    stories: StoriesPlan | None


class BriefWriteV4(Contract):
    """What writer v5 returns, in the 13 October order: the brief, then the finished copy of every asset."""
    approved_angle: ApprovedAngle
    sharpened_point: SharpenedPoint | None
    central_point: Text = Field(description="The idea's point in one sentence: a WIA belief, standard or client "
                                            "experience, never a platform or tactic")
    strategic_purpose: StrategicPurposeV4
    intended_shift: IntendedShiftV3
    audience: AudienceSection
    point_of_view: Literal["we", "I"]
    wia_perspective: Text = Field(description=COPY + "WIA's belief or practice, as Whitney would say it")
    supporting_example: SupportingExampleV4
    narrative_outline: NarrativeOutline
    cta: BriefCTA
    cta_why: Text
    before_publishing: list[BeforePublishing] = Field(max_length=5)
    format_plan: FormatPlanV4


# Writer v5.1 (NP.B10, D43j; D30 superseded): the same contract, written with exactly three Reels, one of each kind in the
# pack's order, whenever the reel channel is confirmed. Its own answer model and wire schema, so a v5 run's request (prompt,
# schema, payload) stays byte for byte what N2 recorded and replays from its cache.
THREE_REELS = list(REEL_KINDS)


class BriefWriteV51(BriefWriteV4):
    """What writer v5.1 returns: v5's answer, with the Reels empty (no reel channel) or story, stance and broll_text."""

    @model_validator(mode="after")
    def three_reels(self):
        """A breach is a schema problem, so the llm module's one repair call fixes it before the brief's checks run."""
        reels = self.format_plan.reels
        if reels and [r.kind for r in reels] != THREE_REELS:
            raise ValueError("format_plan.reels must be exactly story, stance and broll_text, in that order")
        for r in reels:
            if r.kind == "broll_text" and (not r.screens or r.script):
                raise ValueError("the broll_text Reel has one to three screens and a null script")
        return self


# The ledger -------------------------------------------------------------------------------------------------------
# v3's statuses, `attested` included: a fact an approver stated at a gate, with the person and date (R57, 5.B7).


class LedgerClaimV4(Contract):
    claim_id: Text
    text: Text
    claim_class: Literal["particular_interaction", "general_approach", "recommendation", "prevalence", "outcome",
                         "attributed_experience"]
    evidence_ids: list[Text]
    knowledge_base_document: str | None
    numeric_facts: list[NumericFact]
    quote: str | None
    public_quote: bool
    field: Text
    status: Literal["bound", "supported", "unsupported", "unchecked", "kept_by_person", "attested"]
    settled_by: Literal["deterministic", "verifier", "person", "none"]
    note: str | None
    flag: LedgerFlag | None
    attested: Attestation | None = None


class BriefBodyV4(BriefWriteV4):
    # A brief written by v5.3 keeps its plan's own shape (the central story and two premises); every earlier brief validates
    # as FormatPlanV4 and dumps exactly as stored.
    format_plan: FormatPlanV4 | FormatPlanV5
    evidence: list[EvidenceRef]
    claims: list[LedgerClaimV4]


class BriefHeaderV4(Contract):
    schema_version: Literal["brief_document_v4"]
    angle_id: Text
    angle_hash: Text
    purpose: Literal["ATTRACT", "WARM", "CONVERT"]
    content_type: Text
    audience: Text
    intended_shift: IntendedShiftV3
    point_of_view: Literal["we", "I"]
    cta: BriefCTA
    channels: list[Text]
    pinned_inputs: dict


class BriefDocumentV4(Contract):
    header: BriefHeaderV4
    body: BriefBodyV4


# A person edits any writer section at Gate 2 (the approved angle and the CTA have their own routes); the ledger is rebuilt.
WRITER_FIELDS_V4 = tuple(BriefWriteV4.model_fields)
EDITABLE_V4 = set(WRITER_FIELDS_V4) - {"approved_angle", "cta"}


def writer_schema_v4(channels, model=BriefWriteV4):
    """The writer's schema with formats outside the confirmed channel set forced to null, and captions to null when the
    caption channel is not confirmed."""
    schema = model.model_json_schema()
    defs = schema["$defs"]
    plan = defs["FormatPlanV4"]["properties"]
    if "reel" not in channels:
        plan["reels"]["maxItems"] = 0
    for name in ("carousel", "email", "stories"):
        if name not in channels:
            plan[name] = {"type": "null", "title": plan[name].get("title", name)}
    if "caption" not in channels:
        for owner in ("ReelPlanV4", "CarouselPlanV4"):
            defs[owner]["properties"]["caption"] = {"type": "null", "title": "Caption"}
    return schema


def writer_schema_v51(channels):
    """Writer v5.1's schema: v4's, with exactly three Reels when the reel channel is confirmed. The order of the kinds is
    BriefWriteV51's check, which the answer is validated against."""
    schema = writer_schema_v4(channels, BriefWriteV51)
    reels = schema["$defs"]["FormatPlanV4"]["properties"]["reels"]
    if "reel" in channels:
        reels.update(minItems=3, maxItems=3, description="Exactly three Reels, one of each kind, in this order: story, "
                                                         "stance, broll_text")
    return schema


# Writer v5.3 (Round 2, WIA's feedback of 26 October 2026) ---------------------------------------------------------------
# WIA kept the five pieces (one email, three Reels, one carousel) and asked for creative variety inside them: the email, the
# carousel and Reel 1 share the central story, each developed for its format; Reels 2 and 3 each carry a premise of their
# own from the source material (a process behind the scenes, a strategic decision, an observation, a teaching moment),
# never a paraphrase of Reel 1. "B-roll and on-screen text are production choices, not creative angles": a Reel's
# `production` is separate from its `kind`, which is now its place in the theme (central, second, third). Every Reel says
# its premise, its takeaway and why it differs from the other two, and the writer lists the premises it weighed before
# choosing (`premise_options`). Its own Reel and plan models, so every earlier writer's schema is byte for byte unchanged.
PREMISE_KINDS = ("central", "second", "third")
PRODUCTIONS = ("face_to_camera", "on_screen_text")
PREMISE_TYPES = ("client_story", "behind_the_scenes", "strategic_decision", "observation", "teaching", "owner_question")


class ReelPlanV5(Contract):
    kind: Literal["central", "second", "third"] = Field(description="central: Reel 1, the central story told face to "
                                                                     "camera; second and third: Reels 2 and 3, each with "
                                                                     "its own premise from the source material")
    production: Literal["face_to_camera", "on_screen_text"] = Field(description="How it is made, chosen for the premise: "
                                                                                 "face_to_camera (a spoken script) or "
                                                                                 "on_screen_text (one to three screens over "
                                                                                 "b-roll). Reel 1 is face_to_camera. Never "
                                                                                 "what makes two Reels different")
    premise: Text = Field(description=DIRECTION + "This Reel's own premise in one sentence: the question, insight or "
                                                  "perspective it gives a viewer. For Reels 2 and 3, one that merits its "
                                                  "own piece, never Reel 1's story or point said another way")
    takeaway: Text = Field(description=DIRECTION + "What an owner takes away from this Reel, in their words")
    distinct_because: Text = Field(description=DIRECTION + "Why this Reel differs from the other two: a different "
                                                           "question, insight or perspective, never a different format")
    timestamps: list[Text] = Field(max_length=4, description=DIRECTION + "Where this Reel's material is in the calls, as "
                                                                          "m:ss or m:ss to m:ss, each with what happens "
                                                                          "there")
    job: Text = Field(description=DIRECTION + "What this Reel does for the reader")
    register: Literal["spoken", "on_screen"] = Field(description="spoken for face_to_camera; on_screen for on_screen_text")
    cover_text: Text = Field(description=COPY + "The cover: a short, specific statement naming the concrete subject")
    on_screen_hook: Text = Field(description=COPY + "The text on screen in the first seconds, naming the concrete subject")
    spoken_opening: str | None = Field(description=COPY + "The first spoken line; null for on_screen_text")
    script: str | None = Field(description=COPY + "For a face_to_camera Reel: the whole script, start to end, as Whitney "
                                                  "would say it. Null for on_screen_text and an existing clip")
    screens: list[Text] | None = Field(max_length=3, description=COPY + "For on_screen_text only: one to three screens "
                                                                         "that carry this Reel's premise on their own; "
                                                                         "null otherwise")
    beats: list[Text] = Field(min_length=1, max_length=8, description=DIRECTION + "The beats in order; for an existing "
                                                                                 "clip, the exact start and end lines")
    personal_lines: list[Text] = Field(max_length=3, description=DIRECTION + "Lines of personal reaction in the script, "
                                                                            "for Whitney to keep or cut")
    read_time_seconds: int = Field(ge=5, le=180)
    source: Literal["existing_clip", "new_script"]
    caption: CaptionPlanV3 | None = Field(description=COPY + "This Reel's own caption; null only outside the caption channel")
    offer_descriptor: str | None = Field(description=OFFER_DESCRIPTOR)


class PremiseOption(Contract):
    """A premise the writer weighed for the Reels (WIA's question 4: compare approaches, not the first plausible draft)."""
    premise: Text = Field(description=DIRECTION + "The premise in one sentence")
    type: Literal["client_story", "behind_the_scenes", "strategic_decision", "observation", "teaching", "owner_question"]
    material: Text = Field(description=DIRECTION + "The material in the calls it rests on, with its times")
    used_for: Literal["reel_1", "reel_2", "reel_3"] | None = Field(description="The Reel it became, or null when not used")
    why: Text = Field(description=DIRECTION + "Why it was chosen, or why not: independence from the other Reels, the "
                                              "strength of its material, how it reads in public")


class FormatPlanV5(Contract):
    premise_options: list[PremiseOption] = Field(max_length=6, description="Three to six premises weighed for the Reels, "
                                                                          "from different parts of the material, before "
                                                                          "choosing; empty without the reel channel")
    reels: list[ReelPlanV5] = Field(max_length=3)
    carousel: CarouselPlanV4 | None
    email: EmailPlanV4 | None
    stories: StoriesPlan | None


class BriefWriteV53(BriefWriteV4):
    """What writer v5.3 returns: v5.2's brief, with the Reels as the central story and two premises of their own."""
    format_plan: FormatPlanV5

    @model_validator(mode="after")
    def three_premises(self):
        """A breach is a schema problem, so the llm module's one repair call fixes it before the brief's checks run."""
        reels = self.format_plan.reels
        if reels and [r.kind for r in reels] != list(PREMISE_KINDS):
            raise ValueError("format_plan.reels must be exactly central, second and third, in that order")
        for r in reels:
            reel_shape(r)
        if reels and reels[0].production != "face_to_camera":
            raise ValueError("Reel 1 (central) is face_to_camera")
        if reels and len(self.format_plan.premise_options) < 3:
            raise ValueError("format_plan.premise_options lists at least three premises weighed for the Reels")
        return self


# How a Reel is named for a reader (the review document, the brief's export, the pack's document).
KIND_WORDS = {"story": "face to camera (story)", "stance": "face to camera (stance)", "broll_text": "b-roll with on-screen text",
              "central": "the central story", "second": "a premise of its own", "third": "a premise of its own"}
PRODUCTION_WORDS = {"face_to_camera": "face to camera", "on_screen_text": "on-screen text over b-roll"}


def format_words(reel: dict) -> str | None:
    """A Reel's place and how it is made, in words: "the central story, face to camera"; before v5.3, its kind."""
    kind, production = reel.get("kind"), reel.get("production")
    if production:
        return f"{KIND_WORDS.get(kind, kind)}, {PRODUCTION_WORDS.get(production, production)}"
    return KIND_WORDS.get(kind) if kind else None


def premise_lines(reel: dict) -> list[tuple[str, str]]:
    """A v5.3 Reel's premise, takeaway and why it differs, as (label, text); none for an earlier Reel."""
    return [(label, reel[key]) for key, label in (("premise", "Premise"), ("takeaway", "Takeaway"),
                                                   ("distinct_because", "Why it differs")) if reel.get(key)]


def on_screen(reel) -> bool:
    """Whether a Reel is on-screen text over b-roll: its `production` (writer v5.3) or, before it, its kind."""
    get = reel.get if isinstance(reel, dict) else (lambda name: getattr(reel, name, None))
    return get("production") == "on_screen_text" or get("kind") == "broll_text"


class BriefEditV4(BriefWriteV4):
    """A person's edit of a v4 brief at Gate 2: the writer's sections in either plan shape (writer v5.3's premises or the
    earlier Reels), held to no writer's Reel rule; the checks say what an edit breaks instead."""
    format_plan: FormatPlanV4 | FormatPlanV5


def reel_shape(r) -> None:
    """A Reel's copy fits its production: a spoken script, or one to three screens and no script."""
    if r.production == "on_screen_text" and (not r.screens or r.script):
        raise ValueError(f"the {r.kind} Reel is on_screen_text: one to three screens and a null script")
    if r.production == "face_to_camera" and r.source == "new_script" and not (r.script or "").strip():
        raise ValueError(f"the {r.kind} Reel is face_to_camera: it needs its whole script")


def writer_schema_v53(channels):
    """Writer v5.3's schema: v4's channel rules on v5.3's plan, with exactly three Reels when the reel channel is confirmed."""
    schema = BriefWriteV53.model_json_schema()
    defs = schema["$defs"]
    plan = defs["FormatPlanV5"]["properties"]
    if "reel" not in channels:
        plan["reels"]["maxItems"] = 0
        plan["premise_options"]["maxItems"] = 0
    else:
        plan["reels"].update(minItems=3, maxItems=3, description="Exactly three Reels, in this order: central, second, "
                                                                 "third")
    for name in ("carousel", "email", "stories"):
        if name not in channels:
            plan[name] = {"type": "null", "title": plan[name].get("title", name)}
    if "caption" not in channels:
        for owner in ("ReelPlanV5", "CarouselPlanV4"):
            defs[owner]["properties"]["caption"] = {"type": "null", "title": "Caption"}
    return schema


def writer_part_v4(body: dict) -> dict:
    """The writer's sections of a v4 body (a repair or a revision is given these, never the ledger)."""
    return {k: body[k] for k in WRITER_FIELDS_V4 if k in body}


def is_v4_body(body) -> bool:
    b = body if isinstance(body, dict) else body.model_dump(mode="json")
    return "central_point" in b


def _caption_fields(path: str, label: str, caption: dict | None) -> list[tuple[str, str, str]]:
    if not caption:
        return []
    return [(f"{path}.caption.{k}", f"{label}'s caption {k}", caption[k]) for k in ("hook", "body", "ending")]


def copy_fields_v4(body, *, wide: bool = False) -> list[tuple[str, str, str]]:
    """The reader-facing copy of a v4 brief as (ledger field, label for the reviewer, text), for the ledger (ledger_v3). The
    ledger's field names follow v3's: Reels and hooks numbered from 1 and slides by their number, which
    `ledger_v3.field_path` turns into a path; a subject line, a screen and a caption part are named by their path. `wide`
    adds the central point, the outline's directions, the Reel beats and the Stories frames, which become copy too."""
    b = body if isinstance(body, dict) else body.model_dump(mode="json")
    out = []
    if wide:
        out.append(("central_point", "the central point", b["central_point"]))
    out.append(("wia_perspective", "the WIA perspective", b["wia_perspective"]))
    out += [(f"supporting_example.{k}", "the supporting example", b["supporting_example"][k]) for k in ("scene", "wia_move", "client_contribution")]
    outline = b["narrative_outline"]
    out += [(f"narrative_outline.hooks[{i}]", f"hook {i}", h["text"]) for i, h in enumerate(outline["hooks"], 1)]
    if wide:
        out += [("narrative_outline.problems_desires_symptoms", "the problems and desires", " ".join(outline["problems_desires_symptoms"])),
                ("narrative_outline.main_point", "the main point", outline["main_point"]),
                ("narrative_outline.transformation", "the transformation", outline["transformation"]),
                ("narrative_outline.cta", "the outline's CTA", outline["cta"])]
    plan = b["format_plan"]
    for i, r in enumerate(plan.get("reels") or [], 1):
        path, label = f"format_plan.reels[{i}]", f"Reel {i}"
        out += [(f"{path}.cover_text", f"{label}'s cover", r["cover_text"]),
                (f"{path}.on_screen_hook", f"{label}'s on-screen hook", r["on_screen_hook"])]
        if r.get("spoken_opening"):
            out.append((f"{path}.spoken_opening", f"{label}'s spoken opening", r["spoken_opening"]))
        if r.get("script"):
            out.append((f"{path}.script", f"{label}'s script", r["script"]))
        out += [(f"{path}.screens[{j}]", f"{label}'s screen {j + 1}", s) for j, s in enumerate(r.get("screens") or [])]
        out += _caption_fields(path, label, r.get("caption"))
        if wide:
            out.append((f"{path}.beats", f"{label}'s beats", "\n".join(r["beats"])))
    if c := plan.get("carousel"):
        out.append(("format_plan.carousel.title", "the carousel's title", c["title"]))
        out += [(f"format_plan.carousel.slides[{s['number']}].text", f"carousel slide {s['number']}", s["text"]) for s in c["slides"]]
        out += _caption_fields("format_plan.carousel", "the carousel", c.get("caption"))
    if e := plan.get("email"):
        out += [(f"format_plan.email.subject_options[{j}]", f"the email's subject line {j + 1}", s) for j, s in enumerate(e["subject_options"])]
        out += [(f"format_plan.email.{k}", f"the email's {k}", e[k]) for k in ("preview", "opening", "body", "ending")]
    if plan.get("stories") and wide:
        out.append(("format_plan.stories.frames", "the Stories frames", "\n".join(plan["stories"]["frames"])))
    return out
