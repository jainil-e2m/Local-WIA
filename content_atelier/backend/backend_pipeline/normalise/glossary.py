"""The glossary (plan 1.B12): names the transcripts spell wrongly, and what to do about it.

Product, staff and client names get mis-transcribed ("LeadLock" becomes "Lead Lock", "Carmen" becomes "Carmin"). A glossary
term lists its spellings. It is applied in two places and never to the document:

* **a search copy** of each chunk (`transcript_chunks.search_text`, which the full-text column reads): a search for the
  product name finds the segment where the transcript spelled it another way;
* **hints** for extraction and research: the terms a passage of text mentions, in any spelling, so a prompt can say what
  the speaker meant.

`original_text`, the passage map and `chunk_text` are never touched: a quote is always the speaker's exact words.
"""
from __future__ import annotations

import re


class Glossary:
    def __init__(self, terms: list[dict]):
        self.terms = [t for t in terms if t.get("status", "active") == "active"]
        pairs = []
        for term in self.terms:
            for spelling in {term["term"], *(term.get("variants") or [])}:
                if spelling.strip():
                    pairs.append((spelling.strip(), term["term"]))
        # Longer spellings first, so "Lead Lock Pro" is not eaten by "Lead Lock".
        pairs.sort(key=lambda p: -len(p[0]))
        self._canonical = {spelling.lower(): canonical for spelling, canonical in pairs}
        self._pattern = re.compile(r"(?<![A-Za-z0-9])(" + "|".join(re.escape(s) for s, _ in pairs) + r")(?![A-Za-z0-9])", re.I) \
            if pairs else None

    @classmethod
    def from_database(cls, conn) -> Glossary:
        return cls(conn.execute("SELECT term,kind,variants,status FROM glossary_terms").fetchall())

    def normalise(self, text: str) -> str:
        """The text with every known spelling replaced by its canonical term: the search copy."""
        if not self._pattern:
            return text
        return self._pattern.sub(lambda m: self._canonical[m.group(1).lower()], text)

    def hints(self, text: str) -> list[dict]:
        """The terms mentioned in a text, in any spelling: [{term, kind, heard_as}], in order of first mention."""
        if not self._pattern:
            return []
        kinds = {t["term"]: t["kind"] for t in self.terms}
        found: dict[str, dict] = {}
        for match in self._pattern.finditer(text):
            canonical = self._canonical[match.group(1).lower()]
            found.setdefault(canonical, {"term": canonical, "kind": kinds[canonical], "heard_as": []})
            if match.group(1) != canonical and match.group(1) not in found[canonical]["heard_as"]:
                found[canonical]["heard_as"].append(match.group(1))
        return list(found.values())


def refresh_search_text(conn, glossary: Glossary | None = None) -> int:
    """Recompute the search copy of every current chunk (after the glossary changed). No chunk text, hash or vector changes."""
    glossary = glossary or Glossary.from_database(conn)
    count = 0
    for row in conn.execute("SELECT chunk_id,chunk_text,search_text FROM transcript_chunks WHERE is_current").fetchall():
        search = glossary.normalise(row["chunk_text"])
        wanted = None if search == row["chunk_text"] else search
        if wanted != row["search_text"]:
            conn.execute("UPDATE transcript_chunks SET search_text=%s WHERE chunk_id=%s", (wanted, row["chunk_id"]))
            count += 1
    return count


def search(conn, query: str, *, limit: int = 20, glossary: Glossary | None = None) -> list[dict]:
    """Full-text search over current chunks, spelling-tolerant through the glossary: the query is normalised the same way
    the search copy is, so any spelling of a name finds every spelling of it. Returns chunk text exactly as stored."""
    glossary = glossary or Glossary.from_database(conn)
    return conn.execute("""SELECT c.chunk_id,c.transcript_id,c.chunk_text,c.header,t.title,t.occurred_at,
            ts_rank(c.tsv, websearch_to_tsquery('english',%s)) AS rank
        FROM transcript_chunks c JOIN transcripts t USING (transcript_id)
        WHERE c.is_current AND t.included AND c.tsv @@ websearch_to_tsquery('english',%s)
        ORDER BY rank DESC, c.chunk_id LIMIT %s""", (glossary.normalise(query), glossary.normalise(query), limit)).fetchall()
