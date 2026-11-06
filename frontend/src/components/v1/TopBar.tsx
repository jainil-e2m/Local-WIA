import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { Bell, ChevronDown, LogIn, LogOut, Menu } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/context/auth";
import { accountName, currentUser, initials } from "@/data/user";
import { timelineNotices, type NoticeTone } from "./notifications";

const pop = {
  initial: { opacity: 0, y: -6, scale: 0.98 },
  animate: { opacity: 1, y: 0, scale: 1 },
  exit: { opacity: 0, y: -6, scale: 0.98 },
  transition: { duration: 0.2, ease: [0.22, 1, 0.36, 1] as const },
};

/** Closes a popover on an outside pointerdown or Escape. */
function useDismiss(open: boolean, ref: React.RefObject<HTMLElement>, close: () => void) {
  useEffect(() => {
    if (!open) return undefined;
    const onDown = (e: PointerEvent) => {
      if (!ref.current?.contains(e.target as Node)) close();
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
    };
    document.addEventListener("pointerdown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open, ref, close]);
}

export function TopBar({ onMenu }: { onMenu?: () => void }) {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <motion.header
      initial={{ opacity: 0, y: -18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1], delay: 0.05 }}
      className={cn("v1-topbar", scrolled && "is-scrolled")}
    >
      {onMenu && (
        <button type="button" className="v1-menu-btn" onClick={onMenu} aria-label="Open navigation">
          <Menu className="h-[18px] w-[18px]" strokeWidth={1.6} />
        </button>
      )}

      <a href="#v1-top" className="v1-brand" aria-label="Wedding Industry Ads — Command Center home">
        <img src="/logos/wia_logo.webp" alt="Wedding Industry Ads" className="v1-brand-mark" />
        <span className="v1-brand-rule" aria-hidden />
        <span className="v1-brand-product">Command Center</span>
      </a>

      <div className="v1-topbar-right">
        <Notifications />
        <span className="v1-vrule" aria-hidden />
        <UserMenu />
      </div>
    </motion.header>
  );
}

/* ── Notifications ──────────────────────────────────────────────── */

const READ_KEY = "wia:v1:read-notices";

function readSet(): Set<string> {
  try {
    return new Set(JSON.parse(localStorage.getItem(READ_KEY) ?? "[]") as string[]);
  } catch {
    return new Set();
  }
}

const TONE: Record<NoticeTone, { label: string; className: string }> = {
  overdue: { label: "Needs attention", className: "is-overdue" },
  started: { label: "In build", className: "is-started" },
  soon: { label: "Up next", className: "is-soon" },
  done: { label: "Delivered", className: "is-done" },
};

function Notifications() {
  const [open, setOpen] = useState(false);
  const [read, setRead] = useState<Set<string>>(() => readSet());
  const ref = useRef<HTMLDivElement>(null);
  useDismiss(open, ref, () => setOpen(false));
  const notices = useMemo(() => timelineNotices(), []);
  const unread = notices.filter((n) => !read.has(n.id)).length;

  const markAll = () => {
    const next = new Set([...read, ...notices.map((n) => n.id)]);
    setRead(next);
    try {
      localStorage.setItem(READ_KEY, JSON.stringify([...next]));
    } catch {
      /* private mode — the dot simply comes back next visit */
    }
  };

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        className="v1-icon-btn"
        aria-label={unread ? `Notifications, ${unread} unread` : "Notifications"}
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <Bell className="h-[19px] w-[19px]" strokeWidth={1.6} />
        {unread > 0 && <span className="v1-bell-dot" aria-hidden />}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div {...pop} className="v1-popover v1-notice-pop" role="dialog" aria-label="Notifications">
            <div className="flex items-center justify-between gap-4 px-4 pb-2 pt-3.5">
              <div>
                <p className="v1-pop-eyebrow">Build timeline</p>
                <p className="v1-pop-title">What&rsquo;s moving</p>
              </div>
              <button
                type="button"
                onClick={markAll}
                disabled={unread === 0}
                className="v1-text-btn"
              >
                Mark all read
              </button>
            </div>
            <ul className="max-h-[340px] overflow-y-auto px-2 pb-2">
              {notices.map((n) => (
                <li key={n.id} className={cn("v1-notice", !read.has(n.id) && "is-unread")}>
                  <span className={cn("v1-notice-tone", TONE[n.tone].className)} aria-hidden />
                  <div className="min-w-0">
                    <p className="v1-notice-kicker">{TONE[n.tone].label}</p>
                    <p className="v1-notice-title">{n.title}</p>
                    <p className="v1-notice-detail">{n.detail}</p>
                  </div>
                </li>
              ))}
              {notices.length === 0 && (
                <li className="px-3 py-6 text-center text-[12px] text-[#8a8f99]">
                  Nothing new on the timeline.
                </li>
              )}
            </ul>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/* ── User ───────────────────────────────────────────────────────── */

function UserMenu() {
  const { status, user, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useDismiss(open, ref, () => setOpen(false));

  if (status === "loading") return <span className="v1-user-skeleton" aria-hidden />;

  if (status === "unauthenticated") {
    return (
      <Link to="/login" className="v1-signin">
        <LogIn className="h-[14px] w-[14px]" strokeWidth={1.8} aria-hidden />
        Sign in
      </Link>
    );
  }

  const name = user?.name ?? currentUser.name;

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        className="v1-user"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={`Signed in as ${name}`}
      >
        <span className="v1-avatar" aria-hidden>
          {initials(name)}
        </span>
        <span className="v1-user-name">{accountName(name)}</span>
        <ChevronDown
          className={cn("h-[14px] w-[14px] transition-transform duration-300", open && "rotate-180")}
          strokeWidth={1.8}
          aria-hidden
        />
      </button>
      <AnimatePresence>
        {open && (
          <motion.div {...pop} role="menu" className="v1-popover v1-user-pop">
            <div className="px-3.5 pb-2.5 pt-2.5">
              <p className="text-[13px] font-semibold text-[#0e1c38]">{name}</p>
              {user?.email && <p className="mt-0.5 truncate text-[12px] text-[#8a8f99]">{user.email}</p>}
            </div>
            <div className="mx-2 h-px bg-[#eceef2]" aria-hidden />
            <button
              type="button"
              role="menuitem"
              className="v1-pop-row mt-1 w-full"
              onClick={async () => {
                setOpen(false);
                await logout();
                navigate("/", { replace: true });
              }}
            >
              <LogOut className="h-[15px] w-[15px] text-[#8a8f99]" aria-hidden />
              Log out
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
