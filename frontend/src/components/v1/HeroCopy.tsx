import { Link } from "react-router-dom";
import { motion, type Variants } from "framer-motion";
import { ArrowRight, Waypoints } from "lucide-react";
import { useV1Action } from "./useV1Action";
import { useAuth } from "@/context/auth";
import { accountName } from "@/data/user";
import { greeting } from "@/lib/greeting";
import { wakeLaptop } from "./sceneBus";

const LINES: { words: string[]; accent?: boolean }[] = [
  { words: ["Your", "wedding", "business,"] },
  { words: ["Automated", "&", "simplified"], accent: true },
  { words: ["for", "growth."] },
];

const headline: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.075, delayChildren: 0.42 } },
};
const word: Variants = {
  hidden: { y: "108%", rotate: 2.5 },
  show: { y: 0, rotate: 0, transition: { duration: 1, ease: [0.22, 1, 0.36, 1] } },
};

const rise = (delay: number) => ({
  initial: { opacity: 0, y: 14 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.8, delay, ease: [0.22, 1, 0.36, 1] as const },
});

export function HeroCopy() {
  const { status, user } = useAuth();
  const run = useV1Action();

  const signedIn = status === "authenticated";
  const name = signedIn && user?.name ? accountName(user.name) : null;

  return (
    <div className="v1-copy">
      <motion.p {...rise(0.25)} className="v1-greeting">
        <span className="v1-greeting-dot" aria-hidden />
        {greeting()}
        {name ? `, ${name}` : null}
      </motion.p>

      <motion.h1 variants={headline} initial="hidden" animate="show" className="v1-headline">
        {LINES.map((line, li) => (
          <span key={li} className={line.accent ? "v1-headline-line is-accent" : "v1-headline-line"}>
            {line.words.map((w, wi) => (
              <span key={wi} className="v1-word-mask">
                <motion.span variants={word} className="v1-word">
                  {w}
                </motion.span>
              </span>
            ))}
          </span>
        ))}
      </motion.h1>

      <motion.div {...rise(1.2)} className="v1-actions">
        {status === "unauthenticated" && (
          <Link to="/login" className="v1-cta" onMouseEnter={wakeLaptop} onFocus={wakeLaptop}>
            <span>Enter Command Center</span>
            <ArrowRight className="v1-cta-arrow" strokeWidth={1.6} aria-hidden />
          </Link>
        )}
        <button
          type="button"
          className={signedIn ? "v1-cta" : "v1-watch"}
          onClick={() => run({ kind: "automations" })}
        >
          <Waypoints className="h-[18px] w-[18px]" aria-hidden />
          View automations
        </button>
      </motion.div>


    </div>
  );
}
