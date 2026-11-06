"""SQL capabilities are independent of the legacy prompt-testing switches."""
from __future__ import annotations

import os
from pathlib import Path
from . import settings_store
from .config import BACKEND_ROOT, embedding_contract
from .settings_store import LoadedSettings, default
from .store import canonical_hash


def _names(name):
    return tuple(x.strip() for x in os.getenv(name, '').split(',') if x.strip())


class StorageSettings(LoadedSettings):
    """The storage-side configuration. Behavioural fields default to the settings registry's defaults (equal to the
    documented defaults) and come from the settings table or the legacy environment in `from_env`; secrets, paths,
    the allow-lists and the safety catches (generation, encoding, brief generation, pack generation) are read from
    the environment only."""
    database_url: str = "postgresql://atelier:atelier_local_only@127.0.0.1:15432/atelier"
    artifact_root: Path = BACKEND_ROOT / ".storage-artifacts"
    generation_enabled: bool = False
    encoding_enabled: bool = False
    refinement_enabled: bool = False
    api_secret: str = ""
    synthetic: bool = False
    lease_seconds: int = 120
    brief_enabled: bool = default("features.briefs")
    brief_live_enabled: bool = False
    brief_web_enabled: bool = False
    brief_approvers: tuple[str, ...] = ()
    brief_editors: tuple[str, ...] = ()
    brief_brand_path: Path | str | None = None  # a file, or artifact:<key> in the artifact store (artifacts.read_reference)
    brief_model: str | None = default("models.brief")
    brief_review_model: str | None = default("models.brief_review")
    brief_max_characters: int = default("briefs.max_characters")
    # Brief contract for new runs (E.B15): version 1 stays the default until the v2 writer has its benchmark result.
    brief_schema: str = default("prompts.profile.brief")
    # The v2 writer's prompt (E.B22), frozen with each run.
    brief_writer: str = default("prompts.profile.brief_writer")
    # The channel set WIA confirmed for v2 format plans (format guide; rulings R-10, R-11).
    brief_channels: tuple[str, ...] = default("briefs.channels")
    angle_approval_cutoff: float | None = default("matching.approval_cutoff")
    packs_enabled: bool = default("features.packs")
    pack_live_enabled: bool = False
    pack_writer_model: str | None = default("models.pack_writer")
    pack_review_model: str | None = default("models.pack_review")
    # Content pack v2 (NP.B5): the prompt profiles and how the finisher runs (finish, missing_only, assemble).
    pack_finish_profile: str = default("prompts.profile.pack_finish")
    pack_check_profile: str = default("prompts.profile.pack_check")
    pack_repair_profile: str = default("prompts.profile.pack_repair")
    pack_caption_profile: str = default("prompts.profile.pack_caption")
    pack_refinish_profile: str = default("prompts.profile.pack_refinish")
    pack_finish_mode: str = default("packs.finish_mode")
    pack_editors: tuple[str, ...] = ()
    pack_approvers: tuple[str, ...] = ()
    calendar_enabled: bool = default("features.calendar")
    calendar_timezone: str = default("display.timezone")
    calendar_schedulers: tuple[str, ...] = ()
    # Phase L (section 4.12): the review queue and knowledge screens stay behind this flag until the phase exits.
    context_enabled: bool = default("features.context")
    # Who may confirm identity changes (rules, exemplars, voice) and approve versions that carry them: Whitney
    # (rulings 2.5). Empty means the brief approvers.
    identity_approvers: tuple[str, ...] = ()
    # Intake administrators (ATELIER_INTAKE_ADMINS): the administrators of the legacy lists (0.B9, gates/roles.py).
    intake_admins: tuple[str, ...] = ()
    # WIA's own reviewers (ATELIER_WIA_REVIEWERS: emails or names; Whitney and the reviewers she names, R50). A gate
    # decision is WIA's judgement only when its actor or named author is one of them; anything else (a decision
    # recorded under D12's delegation) is kept, with a proxy label that never calibrates as WIA's (section 2.3).
    wia_reviewers: tuple[str, ...] = ()

    def explicit_model_gaps(self) -> list[str]:
        """Brief models left at the code default (section 4.10): none for an object built by hand."""
        return settings_store.explicit_model_gaps(storage=self, brief=True)

    @classmethod
    def from_env(cls, conn=None, *, database_url: str | None = None):
        """Build the storage settings: the one environment reader (settings_store.load_env_files), then the legacy
        environment and the settings table for the behavioural fields. The table is read from `conn`,
        `database_url` or ATELIER_DATABASE_URL when one is set."""
        return cls.from_effective(settings_store.load(conn, database_url=database_url))

    @classmethod
    def from_effective(cls, eff):
        values = {d.field: eff.values[d.key] for d in settings_store.DEFINITIONS
                  if "storage" in (d.target or "").split("+") and d.field}
        return cls(database_url=os.getenv("ATELIER_DATABASE_URL", cls.model_fields["database_url"].default),
                   artifact_root=os.getenv("ATELIER_ARTIFACT_ROOT", str(BACKEND_ROOT / ".storage-artifacts")),
                   generation_enabled=os.getenv("ATELIER_ALLOW_GENERATION") == "true",
                   encoding_enabled=os.getenv("ATELIER_ALLOW_ENCODING") == "true",
                   refinement_enabled=os.getenv("ATELIER_ALLOW_REFINEMENT") == "true",
                   api_secret=os.getenv("ATELIER_API_SECRET", ""),
                   brief_live_enabled=os.getenv('ATELIER_ALLOW_BRIEF_GENERATION') == 'true',
                   brief_web_enabled=os.getenv('ATELIER_ALLOW_BRIEF_WEB') == 'true',
                   brief_approvers=_names('ATELIER_BRIEF_APPROVERS'),
                   brief_editors=_names('ATELIER_BRIEF_EDITORS'),
                   brief_brand_path=os.getenv('ATELIER_BRAND_BUNDLE_PATH') or None,
                   pack_live_enabled=os.getenv('ATELIER_ALLOW_PACK_GENERATION') == 'true',
                   pack_editors=_names('ATELIER_PACK_EDITORS'),
                   pack_approvers=_names('ATELIER_PACK_APPROVERS'),
                   calendar_schedulers=_names('ATELIER_CALENDAR_SCHEDULERS'),
                   identity_approvers=_names('ATELIER_IDENTITY_APPROVERS'),
                   intake_admins=_names('ATELIER_INTAKE_ADMINS'),
                   wia_reviewers=_names('ATELIER_WIA_REVIEWERS'),
                   synthetic=os.getenv("ATELIER_SYNTHETIC_DATABASE") == "true",
                   **values)._attach(eff)


def encoding_contract(settings, *, synthetic=False):
    # Configuration stays outside SQL; execution provenance stores only its digest.
    return canonical_hash({**embedding_contract(settings), "signature": "six-fields-v1", "synthetic": synthetic})
