import { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowUpRight, CornerDownLeft, Globe, Play, Search, Sparkles, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/context/auth";
import { toolsForRole, toolRoute } from "@/data/tools";
import { EXTERNAL, NAV, type V1Action } from "./destinations";
import { useV1Action } from "./useV1Action";

/* ────────────────────────────────────────────────────────────────
   ⌘K. Everything the landing can reach, in one list: the rail's pages,
   every console the signed-in role can open, the three outside
   destinations, and the page's own actions. Built from the same tables
   as the rail and the cards, so it can never offer a destination they
   don't.
   ──────────────────────────────────────────────────────────────── */

interface Entry {
  id: string;
  group: string;
  label: string;
  hint: string;
  icon: LucideIcon;
  action: V1Action;
}

function useEntries(): Entry[] {
  const { user } = useAuth();
  return useMemo(() => {
    const pages: Entry[] = NAV.map((n) => ({
      id: `nav:${n.id}`,
      group: "Navigate",
      label: n.label,
      hint: n.hint,
      icon: n.icon,
      action: n.action,
    }));
    const consoles: Entry[] = toolsForRole(user?.role).map((t) => ({
      id: `tool:${t.id}`,
      group: "Consoles",
      label: t.name,
      hint: t.status === "live" ? (t.tags.slice(0, 2).join(" · ") || "Open") : "On the roadmap · coming soon",
      icon: t.icon,
      action: t.status === "live" ? { kind: "route", to: toolRoute(t) } : { kind: "automations" },
    }));
    const outside: Entry[] = EXTERNAL.map((e) => ({
      id: `ext:${e.id}`,
      group: "Destinations",
      label: e.label,
      hint: e.hint,
      icon: Globe,
      action: { kind: "external", href: e.href },
    }));
    const actions: Entry[] = [
      { id: "act:overview", group: "Actions", label: "Watch overview", hint: "A two-minute tour of the hub", icon: Play, action: { kind: "overview" } },
      { id: "act:automations", group: "Actions", label: "View automations", hint: "The full library", icon: Sparkles, action: { kind: "automations" } },
    ];
    return [...pages, ...consoles, ...outside, ...actions];
  }, [user?.role]);
}

/** Subsequence match, scored so prefix and word-start hits rank first. */
function score(q: string, text: string): number {
  if (!q) return 1;
  const t = text.toLowerCase();
  const i = t.indexOf(q);
  if (i === 0) return 100;
  if (i > 0) return t[i - 1] === " " ? 80 : 60;
  let ti = 0;
  for (const ch of q) {
    ti = t.indexOf(ch, ti);
    if (ti < 0) return 0;
    ti++;
  }
  return 20;
}

export function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const entries = useEntries();
  const run = useV1Action();
  const [q, setQ] = useState("");
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLUListElement>(null);

  /* Groups keep their order (so each header appears once); within a group
     the best match comes first. */
  const results = useMemo(() => {
    const query = q.trim().toLowerCase();
    const order = new Map<string, number>();
    entries.forEach((e) => order.has(e.group) || order.set(e.group, order.size));
    return entries
      .map((e) => ({ e, s: Math.max(score(query, e.label), score(query, e.hint) * 0.6) }))
      .filter((r) => r.s > 0)
      .sort((a, b) => order.get(a.e.group)! - order.get(b.e.group)! || (query ? b.s - a.s : 0))
      .map((r) => r.e);
  }, [entries, q]);

  useEffect(() => {
    if (!open) return undefined;
    setQ("");
    setActive(0);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const t = window.setTimeout(() => inputRef.current?.focus(), 30);
    return () => {
      window.clearTimeout(t);
      document.body.style.overflow = prev;
    };
  }, [open]);

  useEffect(() => setActive(0), [q]);

  useEffect(() => {
    listRef.current?.querySelector<HTMLElement>(`[data-index="${active}"]`)?.scrollIntoView({ block: "nearest" });
  }, [active]);

  const choose = (e: Entry | undefined) => {
    if (!e) return;
    onClose();
    run(e.action);
  };

  const onKeyDown = (ev: React.KeyboardEvent) => {
    if (ev.key === "ArrowDown") {
      ev.preventDefault();
      setActive((a) => Math.min(results.length - 1, a + 1));
    } else if (ev.key === "ArrowUp") {
      ev.preventDefault();
      setActive((a) => Math.max(0, a - 1));
    } else if (ev.key === "Enter") {
      ev.preventDefault();
      choose(results[active]);
    } else if (ev.key === "Escape") {
      ev.preventDefault();
      onClose();
    }
  };

  let lastGroup = "";

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="v1-overlay is-palette"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          onMouseDown={onClose}
        >
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-label="Search the Command Center"
            className="v1-palette"
            initial={{ opacity: 0, y: -14, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.98 }}
            transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
            onMouseDown={(e) => e.stopPropagation()}
            onKeyDown={onKeyDown}
          >
            <div className="v1-palette-search">
              <Search className="h-[18px] w-[18px] text-[#8a8f99]" strokeWidth={1.6} aria-hidden />
              <input
                ref={inputRef}
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Search consoles, pages and destinations…"
                aria-label="Search"
                aria-controls="v1-palette-list"
                aria-activedescendant={results[active] ? `v1-pal-${results[active].id}` : undefined}
                role="combobox"
                aria-expanded="true"
                autoComplete="off"
                spellCheck={false}
              />
              <kbd className="v1-kbd">esc</kbd>
            </div>

            <ul ref={listRef} id="v1-palette-list" role="listbox" className="v1-palette-list">
              {results.map((e, i) => {
                const header = e.group !== lastGroup ? e.group : null;
                lastGroup = e.group;
                const Icon = e.icon;
                return (
                  <li key={e.id} role="presentation">
                    {header && <p className="v1-palette-group">{header}</p>}
                    <div
                      id={`v1-pal-${e.id}`}
                      role="option"
                      aria-selected={i === active}
                      data-index={i}
                      className={cn("v1-palette-row", i === active && "is-active")}
                      onMouseMove={() => setActive(i)}
                      onClick={() => choose(e)}
                    >
                      <span className="v1-palette-icon">
                        <Icon className="h-[16px] w-[16px]" strokeWidth={1.6} aria-hidden />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="v1-palette-label">{e.label}</span>
                        <span className="v1-palette-hint">{e.hint}</span>
                      </span>
                      {e.action.kind === "external" ? (
                        <ArrowUpRight className="h-[14px] w-[14px] text-[#9aa0aa]" strokeWidth={1.6} aria-hidden />
                      ) : (
                        <CornerDownLeft className="v1-palette-enter" strokeWidth={1.6} aria-hidden />
                      )}
                    </div>
                  </li>
                );
              })}
              {results.length === 0 && (
                <li className="px-5 py-10 text-center text-[13px] text-[#8a8f99]">
                  Nothing matches &ldquo;{q}&rdquo;.
                </li>
              )}
            </ul>

            <div className="v1-palette-foot">
              <span>
                <kbd className="v1-kbd">↑</kbd>
                <kbd className="v1-kbd">↓</kbd> to move
              </span>
              <span>
                <kbd className="v1-kbd">↵</kbd> to open
              </span>
              <span className="ml-auto">Command Center</span>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
