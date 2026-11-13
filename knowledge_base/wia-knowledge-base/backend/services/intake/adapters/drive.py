"""Google Drive adapter. Scope = approved folder (walked recursively). Record = file.

Window semantics: files whose modifiedTime falls in the window. Folders are walked
regardless of their own dates. Video/images/audio are references only (no OCR or
transcription). Shortcuts are recorded, not followed (see before_production.md).
"""
import json
import re
from datetime import datetime
from urllib.parse import quote

from backend.config import get_settings
from backend.models.domain.intake import (
    BusinessHint,
    ChangeBatch,
    DiscoveryResult,
    Gap,
    IdentityRef,
    IntakeContext,
    NormalisedRecord,
    ScopeCandidate,
)
from backend.services.intake.adapters import google_auth
from backend.services.intake.adapters.base import ConnectorIdentity
from backend.services.intake.normalise import documents
from backend.services.shared.errors import IntakeError, NotFoundError, ScopeDeniedError
from backend.services.shared.http import ProviderClient

FOLDER = "application/vnd.google-apps.folder"
GDOC = "application/vnd.google-apps.document"
GSHEET = "application/vnd.google-apps.spreadsheet"
SHORTCUT = "application/vnd.google-apps.shortcut"
PDF = "application/pdf"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
TEXTLIKE = {"text/plain", "text/vtt", "text/markdown", "text/csv"}
FIELDS = ("nextPageToken,files(id,name,mimeType,parents,modifiedTime,createdTime,size,webViewLink,"
          "owners(displayName,emailAddress),lastModifyingUser(displayName,emailAddress),shortcutDetails,version,trashed)")
COMMON = {"supportsAllDrives": "true", "includeItemsFromAllDrives": "true"}


# Long-lived profile documents (questionnaires, brand assets, agreements) rarely change, so an activity
# window would never include them. In a windowed run they are taken regardless of date. Full-history
# runs (production) take everything anyway, so this only matters for bounded backfills.
PROFILE_NAME = re.compile(r"questionnaire|onboarding|positioning|brand|logo|contract|agreement|proposal|intake form",
                          re.IGNORECASE)


# Agreements and pricing are finance (F2: admins only), whichever folder they sit in.
FINANCE_NAME = re.compile(r"contract|agreement|proposal|invoice|packages|pricing|price list", re.IGNORECASE)


def is_profile_document(name: str, folder_path: list[str]) -> bool:
    return bool(PROFILE_NAME.search(name) or any(PROFILE_NAME.search(p) for p in folder_path))


def _dt(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


class DriveAdapter:
    provider = "drive"
    parser_version = "drive-v2"

    def __init__(self):
        self.http = ProviderClient("drive", "https://www.googleapis.com/", min_interval_seconds=0.1)
        google_auth.bind(self.http)
        self._refresh = lambda: google_auth.refresh(self.http)

    def _get(self, path, params=None):
        return self.http.get_json(path, params, auth_retry=self._refresh)

    def identify(self) -> ConnectorIdentity:
        user = self._get("drive/v3/about", {"fields": "user(emailAddress,displayName)"})["user"]
        email = user["emailAddress"].lower()
        return ConnectorIdentity(provider_account_id=email, display_identity=email, expected_identity_value=email,
                                 granted_scopes=google_auth.granted_scopes(), credential_ref="GOOGLE_REFRESH_TOKEN")

    def _list(self, q: str, token: str | None = None, page_size: int = 100) -> dict:
        return self._get("drive/v3/files", {"q": q, "fields": FIELDS, "pageSize": page_size, **COMMON,
                                            **({"pageToken": token} if token else {})})

    def discover(self, hints: list[BusinessHint], window_start, window_end) -> DiscoveryResult:
        result = DiscoveryResult()
        found: dict[str, tuple[dict, BusinessHint]] = {}
        for hint in hints:
            for alias in hint.aliases:
                safe = alias.replace("'", "\\'")
                data = self._list(f"mimeType='{FOLDER}' and name contains '{safe}' and trashed=false", page_size=50)
                for f in data.get("files", []):
                    found.setdefault(f["id"], (f, hint))
        # Propose only top-most matches: a matching folder inside another matching folder is covered by recursion.
        for fid, (f, hint) in found.items():
            if any(p in found for p in f.get("parents", [])):
                continue
            parent = None
            if f.get("parents"):
                try:
                    parent = self._get(f"drive/v3/files/{f['parents'][0]}", {"fields": "name", **COMMON}).get("name")
                except IntakeError:
                    parent = None
            result.scopes.append(ScopeCandidate(
                kind="folder", external_id=fid, name=f["name"], parent_name=parent, default_domain="profile",
                association_mode="dedicated", suggested_business_id=hint.business_id,
                reason=f"folder name matches alias of {hint.name}",
                stats={"modified": f.get("modifiedTime"), "link": f.get("webViewLink")}))
        return result

    def read_page(self, ctx: IntakeContext, checkpoint: dict) -> ChangeBatch:
        from backend.services.intake.adapters.readers import read_page
        return read_page(self, ctx, checkpoint)

    def backfill_page(self, ctx: IntakeContext, cursor: str | None) -> ChangeBatch:
        return self.read_page(ctx, json.loads(cursor) if cursor else {})

    def _download(self, f: dict) -> bytes | None:
        if int(f.get("size") or 0) > get_settings().max_file_bytes:
            return None
        return self.http.request("GET", f"drive/v3/files/{f['id']}", params={"alt": "media", **COMMON},
                                 auth_retry=self._refresh).content

    def _normalise(self, f: dict, path: list[str]) -> NormalisedRecord:
        mime, fid = f["mimeType"], f["id"]
        units, notes, state = [], [], "content"
        try:
            if mime == GDOC:
                doc = self._get(f"https://docs.googleapis.com/v1/documents/{fid}", {"includeTabsContent": "true"})
                units = documents.google_doc_units(doc, fid)
            elif mime == GSHEET:
                meta = self._get(f"https://sheets.googleapis.com/v4/spreadsheets/{fid}",
                                 {"fields": "sheets(properties(title))"})
                titles = [s["properties"]["title"] for s in meta.get("sheets", [])]
                tabs = []
                for title in titles:
                    a1 = "'" + title.replace("'", "''") + "'"
                    # The range sits in the URL path: "+" would arrive as a space ("Branding + Colors").
                    values = self._get(f"https://sheets.googleapis.com/v4/spreadsheets/{fid}/values/{quote(a1, safe='')}",
                                       {"valueRenderOption": "FORMATTED_VALUE"}).get("values", [])
                    tabs.append((title, values))
                units, notes = documents.sheet_units(fid, tabs)
                state = "partial" if notes else "content"
            elif mime in (PDF, DOCX) or mime in TEXTLIKE:
                data = self._download(f)
                if data is None:
                    state, notes = "unsupported", [f"file larger than {get_settings().max_file_bytes} bytes"]
                elif mime == PDF:
                    units, notes = documents.pdf_units(data, fid)
                    state = "partial" if notes and units else ("unsupported" if not units else "content")
                elif mime == DOCX:
                    units = documents.docx_units(data, fid)
                else:
                    units = documents.transcript_text_units(data.decode("utf-8", errors="replace"), fid)
            else:
                state = "metadata_only"
                notes = [f"{mime}: referenced only (no OCR/transcription/media processing)"]
        except IntakeError:
            raise
        except Exception as exc:  # parser failure on one file: keep metadata, record why
            units, state, notes = [], "unsupported", [f"parser error: {type(exc).__name__}"]
        modifier = f.get("lastModifyingUser") or {}
        owners = [IdentityRef(external_key=o["emailAddress"].lower(), display_name=o.get("displayName"),
                              email=o["emailAddress"].lower()) for o in f.get("owners", []) if o.get("emailAddress")]
        modified_by = (IdentityRef(external_key=modifier["emailAddress"].lower(), display_name=modifier.get("displayName"),
                                   email=modifier["emailAddress"].lower()) if modifier.get("emailAddress") else None)
        return NormalisedRecord(
            record_kind="drive_file", external_id=fid, occurred_at=_dt(f.get("createdTime")),
            provider_updated_at=_dt(f.get("modifiedTime")), source_url=f.get("webViewLink"),
            attributes={"name": f.get("name"), "mime_type": mime, "folder_path": path, "parents": f.get("parents", []),
                        "size": f.get("size"), "created_time": f.get("createdTime"),
                        "modified_time": f.get("modifiedTime"),
                        "shortcut_target": (f.get("shortcutDetails") or {}).get("targetId") if mime == SHORTCUT else None},
            units=units, participants=[p for p in owners + [modified_by] if p], content_state=state,
            coverage_notes=notes, version_hint=f"v{f['version']}" if f.get("version") else None,
            domain="finance" if FINANCE_NAME.search(f.get("name") or "") else None,
        )
