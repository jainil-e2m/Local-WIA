import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { Bookmark, ChevronDown, LogIn, LogOut } from "lucide-react";
import { cn } from "@/lib/utils";
import { BookmarksDock } from "@/components/BookmarksDock";
import { currentUser, initials, accountName } from "@/data/user";
import { useAuth } from "@/context/auth";
import { useEdgeReveal } from "@/hooks/useEdgeReveal";

/** Geometry for the header's pills (Bookmarks, Sign in) — the marble design's
    30px capsule: hairline border, near-white fill, 11px semibold ink. */
const quickLinkClass =
  "hidden h-[30px] items-center gap-1.5 rounded-full border border-[#dcdde6] bg-white/90 px-[14px] text-[11px] font-semibold leading-none text-[#1f2130] shadow-[0_1px_2px_rgba(20,20,60,0.04)] transition-colors hover:border-brand-stone hover:bg-white md:inline-flex";

export function Header() {
  const [scrolled, setScrolled] = useState(false);
  // Bookmarks island: click the pill to pin it open, or park the cursor at the
  // right edge to peek (which auto-dismisses when the cursor leaves).
  const bookmarks = useEdgeReveal();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <motion.header
      initial={{ y: -80, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1], delay: 0.1 }}
      className={cn(
        "fixed inset-x-0 top-0 z-50 flex h-[52px] items-center transition-all duration-300",
        scrolled
          ? "border-b border-brand-mist bg-white/85 backdrop-blur-xl shadow-[0_10px_30px_-12px_rgba(34,30,23,0.14)]"
          : "bg-transparent",
      )}
    >
      {/* Same shell as the marble hero, so the badge and the copy column
          share one left edge. */}
      <div className="landing-shell flex items-center justify-between gap-6">
        <a
          href="#top"
          aria-label="Wedding Industry Ads home"
          className="flex items-center gap-[13px]"
        >
          {/* Circular badge mark, 39px in the 52px bar, as in the design. */}
          <img
            src="/logos/wia_logo.webp"
            alt="Wedding Industry Ads"
            className="h-[39px] w-[39px]"
          />
          <span className="hidden h-[26px] w-px bg-[#dcc9ad] sm:block" aria-hidden />
          <span className="hidden text-[11px] font-medium uppercase leading-none tracking-[0.29em] text-[#222] sm:block">
            Command&nbsp;Center
          </span>
        </a>

        <div className="flex items-center gap-[18px]">
          {/* Bookmarks board — the dashboard's own shortcut shelf. While the
              island is showing, the pill adopts the primary CTA treatment
              ("View automations"): solid brand fill and its orange glow. */}
          <button
            type="button"
            onClick={bookmarks.toggle}
            aria-expanded={bookmarks.isOpen}
            /* The island's outside-click handler skips this, so pointerdown
               can't close it a beat before the click re-opens it. */
            data-bookmarks-ui
            className={cn(
              quickLinkClass,
              bookmarks.isOpen &&
                "border-brand-primary bg-brand-primary text-white shadow-[0_12px_30px_-10px_rgba(80,112,255,0.45)] hover:border-brand-primary hover:bg-brand-primary",
            )}
          >
            <Bookmark
              className={cn("h-3 w-3", bookmarks.isOpen ? "text-white" : "text-[#1f2130]")}
              aria-hidden
            />
            Bookmarks
          </button>

          {/* The audit-history pill used to sit here. Removed so History is
              not reachable from anywhere in the Command Center; the /history
              route itself is left intact and still resolves if typed, the
              same treatment the four inherited automations got in
              data/tools.ts. */}

          <UserMenu />
        </div>
      </div>

      <BookmarksDock open={bookmarks.isOpen} onClose={bookmarks.close} onPin={bookmarks.pin} />
    </motion.header>
  );
}

/** Signed-in user pill with a dropdown (log out); a sign-in pill when guest. */
function UserMenu() {
  const { status, user, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close on outside click / Escape.
  useEffect(() => {
    if (!open) return;
    const onPointerDown = (e: PointerEvent) => {
      if (!menuRef.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  // While the session check is in flight, hold the space to avoid layout shift.
  if (status === "loading") {
    return <span className="hidden h-[30px] w-[110px] lg:block" aria-hidden />;
  }

  if (status === "unauthenticated") {
    return (
      <Link to="/login" className={cn(quickLinkClass, "md:hidden lg:inline-flex")}>
        <LogIn className="h-3 w-3 text-[#1f2130]" aria-hidden />
        Sign in
      </Link>
    );
  }

  const displayName = user?.name ?? currentUser.name;

  async function onLogout() {
    setOpen(false);
    await logout();
    navigate("/", { replace: true });
  }

  return (
    <div ref={menuRef} className="relative hidden lg:block">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label={`Signed in as ${displayName}`}
        aria-expanded={open}
        aria-haspopup="menu"
        className="group inline-flex h-[30px] items-center gap-[9px] rounded-full border border-[#dcdde6] bg-white/90 pl-[3px] pr-[14px] shadow-[0_1px_2px_rgba(20,20,60,0.04)] transition-colors hover:border-brand-stone hover:bg-white"
      >
        <span
          aria-hidden
          className="grid h-[23px] w-[23px] place-items-center rounded-full bg-[#1c1d24] text-[8.5px] font-bold leading-none tracking-[0.03em] text-white"
        >
          {initials(displayName)}
        </span>
        <span className="max-w-[168px] truncate text-[11px] font-semibold leading-none text-[#1f2130]">
          {accountName(displayName)}
        </span>
        <ChevronDown
          className={cn(
            "h-3 w-3 text-[#1f2130] transition-transform duration-300",
            open ? "rotate-180" : "group-hover:translate-y-0.5",
          )}
          aria-hidden
        />
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            role="menu"
            initial={{ opacity: 0, y: -6, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.97 }}
            transition={{ duration: 0.18, ease: [0.22, 1, 0.36, 1] }}
            className="absolute right-0 top-[calc(100%+10px)] w-60 overflow-hidden rounded-2xl border border-brand-mist bg-white/95 p-1.5 shadow-[0_24px_60px_-18px_rgba(34,30,23,0.22)] backdrop-blur-xl"
          >
            <div className="px-3.5 pb-2.5 pt-2.5">
              <p className="text-[13px] font-semibold text-brand-accent">{displayName}</p>
              {user?.email && (
                <p className="mt-0.5 truncate text-[12px] text-brand-gray">{user.email}</p>
              )}
            </div>
            <div className="mx-2 h-px bg-brand-mist" aria-hidden />
            <button
              type="button"
              role="menuitem"
              onClick={onLogout}
              className="mt-1 flex w-full items-center gap-2.5 rounded-xl px-3.5 py-2.5 text-left text-[13px] font-semibold text-brand-secondary transition-colors hover:bg-brand-mist/60 hover:text-brand-accent"
            >
              <LogOut className="h-[15px] w-[15px] text-brand-slate" aria-hidden />
              Log out
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
