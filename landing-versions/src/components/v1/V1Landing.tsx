import { useEditorialFonts } from "@/hooks/useEditorialFonts";
import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowDown } from "lucide-react";
import { AutomationsModal } from "@/components/AutomationsModal";
import { TopBar } from "./TopBar";
import { HeroCopy } from "./HeroCopy";
import { HeroScene } from "./scene/HeroScene";
import { CommandPalette } from "./CommandPalette";
import { OverviewModal } from "./OverviewModal";
import { ExploreSection } from "./ExploreSection";
import { V1ActionContext } from "./useV1Action";
import type { V1Action } from "./destinations";
import "./v1.css";

/* ────────────────────────────────────────────────────────────────
   Landing variant 1 — `/?variant=1`.

   An editorial still life: a desk by the Amalfi coast, the laptop that
   runs the business on it, and the Command Center's five surfaces riding
   a gold orbit round it. Its own shell (top bar + rail) rather than the
   shared Header, because the design is one composition with it.

   Everything that looks like a number or a destination is wired to the
   same sources the rest of the hub reads (see destinations.ts).
   ──────────────────────────────────────────────────────────────── */

export default function V1Landing() {
  useEditorialFonts();
  const navigate = useNavigate();
  const [automations, setAutomations] = useState(false);
  const [overview, setOverview] = useState(false);
  const [palette, setPalette] = useState(false);

  /* ⌘K / Ctrl+K anywhere, and "/" when not typing, open the palette. */
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const typing = e.target instanceof HTMLElement && e.target.closest("input, textarea, [contenteditable]");
      if ((e.key === "k" || e.key === "K") && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setPalette((v) => !v);
      } else if (e.key === "/" && !typing && !e.metaKey && !e.ctrlKey) {
        e.preventDefault();
        setPalette(true);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const run = useCallback(
    (action: V1Action) => {
      switch (action.kind) {
        case "route":
          navigate(action.to);
          break;
        case "external":
          window.open(action.href, "_blank", "noopener,noreferrer");
          break;
        case "automations":
          setAutomations(true);
          break;
        case "overview":
          setOverview(true);
          break;
        case "top":
          window.scrollTo({ top: 0, behavior: "smooth" });
          break;
        case "explore":
          document.getElementById("v1-explore")?.scrollIntoView({ behavior: "smooth" });
          break;
      }
    },
    [navigate],
  );

  return (
    <V1ActionContext.Provider value={run}>
      <div className="v1">
        <TopBar />

        <main className="v1-main">
          <section id="v1-top" className="v1-hero" aria-label="Command Center">
            <div className="v1-hero-grid">
              <HeroCopy />
              <HeroScene />
            </div>

            <motion.button
              type="button"
              className="v1-scroll"
              onClick={() => run({ kind: "explore" })}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 1, delay: 2 }}
            >
              <span className="v1-scroll-line" aria-hidden />
              Scroll to explore
              <ArrowDown className="v1-scroll-arrow" strokeWidth={1.6} aria-hidden />
            </motion.button>

            <motion.p
              className="v1-tagline"
              initial={{ opacity: 0, x: 12 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 1, delay: 2.1 }}
            >
              <span className="v1-tagline-rule" aria-hidden />
              <span>
                Building a stronger
                <br />
                wedding industry
              </span>
            </motion.p>
          </section>

          <ExploreSection />
        </main>

        <AutomationsModal open={automations} onClose={() => setAutomations(false)} />
        <OverviewModal open={overview} onClose={() => setOverview(false)} />
        <CommandPalette open={palette} onClose={() => setPalette(false)} />
      </div>
    </V1ActionContext.Provider>
  );
}
