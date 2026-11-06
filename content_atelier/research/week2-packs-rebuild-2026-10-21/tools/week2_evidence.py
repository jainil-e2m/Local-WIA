"""Extract, verbatim, every ChatGPT-export message cited in notes/chatgpt_export_week2_findings.md.

Run:  python -I week2_evidence.py
Writes: ../notes/chatgpt_export_week2_evidence.md  (full text of each cited message, in citation order)
        ../notes/chatgpt_export_week2_pack_copy.md (the 13 Oct 2026 simulated pack copy, complete)
Reads the export as data only (gptx.py parser). Attachments are read from the export's .dat files.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gptx

NOTES = Path(__file__).resolve().parent.parent / "notes"
NOTES.mkdir(exist_ok=True)

# (label, conversation-id prefix, node-id prefix, provenance)
CITES = [
    # --- A. 13 Oct 2026 conversations ---
    ("A1 W: rating everything a 1 / zoom out", "6acd92cc", "f243aec5", "Whitney-typed"),
    ("A1 W: create my own doc / question the fields", "6acd92cc", "22a46fd1", "Whitney-typed"),
    ("A1 W: 'I don't like this. Can I switch back to chat?'", "6acd92cc", "3d634c10", "Whitney-typed"),
    ("A1 AI: first critique of the six Week-1 angles", "6acd92cc", "a43d8ebc", "ChatGPT"),
    ("A1 AI: 'zoomed in when they should be zoomed out'", "6acd92cc", "4cbb6622", "ChatGPT"),
    ("A1 AI: field critique (chat-mode answer Whitney kept)", "6acd92cc", "26f45f60", "ChatGPT"),
    ("A1 D: Week-2 system angles pasted for critique", "6acdefc0", "22e8327a", "developer-typed"),
    ("A1 AI: critique of developer system's Week-2 angles", "6acdefc0", "c56d649b", "ChatGPT"),
    ("A1 AI: CTA for Week-2 angle 1 (first answer)", "6acdefc0", "7027b838", "ChatGPT"),
    ("A1 AI: CTA for Week-2 angle 1 (corrected)", "6acdefc0", "d49b3cd9", "ChatGPT"),
    ("A1 AI: critique of 2 handbook-trained angles", "6acde8a5", "893c90f9", "ChatGPT"),
    ("A1 AI: critique of the editorial brief", "6acde8a5", "a142b84c", "ChatGPT"),
    ("A1 AI: simulation understanding (five-asset caveat)", "6acde8a5", "5c91ed29", "ChatGPT"),
    ("A3 AI: 10-angle review", "6acde8a5", "ef547fed", "ChatGPT"),
    ("A3 AI: briefs A01 + A05", "6acde8a5", "6776b076", "ChatGPT"),
    ("A3 AI: briefs A03 + A09 summary", "6acde8a5", "c73805e7", "ChatGPT"),
    ("A3 D: angle cards pasted back (A01/A03/A05/A09)", "6acde8a5", "179ed67f", "developer-typed"),
    ("A4 D: brief expansion request", "6acde8a5", "f10de3d1", "developer-typed"),
    ("A4 D: pack request", "6acde8a5", "00453cd3", "developer-typed"),
    ("A4 D: 2024 email samples", "6acde8a5", "f6d9db82", "developer-typed"),
    ("A4 D: reel samples", "6acde8a5", "006a12b2", "developer-typed"),
    ("A4 D: caption samples", "6acde8a5", "064257db", "developer-typed"),
    # --- B. Whitney's finished copy ---
    ("B 2026-04-28 W: subject line correction", "69d530e4", "f251a184", "Whitney-typed"),
    ("B 2026-04-29 W: 'More leads won't fix this' final", "69d530e4", "47b48d7f", "Whitney-typed"),
    ("B 2026-04-16 W: LeadLock is not where contracts happen", "69d530e4", "9a47f4a8", "Whitney-typed"),
    ("B 2026-04-16 W: 'We're interested...' to 'We're ready to book!'", "69d530e4", "301926d4", "Whitney-typed"),
    ("B 2026-04-21 W: automation supports personal follow-up", "69d530e4", "a2cb6d4b", "Whitney-typed"),
    ("B 2025-12-18 W: LeadLock not integrated with Dubsado/HoneyBook", "6942fe07", "0e0c472d", "Whitney-typed"),
    ("B 2025-10-07 W: WIA's own Meta leads no-show", "68e50a38", "75c25716", "Whitney-typed"),
    ("B 2026-01-14 W: ghosting feels personal when manual", "6967d2ea", "fc07e1a8", "Whitney-typed"),
    ("B 2026-06-10 W: 'The question we ask every new client' email", "6a296764", "48c9328c", "Whitney-typed"),
    ("B 2026-06-10 W: carousel draft", "6a296764", "519cc2f6", "Whitney-typed"),
    ("B 2026-06-10 W: 'not conducting market research ... yet'", "6a296764", "cb764f40", "Whitney-typed"),
    ("B 2026-06-10 W: current-state foundations", "6a296764", "8821799a", "Whitney-typed"),
    ("B 2026-06-10 W: caption she wrote", "6a296764", "98033bc2", "Whitney-typed"),
    ("B 2026-06-08 W: VAULT research training brief", "6a26e8bc", "70afcd7f", "Whitney-typed"),
    ("B 2026-06-08 W: 'highlight how in depth we work'", "6a26e8bc", "945cc76b", "Whitney-typed"),
    ("B 2026-06-10 W: lower-barrier CTA", "6a26e8bc", "ea055c19", "Whitney-typed"),
    ("B 2026-06-25 W: sales on autopilot caption draft", "6a3d3a29", "d8a7f415", "Whitney-typed"),
    ("B 2026-06-25 W: positioning corrections", "6a3d3a29", "0e5798bb", "Whitney-typed"),
    ("B 2026-06-25 W: ELEVATE buyers already trying", "6a3d3a29", "67dc25d8", "Whitney-typed"),
    ("B 2026-06-29 W: email edit", "6a3d3a29", "21a9939a", "Whitney-typed"),
    ("B 2026-06-29 W: caption as posted + email brief", "6a3d3a29", "e41f373b", "Whitney-typed"),
    ("B 2026-06-29 AI: final email after her edits", "6a3d3a29", "489f339d", "ChatGPT (approved)"),
    ("B 2026-07-16 W: Erin story facts", "6a4d4971", "e9bb9c0e", "Whitney-typed"),
    ("B 2026-07-17 W: audit follow-up email", "6a5a2d83", "6e750227", "Whitney-typed"),
    ("B 2026-07-30 W: $22K caption", "6a4d4971", "12eca42a", "Whitney-typed"),
    ("B 2026-08-13 W: 10-week reel draft", "6a73993f", "60b841f2", "Whitney-typed"),
    ("B 2026-09-15 W: UVP email final", "6aa98079", "3eb7f12d", "Whitney-typed"),
    ("B 2026-09-15 W: 'disingenuous to say we'", "6aa983fe", "c2fe1f77", "Whitney-typed"),
    ("B 2026-09-16 W: reel 1 script", "6aaaba8c", "4d18f018", "Whitney-typed"),
    ("B 2026-09-16 W: own the results", "6aaaba8c", "9fbe40ac", "Whitney-typed"),
    ("B 2026-10-01 W: 'That first line is terrible'", "6abeb98d", "f87a3d4a", "Whitney-typed"),
    ("B 2026-10-01 W: shitty websites / UVP email as sent", "6abeb98d", "09ff6130", "Whitney-typed"),
    ("B 2026-10-01 W: 'nobody actually showed up'", "6abeb98d", "6d1e88a1", "Whitney-typed"),
    ("B 2026-10-01 AI: approved caption (UVP reel)", "6abeb98d", "e9e74bd4", "ChatGPT (approved)"),
    ("B 2026-10-01 AI: approved caption (visibility reel)", "6abeb98d", "c46c692c", "ChatGPT (approved after her edits)"),
    ("B 2026-10-08 AI: Google-rep giveaway caption", "6ac3c3eb", "8aa03af0", "ChatGPT (implicitly accepted)"),
    ("B 2026-04-13 W: Accelerator scope", "69cd32e6", "e526d231", "Whitney-typed"),
    ("B 2026-04-01 W: Meta as retargeting", "69cd32e6", "f9296ea9", "Whitney-typed"),
    ("B 2026-01-30 W: Google captures, Meta retargets", "697cb7d4", "b366209f", "Whitney-typed"),
    ("B 2026-01-30 W: client asked to turn Google off", "697cb7d4", "a0b9779e", "Whitney-typed"),
    ("B 2026-07-13 W: Elia email (both platforms)", "6a5426db", "0a9df4ee", "Whitney-typed"),
    ("B 2026-08-20 W: Google + Meta compounding", "6a5667a7", "a346970f", "Whitney-typed"),
    ("B 2026-05-01 W: final email 'A smarter way...'", "69c14c0f", "dcfe2088", "Whitney-typed"),
    # --- C. reactions ---
    ("C 2026-05-01 W: subject line / survey insight", "69c14c0f", "c2932f92", "Whitney-typed"),
    ("C 2026-05-01 W: terrible hook", "69c14c0f", "7b78121f", "Whitney-typed"),
    ("C 2026-05-01 W: chosen reel hook", "69c14c0f", "87494b16", "Whitney-typed"),
    ("C 2026-05-13 W: liked text hook", "6a026ad2", "4baf3a30", "Whitney-typed"),
    ("C 2026-05-13 W: hook sucks / cold to sold", "6a026ad2", "50626c3e", "Whitney-typed"),
    ("C 2026-05-13 W: repeat ideas not language", "6a026ad2", "bd2a5e49", "Whitney-typed"),
    ("C 2026-05-13 W: desperation hook", "6a026ad2", "82aaf943", "Whitney-typed"),
    ("C 2026-05-19 W: subject line sucks", "6a06061f", "44e68ec4", "Whitney-typed"),
    ("C 2026-06-02 W: played-out subject", "6a1efd89", "9cd538df", "Whitney-typed"),
    ("C 2026-06-02 W: her subject line", "6a1efd89", "12456645", "Whitney-typed"),
    ("C 2026-06-16 W: contradictory subject", "6a0c862f", "21cd131e", "Whitney-typed"),
    ("C 2026-06-25 W: hook terrible and generic", "6a3d3a29", "fc96c6eb", "Whitney-typed"),
    ("C 2026-06-29 W: subject line sucks", "6a3d3a29", "e86c9d25", "Whitney-typed"),
    ("C 2026-06-29 W: anomaly line", "6a3d3a29", "aa11a578", "Whitney-typed"),
    ("C 2026-07-29 W: generic reel cover", "6a68eccd", "5bc8d477", "Whitney-typed"),
    ("C 2026-08-04 W: same hook as reel?", "6a721147", "bd00270f", "Whitney-typed"),
    ("C 2026-08-04 W: slide-1 direction", "6a721147", "20bca7af", "Whitney-typed"),
    ("C 2026-08-04 W: hand-hold the agency", "6a721147", "b824b80f", "Whitney-typed"),
    ("C 2026-08-13 W: not the exact same hook", "6a73993f", "05394e39", "Whitney-typed"),
    ("C 2026-08-13 W: love the new hook", "6a73993f", "16933c6e", "Whitney-typed"),
    # --- D. accounts ---
    ("D 2026-08-26 W: Diamond A restructure + video SMS plan", "6a8dfcd0", "a0aa480c", "Whitney's sent emails relayed by Gisselle"),
    ("D 2026-09-01 W: Diamond A Aug 31 recap", "6a8dfcd0", "ba38fd21", "Whitney's sent email relayed by Gisselle"),
    ("D 2026-09-09 team: Diamond A SMS done", "6a8dfcd0", "d2b60b72", "meeting transcript relayed by Gisselle"),
    ("D 2026-09-11 W: Diamond A August report final", "6a8dfcd0", "6eb0aaeb", "Whitney's sent email relayed by Gisselle"),
    ("D 2026-09-25 W: Diamond A AI Max reply", "6a8dfcd0", "c1da5289", "Whitney's sent email relayed by Gisselle"),
    ("D 2026-09-15 Zoom summary: The Penny call", "6a8dfcd0", "9ab8765f", "Zoom AI summary relayed by Gisselle"),
    ("D 2026-10-06 W: reply to Shannon", "6a8dfcd0", "5f69db84", "Whitney's sent email relayed by Gisselle"),
    ("D 2026-10-09 team: Erin office-hours recap", "6aa43a8b", "dcc89c5f", "Carmen's Slack note relayed by team"),
]

PACK = [
    ("Emails rewritten to the 2024 samples (A01, A05, A03, A09)", "6acde8a5", "148279fe"),
    ("Carousels (A01, A05, A03, A09)", "6acde8a5", "18f55a39"),
    ("Reel scripts, 12 (after reel samples)", "6acde8a5", "258218c4"),
    ("Reel captions, 12 (after caption samples)", "6acde8a5", "c0103650"),
]

ATTACH = [
    ("Pasted text(8): developer system's Week-2 angles (13 Oct 08:46)", "file_000000005c548211aaeda61140e8fe7d.dat"),
    ("Pasted text(9): 2 angles 'generated after learning from the handbook' (13 Oct 10:28)", "file_000000008ee0820b9de5fc11965dda28.dat"),
    ("Pasted text(20261013-134147): carousel examples (13 Oct 13:45)", "file_000000006600820eb53123bf1b3ac2d4.dat"),
]


def node_text(convs, cpre, npre):
    for c in gptx.find(convs, cpre):
        for m in gptx.messages(c, all_nodes=True):
            if m["id"].startswith(npre):
                return c, m
    return None, None


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    convs = gptx.load()
    out = ["# Week 2 findings: verbatim evidence", "",
           "Generated by scripts/week2_evidence.py from the ChatGPT export. Each block is one message, quoted in full. "
           "Times are UTC. Provenance is the author of the text as best established (see findings file).", ""]
    missing = []
    for label, cpre, npre, prov in CITES:
        c, m = node_text(convs, cpre, npre)
        if not m:
            missing.append(label)
            continue
        cid = c.get("conversation_id") or c.get("id")
        out += [f"## {label}", f"`{cid}` · \"{c.get('title')}\" · node `{m['id']}` · {gptx.ts(m['t'])} UTC · role={m['role']} · provenance: {prov}", "",
                "```text", m["text"].strip(), "```", ""]
    for title, fname in ATTACH:
        p = gptx.EXPORT / fname
        out += [f"## Attachment: {title}", f"`{fname}`", "", "```text", p.read_text(encoding="utf-8", errors="replace").strip(), "```", ""]
    (NOTES / "chatgpt_export_week2_evidence.md").write_text("\n".join(out), encoding="utf-8")

    pk = ["# 13 Oct 2026 simulated Week-2 pack copy (complete, verbatim)", "",
          "Conversation `6acde8a5-de40-83e8-b8e3-f6f533f943c9`. All text below is ChatGPT-written (model gpt-6.1 family) on prompts typed by the developer. "
          "The first-draft .docx packs (WIA_Content_Pack_1_A01.docx ... _4_A09.docx) are sandbox links and are NOT in the export; "
          "what survives is the chat-only rewrites below.", ""]
    for title, cpre, npre in PACK:
        c, m = node_text(convs, cpre, npre)
        pk += [f"## {title}", f"node `{m['id']}` · {gptx.ts(m['t'])} UTC", "", m["text"].strip(), ""]
    (NOTES / "chatgpt_export_week2_pack_copy.md").write_text("\n".join(pk), encoding="utf-8")
    print("evidence blocks:", len(CITES) - len(missing), "missing:", missing)


if __name__ == "__main__":
    main()
