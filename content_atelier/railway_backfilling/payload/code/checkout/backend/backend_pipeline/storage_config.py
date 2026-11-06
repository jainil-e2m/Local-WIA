"""SQL capabilities are independent of the legacy prompt-testing switches."""
from __future__ import annotations

import os
from pathlib import Path
from pydantic import BaseModel
from .config import BACKEND_ROOT
from .store import canonical_hash


class StorageSettings(BaseModel):
    database_url: str = "postgresql://atelier:REDACTED_FOR_HANDOVER@127.0.0.1:15432/atelier"
    artifact_root: Path = BACKEND_ROOT / ".storage-artifacts"
    generation_enabled: bool = False
    encoding_enabled: bool = False
    refinement_enabled: bool = False
    api_secret: str = ""
    synthetic: bool = False
    lease_seconds: int = 120
    brief_enabled: bool = False
    brief_live_enabled: bool = False
    brief_web_enabled: bool = False
    brief_approvers: tuple[str, ...] = ()
    brief_editors: tuple[str, ...] = ()
    brief_brand_path: Path | None = None
    brief_model: str | None = None
    brief_review_model: str | None = None
    brief_max_characters: int = 120000
    angle_approval_cutoff: float | None = None
    packs_enabled: bool = False
    pack_live_enabled: bool = False
    pack_writer_model: str | None = None
    pack_review_model: str | None = None
    pack_editors: tuple[str, ...] = ()
    pack_approvers: tuple[str, ...] = ()
    calendar_enabled: bool = False
    calendar_timezone: str = 'Asia/Kolkata'
    calendar_schedulers: tuple[str, ...] = ()

    @classmethod
    def from_env(cls):
        path = BACKEND_ROOT / '.env.storage.local'
        if path.exists():
            for line in path.read_text(encoding='utf-8').splitlines():
                if line.strip() and not line.lstrip().startswith('#') and '=' in line:
                    key,value=line.split('=',1)
                    if key.strip().startswith('ATELIER_'):
                        os.environ.setdefault(key.strip(),value.strip())
        return cls(database_url=os.getenv("ATELIER_DATABASE_URL", cls.model_fields["database_url"].default),
                   artifact_root=os.getenv("ATELIER_ARTIFACT_ROOT", str(BACKEND_ROOT / ".storage-artifacts")),
                   generation_enabled=os.getenv("ATELIER_ALLOW_GENERATION") == "true",
                   encoding_enabled=os.getenv("ATELIER_ALLOW_ENCODING") == "true",
                   refinement_enabled=os.getenv("ATELIER_ALLOW_REFINEMENT") == "true",
                   api_secret=os.getenv("ATELIER_API_SECRET", ""),
                   brief_enabled=os.getenv('ATELIER_BRIEFS_ENABLED') == 'true',
                   brief_live_enabled=os.getenv('ATELIER_ALLOW_BRIEF_GENERATION') == 'true',
                   brief_web_enabled=os.getenv('ATELIER_ALLOW_BRIEF_WEB') == 'true',
                   brief_approvers=tuple(x.strip() for x in os.getenv('ATELIER_BRIEF_APPROVERS','').split(',') if x.strip()),
                   brief_editors=tuple(x.strip() for x in os.getenv('ATELIER_BRIEF_EDITORS','').split(',') if x.strip()),
                   brief_brand_path=os.getenv('ATELIER_BRAND_BUNDLE_PATH') or None,
                   brief_model=os.getenv('ATELIER_BRIEF_MODEL') or None,
                   brief_review_model=os.getenv('ATELIER_BRIEF_REVIEW_MODEL') or None,
                   brief_max_characters=int(os.getenv('ATELIER_BRIEF_MAX_CHARACTERS','120000')),
                   angle_approval_cutoff=float(os.environ['ATELIER_ANGLE_APPROVAL_CUTOFF']) if os.getenv('ATELIER_ANGLE_APPROVAL_CUTOFF') else None,
                   packs_enabled=os.getenv('ATELIER_PACKS_ENABLED') == 'true',
                   pack_live_enabled=os.getenv('ATELIER_ALLOW_PACK_GENERATION') == 'true',
                   pack_writer_model=os.getenv('ATELIER_PACK_WRITER_MODEL') or None,
                   pack_review_model=os.getenv('ATELIER_PACK_REVIEW_MODEL') or None,
                   pack_editors=tuple(x.strip() for x in os.getenv('ATELIER_PACK_EDITORS','').split(',') if x.strip()),
                   pack_approvers=tuple(x.strip() for x in os.getenv('ATELIER_PACK_APPROVERS','').split(',') if x.strip()),
                   calendar_enabled=os.getenv('ATELIER_CALENDAR_ENABLED') == 'true',
                   calendar_timezone=os.getenv('ATELIER_CALENDAR_TIMEZONE','Asia/Kolkata'),
                   calendar_schedulers=tuple(x.strip() for x in os.getenv('ATELIER_CALENDAR_SCHEDULERS','').split(',') if x.strip()),
                   synthetic=os.getenv("ATELIER_SYNTHETIC_DATABASE") == "true")


def encoding_contract(settings, *, synthetic=False):
    # Configuration stays outside SQL; execution provenance stores only its digest.
    return canonical_hash({"endpoint": settings.embedding_base_url.rstrip('/'),
                           "model": settings.embedding_model, "dimensions": 1536,
                           "signature": "six-fields-v1", "synthetic": synthetic})
