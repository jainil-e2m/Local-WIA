"""Bootstrap client registry from a YAML file (FR-INT-01). Loading is idempotent by slug.

YAML is only for bootstrap and local development: admins add, map and archive clients in the UI, and
both paths go through `backend.services.clients.mapping`.
"""
from pathlib import Path

import yaml
from sqlalchemy import select

from backend.db import transaction
from backend.models.db import Business, BusinessAlias
from backend.services.clients import mapping


def load(path: Path, actor: str = "cli") -> list[str]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    loaded = []
    with transaction() as session:
        for entry in data.get("clients", []):
            business = session.execute(select(Business).where(Business.slug == entry["slug"])).scalar_one_or_none()
            aliases = entry.get("aliases", [])
            if business is None:
                business = mapping.create_client(session, name=entry["name"], slug=entry["slug"], aliases=aliases,
                                                 actor=actor, discover=False)
            else:
                existing = set(session.execute(
                    select(BusinessAlias.alias).where(BusinessAlias.business_id == business.id)).scalars())
                new = [a for a in aliases if a not in existing]
                if new or business.name != entry["name"]:
                    mapping.update_client(session, business.id, expected_revision=None, actor=actor,
                                          name=entry["name"], add_aliases=new)
            for item in entry.get("contacts", []):  # contacts supplied by WIA are approved directly
                mapping.add_contact(session, business.id, actor=actor, email=item.get("email"), domain=item.get("domain"))
            loaded.append(entry["slug"])
    return loaded
