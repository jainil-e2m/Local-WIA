import { motion } from "framer-motion";
import { ArrowUpRight, BarChart3, Database, Sparkles } from "lucide-react";
import { EXTERNAL } from "./destinations";
import { WiaMark } from "./WiaMark";

/* ────────────────────────────────────────────────────────────────
   Below the hero — where "Scroll to explore" lands.

   The consoles the signed-in role can open, and the roadmap phase by
   phase, both read from the same data as the hero's figures: a count
   can't say one thing up there and another down here.
   ──────────────────────────────────────────────────────────────── */

const reveal = (delay = 0) => ({
  initial: { opacity: 0, y: 26 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, amount: 0.25 },
  transition: { duration: 0.9, delay, ease: [0.22, 1, 0.36, 1] as const },
});

function deployedAtelierUrl(): string | undefined {
  try {
    const url = new URL(import.meta.env.VITE_CONTENT_ATELIER_URL?.trim() ?? "");
    return ["https:", "http:"].includes(url.protocol) ? url.href : undefined;
  } catch {
    return undefined;
  }
}

const AUTOMATIONS = [
  {
    name: "Content Atelier",
    status: "In development",
    kicker: "Voice to publish-ready work",
    description:
      "Turns the founder voice library, campaign context and proven examples into structured briefs and approval-ready content without flattening the brand into generic copy.",
    outcome: "A repeatable editorial workflow with the source, rationale and review state attached to every draft.",
    tags: ["Voice library", "Brief generation", "Approval queue"],
    icon: Sparkles,
  },
  {
    name: "Client Knowledge Base",
    status: "Coming soon",
    kicker: "One source of client truth",
    description:
      "Organizes client context, decisions, assets, meeting history and brand guidance into a searchable operating record the whole team can use.",
    outcome: "Answers arrive with the client-specific evidence behind them, instead of living in one person’s memory.",
    tags: ["Client context", "Decision history", "Searchable evidence"],
    icon: Database,
  },
  {
    name: "Paid Media Reporting",
    status: "Coming soon",
    kicker: "Performance into decisions",
    description:
      "Pulls paid-channel performance into a consistent reporting flow, identifies meaningful movement and prepares the plain-English narrative for review.",
    outcome: "A client-ready reporting rhythm that explains what changed, why it matters and what the team should do next.",
    tags: ["Google + Meta", "Executive summary", "Review gate"],
    icon: BarChart3,
  },
] as const;

export function ExploreSection() {
  const atelierUrl = deployedAtelierUrl();
  return (
    <section id="v1-explore" className="v1-explore" aria-labelledby="v1-explore-title">
      <div className="v1-explore-inner">
        <motion.p {...reveal()} className="v1-greeting">
          <span className="v1-greeting-dot" aria-hidden />
          Inside the Command Center
        </motion.p>
        <motion.h2 {...reveal(0.08)} id="v1-explore-title" className="v1-explore-title">
          What&rsquo;s running now, <em>and what&rsquo;s next.</em>
        </motion.h2>
        <motion.p {...reveal(0.16)} className="v1-explore-lede">
          Three connected automations carry the work from institutional knowledge to publish-ready content and
          client-facing performance decisions.
        </motion.p>

        <div className="v1-automation-stack">
          {AUTOMATIONS.map((item, i) => (
            <motion.article
              key={item.name}
              {...reveal(0.08 * i)}
              className={`v1-automation-row${i % 2 ? " is-reverse" : ""}`}
            >
              <div className="v1-automation-visual">
                <span className="v1-automation-index">0{i + 1}</span>
                <span className="v1-automation-icon">
                  <item.icon aria-hidden strokeWidth={1.45} />
                </span>
                <span className="v1-automation-signal" aria-hidden>
                  <i />
                  <i />
                  <i />
                </span>
                <p>{item.name}</p>
                <span className="v1-automation-live">
                  {item.status}
                </span>
                {item.name === "Content Atelier" && (
                  atelierUrl ? (
                    <a className="v1-automation-view" href={atelierUrl} aria-label="View Content Atelier">
                      View Here <ArrowUpRight size={16} strokeWidth={1.6} aria-hidden />
                    </a>
                  ) : (
                    <button className="v1-automation-view" type="button" disabled title="Content Atelier is in development">
                      View Here <ArrowUpRight size={16} strokeWidth={1.6} aria-hidden />
                    </button>
                  )
                )}
              </div>
              <div className="v1-automation-copy">
                <p className="v1-pop-eyebrow">{item.kicker}</p>
                <h3>{item.name}</h3>
                <p className="v1-automation-description">{item.description}</p>
                <p className="v1-automation-outcome">{item.outcome}</p>
                <ul className="v1-automation-tags" aria-label={`${item.name} capabilities`}>
                  {item.tags.map((tag) => (
                    <li key={tag}>{tag}</li>
                  ))}
                </ul>
              </div>
            </motion.article>
          ))}
        </div>
      </div>

      <footer className="v1-footer">
        <div className="v1-footer-inner">
          <WiaMark className="h-12 w-12 text-[#1b2540]" title="Wedding Industry Ads" />
          <p className="v1-footer-line">
            <span className="v1-tagline-rule" aria-hidden />
            Building a stronger wedding industry
          </p>
          <nav className="v1-footer-links" aria-label="Elsewhere">
            {EXTERNAL.map((e) => (
              <a key={e.id} href={e.href} target="_blank" rel="noopener noreferrer">
                {e.label}
                <ArrowUpRight className="h-[12px] w-[12px]" strokeWidth={1.8} aria-hidden />
              </a>
            ))}
          </nav>
        </div>
      </footer>
    </section>
  );
}
