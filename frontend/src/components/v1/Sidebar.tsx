import { useEffect } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";
import { ActionLink } from "./ActionLink";
import { NAV } from "./destinations";
import { WiaMark } from "./WiaMark";

/**
 * The left rail. Labels from 1360px; an icon rail with hover labels between
 * 1100 and 1360; below that the same list lives in a drawer behind the top
 * bar's menu button.
 */
export function Sidebar({ active = "home" }: { active?: string }) {
  return (
    <motion.nav
      aria-label="Primary"
      className="v1-sidebar"
      initial={{ opacity: 0, x: -12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.8, delay: 0.15, ease: [0.22, 1, 0.36, 1] }}
    >
      <ul className="v1-nav">
        {NAV.map((item, i) => (
          <motion.li
            key={item.id}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6, delay: 0.25 + i * 0.05, ease: [0.22, 1, 0.36, 1] }}
          >
            <ActionLink
              action={item.action}
              className={cn("v1-nav-item", item.id === active && "is-active")}
              aria-label={item.label}
            >
              <item.icon className="v1-nav-icon" strokeWidth={1.5} aria-hidden />
              <span className="v1-nav-label">{item.label}</span>
              <span className="v1-nav-tip" aria-hidden>
                {item.label}
              </span>
            </ActionLink>
          </motion.li>
        ))}
      </ul>
    </motion.nav>
  );
}

export function MobileNav({
  open,
  onClose,
  active = "home",
}: {
  open: boolean;
  onClose: () => void;
  active?: string;
}) {
  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="v1-drawer-scrim"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
        >
          <motion.nav
            aria-label="Primary"
            className="v1-drawer"
            initial={{ x: "-100%" }}
            animate={{ x: 0 }}
            exit={{ x: "-100%" }}
            transition={{ duration: 0.42, ease: [0.22, 1, 0.36, 1] }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-5 pb-6 pt-5">
              <WiaMark className="h-11 w-11 text-[#1b2540]" title="Wedding Industry Ads" />
              <button type="button" className="v1-icon-btn" onClick={onClose} aria-label="Close navigation">
                <X className="h-[18px] w-[18px]" strokeWidth={1.6} />
              </button>
            </div>
            <ul className="v1-nav is-drawer">
              {NAV.map((item) => (
                <li key={item.id}>
                  <ActionLink
                    action={item.action}
                    onBeforeAction={onClose}
                    className={cn("v1-nav-item", item.id === active && "is-active")}
                  >
                    <item.icon className="v1-nav-icon" strokeWidth={1.5} aria-hidden />
                    <span className="v1-nav-label">{item.label}</span>
                  </ActionLink>
                </li>
              ))}
            </ul>
          </motion.nav>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
