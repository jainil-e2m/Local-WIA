/* ─────────────────────────────────────────────────────────────────
   Capture every Private Integration scope from a LeadLock / GHL tenant.

   WHERE: the Scopes step of Settings → Private Integrations. Paste into
   the DevTools Console and press Enter. Chrome blocks the first console
   paste — type `allow pasting`, Enter, then paste.

   DO NOT OPEN THE DROPDOWN FIRST. The script opens it. Clicking into
   DevTools blurs the page and closes it again, so anything that expects
   an already-open list finds nothing.

   THERE IS NO SEARCH BOX in this component — it is a plain checkbox list
   of 162 rows, virtualised, so scrolling is the only way through.

   v3 changes, after v2 topped out at 131 of 162:

     · steps by ONE ROW at a time, measured off a real row rather than
       guessed from the viewport, so no row can pass the render window
       without mounting
     · dwells 120ms per step and sweeps both directions
     · runs up to 12 passes within a 150-second budget, stopping as soon
       as a whole pass adds nothing new
     · matches more row shapes. v2 assumed "Label - scope.readonly". The
       tenant also has `.read` and `.create` suffixes, may use an en- or
       em-dash as the separator, and may render some rows as a bare token
       with no label at all.

   SAFE TO RE-RUN. Results accumulate in window.__ghlScopes.
   ───────────────────────────────────────────────────────────────── */

(async () => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const t0 = Date.now();
  const BUDGET_MS = 150000;

  /* HYPHENS ARE PART OF THE RESOURCE NAME. v3 used [A-Za-z0-9_] here, which
     cannot match `voice-ai/agents.readonly` — so the match started after the
     hyphen and filed it as `agents.readonly`, swallowing "voice-ai" into the
     label. Around 24 rows came back wrong that way. */
  const TOKEN = String.raw`[a-z][A-Za-z0-9_-]*(?:\/[A-Za-z0-9_-]+)*\.[a-z]+`;

  /* The separator now REQUIRES whitespace both sides. With hyphens legal
     inside a token, `\s*[-]\s*` would cheerfully split
     `voice-ai/agents.readonly` in half and call the first part a label. */
  const LABELLED = new RegExp(`^(.{2,90}?)\\s+[-–—]\\s+(${TOKEN})$`);
  const BARE = new RegExp(`^(${TOKEN})$`);
  const CONTAINS_TOKEN = new RegExp(TOKEN);


  /* PARSER VERSION. Results accumulate across runs, which is right while
     the parser is stable and actively wrong when it is not: v3 filed
     `voice-ai-agents.readonly` as `agents.readonly`, and simply re-running
     v4 left both in the Map — then stopped early because the polluted
     count had already reached the target. Bumping this discards the old
     harvest automatically, so nobody has to remember a reset line. */
  const PARSER = 4;
  if (window.__ghlParser !== PARSER) {
    window.__ghlScopes = new Map();
    window.__ghlRaw = new Set();
    window.__ghlParser = PARSER;
    console.log(`Parser v${PARSER} — cleared any harvest from an older parser.`);
  }

  /* scope token → label. Keyed on the token, so re-collecting is free.
     Bound AFTER the reset above, or it would alias the discarded Map. */
  const store = (window.__ghlScopes = window.__ghlScopes || new Map());

  /* Every matched row's raw text, kept so a parsing mistake can be
     diagnosed without another two-minute scroll. */
  const raw = (window.__ghlRaw = window.__ghlRaw || new Set());

  const target = (() => {
    const m = document.body.innerText.match(/(\d+)\s+of\s+(\d+)\s+selected/);
    return m ? Number(m[2]) : null;
  })();

  const collect = () => {
    for (const el of document.querySelectorAll('li,div,span,label,p,td')) {
      if (el.firstElementChild) continue;          // leaves only
      const t = (el.textContent || '').trim();
      if (t.length < 4 || t.length > 110) continue;

      const m = LABELLED.exec(t);
      if (m || BARE.test(t)) raw.add(t);
      if (m) {
        /* A label carrying its own scope token means we matched across a
           row boundary — drop it rather than file a real scope under
           nonsense. Tested against the token pattern itself, not a word
           boundary: two glued rows produce "…businesses.readonlyEdit
           Businesses", where \b after "readonly" never fires. */
        if (!CONTAINS_TOKEN.test(m[1])) store.set(m[2], m[1]);
        continue;
      }
      const b = BARE.exec(t);
      if (b && !store.has(b[1])) store.set(b[1], '(no label)');
    }
  };

  /* The nearest scrollable ancestor of a real option row — never the page. */
  const findScroller = () => {
    const leaf = [...document.querySelectorAll('li,div,span,label,p')]
      .find((e) => !e.firstElementChild && LABELLED.test((e.textContent || '').trim()));
    for (let n = leaf; n && n !== document.body; n = n.parentElement) {
      if (n.scrollHeight > n.clientHeight + 20) return n;
    }
    return null;
  };

  /* One option row's height, measured rather than guessed. Walk up from a
     matching leaf until the box is tall enough to be the row itself. */
  const rowHeight = (sc) => {
    const leaf = [...document.querySelectorAll('li,div,span,label,p')]
      .find((e) => !e.firstElementChild && LABELLED.test((e.textContent || '').trim()));
    for (let n = leaf; n && n !== sc; n = n.parentElement) {
      const h = n.getBoundingClientRect().height;
      if (h >= 18 && h <= 90) return Math.round(h);
    }
    return 28;
  };

  /* ── 1 · open the dropdown ───────────────────────────────────── */

  const opener =
    document.querySelector('.hr-base-selection') ||
    document.querySelector('[class*="selection"]:not([class*="tag"])') ||
    [...document.querySelectorAll('div,span')].find(
      (d) => !d.firstElementChild && /select scopes/i.test(d.textContent || ''),
    );

  if (opener) {
    opener.click();
    await sleep(700);
  }

  let sc = findScroller();
  if (!sc) {
    console.log('Could not open it automatically — click the dropdown open now. Waiting 8s...');
    for (let i = 0; i < 40 && !sc; i++) {
      await sleep(200);
      sc = findScroller();
    }
  }
  if (!sc) {
    console.error('No option list found. Open the scopes dropdown, then re-run.');
    return;
  }

  /* ── 2 · row-by-row sweep ────────────────────────────────────── */

  const step = rowHeight(sc);
  console.log(
    `Target ${target ?? 'unknown'} · holding ${store.size} · row ${step}px · up to ${BUDGET_MS / 1000}s`,
  );

  const done = () => (target && store.size >= target) || Date.now() - t0 > BUDGET_MS;

  let pass = 0;
  let previous = -1;

  while (pass < 12 && store.size !== previous && !done()) {
    previous = store.size;
    pass++;
    sc = findScroller() || sc;

    for (let y = 0; y <= sc.scrollHeight && !done(); y += step) {
      sc.scrollTop = y;
      await sleep(120);
      collect();
    }
    /* Back up as well — some virtualisers only mount in the direction of
       travel. */
    for (let y = sc.scrollHeight; y >= 0 && !done(); y -= step) {
      sc.scrollTop = y;
      await sleep(120);
      collect();
    }

    const secs = Math.round((Date.now() - t0) / 1000);
    console.log(
      `  pass ${pass} → ${store.size}${target ? ' / ' + target : ''}  (+${store.size - previous}, ${secs}s)`,
    );
  }

  /* ── 3 · output ──────────────────────────────────────────────── */

  const rows = [...store.entries()].sort((a, b) => a[0].localeCompare(b[0]));
  window.__out = rows.map(([scope, label]) => `${scope}\t${label}`).join('\n');

  console.log(`\nDONE — ${store.size}${target ? ' of ' + target : ''} in ${Math.round((Date.now() - t0) / 1000)}s`);
  if (target && store.size < target) {
    console.warn(`${target - store.size} still missing. Re-run; it accumulates.`);
  }
  console.log(window.__out);
  console.log('%cNow run:  copy(window.__out)', 'font-weight:bold');
})();
