"""The content pack v2 service behind the API (NP.B2, NP.B3, NP.B6; the content-packs plan, sections 4.1, 5.3 and 5.6).

Each function is one route of `production_api.py` and answers the response model named beside it (`api_models.py`). The
work lives in the modules it calls: `queue` (start on Gate 2 approval, create and retry), `versions` (edits, reverts,
clearances, attestations, readiness, published marks, Finish again), `views` (detail, listing, production), `checks` (the
deterministic pack checks), `week` (the week plan) and `document` (the week's pack document).

Errors are `ProductionError` (message, code, HTTP status) so the route answers in words; a pack mutation takes the pack's
current manifest hash and refuses a stale one (409 `stale_pack`) and any change while the pack's run is active (409
`pack_running`). Every route answers 503 `packs_disabled` while `features.packs` is off.
"""
from __future__ import annotations


def create(repo, brief_id, payload, actor):
    """POST /briefs/{id}/pack -> PackQueuedV2. Create the pack of an approved v4 brief, or retry its failed or waiting run."""
    from . import queue
    return queue.create(repo, brief_id, payload, actor)


def listing(repo, actor, week_id=None, state=None, limit=20, offset=0, *, brief_id=None):
    """GET /packs -> PackPageV2: the current v2 packs (nothing supersedes them), newest first, with their state; filtered by
    week, by state, or by brief (any version of the brief's lineage: the brief page finds its pack this way)."""
    from . import views
    return views.listing(repo, actor, week_id=week_id, state=state, limit=limit, offset=offset, brief_id=brief_id)


def detail(repo, pack_id, actor):
    """GET /packs/{id} -> StoredPackV2 (a v1 pack keeps its v1 detail, packs/service.detail)."""
    from . import views
    return views.detail(repo, pack_id, actor)


def production(repo, pack_id, actor):
    """GET /packs/{id}/production -> PackProductionV2."""
    from . import views
    return views.production(repo, pack_id, actor)


def edit(repo, pack_id, key, payload, actor):
    """PATCH /packs/{id}/pieces/{key} -> PackSavedV2."""
    from . import versions
    return versions.edit(repo, pack_id, key, payload, actor)


def revert(repo, pack_id, key, payload, actor):
    """POST /packs/{id}/pieces/{key}/revert -> PackSavedV2."""
    from . import versions
    return versions.revert(repo, pack_id, key, payload, actor)


def clearance(repo, pack_id, payload, actor):
    """POST /packs/{id}/clearances -> PackSavedV2."""
    from . import versions
    return versions.clearance(repo, pack_id, payload, actor)


def attest(repo, pack_id, finding_id, payload, actor):
    """POST /packs/{id}/findings/{finding_id}/attest -> PackSavedV2."""
    from . import versions
    return versions.attest(repo, pack_id, finding_id, payload, actor)


def finish_again(repo, pack_id, payload, actor):
    """POST /packs/{id}/finish -> PackSavedV2 (the new run's pack, finishing)."""
    from . import versions
    return versions.finish_again(repo, pack_id, payload, actor)


def recorded_take(repo, pack_id, key, payload, actor):
    """POST /packs/{id}/pieces/{key}/recorded -> PackSavedV2 (the post-recording pass's run, finishing; NP.B14)."""
    from . import versions
    return versions.recorded_take(repo, pack_id, key, payload, actor)


def refinish(repo, pack_id, payload, actor):
    """POST /packs/{id}/refinish -> PackSavedV2 (finishing again with a permission, finishing; NP.B15)."""
    from . import versions
    return versions.refinish(repo, pack_id, payload, actor)


def decide(repo, pack_id, payload, actor):
    """POST /packs/{id}/decision -> PackSavedV2: ready to publish (bound to the manifest) or back to review."""
    from . import versions
    return versions.decide(repo, pack_id, payload, actor)


def published(repo, pack_id, key, payload, actor):
    """POST /packs/{id}/pieces/{key}/published -> PackPublishedV2."""
    from . import versions
    return versions.published(repo, pack_id, key, payload, actor)


def week_plan(repo, week_id, actor):
    """GET /weeks/{id}/pack-plan -> WeekPackPlanV2."""
    from . import week
    return week.plan(repo, week_id, actor)


def week_document(repo, week_id, actor):
    """GET /weeks/{id}/packs.md -> text/markdown: the week's pack document, every piece unabbreviated."""
    from . import document
    return document.markdown(repo, week_id, actor)


def week_document_docx(repo, week_id, actor):
    """GET /weeks/{id}/packs.docx -> the same document as packs.md, as a Word file (python-docx, no client template)."""
    from . import document_docx
    return document_docx.docx(repo, week_id, actor)
