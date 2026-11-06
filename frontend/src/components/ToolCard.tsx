import { useRef } from "react";
import { Link } from "react-router-dom";
import { motion, useMotionValue, useSpring, useReducedMotion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { toolRoute, type Tool } from "@/data/tools";

export function ToolCard({ tool, index }: { tool: Tool; index: number }) {
  const reduce = useReducedMotion();
  const ref = useRef<HTMLDivElement>(null);

  const rotX = useMotionValue(0);
  const rotY = useMotionValue(0);
  const srotX = useSpring(rotX, { stiffness: 150, damping: 15 });
  const srotY = useSpring(rotY, { stiffness: 150, damping: 15 });

  function onMove(e: React.MouseEvent<HTMLDivElement>) {
    if (reduce || !ref.current) return;
    const rect = ref.current.getBoundingClientRect();
    const px = (e.clientX - rect.left) / rect.width;
    const py = (e.clientY - rect.top) / rect.height;
    rotY.set((px - 0.5) * 7);
    rotX.set((0.5 - py) * 7);
    ref.current.style.setProperty("--mx", `${e.clientX - rect.left}px`);
    ref.current.style.setProperty("--my", `${e.clientY - rect.top}px`);
  }

  function onLeave() {
    rotX.set(0);
    rotY.set(0);
  }

  const Icon = tool.icon;
  // Locked is now purely status-driven, and status already carries the tool's
  // VITE_TOOL_<ID>_ENABLED override (see data/toolFlags.ts). A link-out tool
  // opens its external dashboard; everything else opens in-app.
  const live = tool.status === "live";
  const external = tool.url.trim() !== "";

  return (
    <motion.article
      ref={ref}
      onMouseMove={onMove}
      onMouseLeave={onLeave}
      style={{ rotateX: srotX, rotateY: srotY, transformPerspective: 1000 }}
      initial={{ opacity: 0, y: 40 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-40px" }}
      transition={{ duration: 0.6, delay: index * 0.09, ease: [0.22, 1, 0.36, 1] }}
      className={cn(
        "group relative flex flex-col overflow-hidden rounded-[17px] border border-brand-lavender/40 bg-white p-7 transition-shadow duration-300",
        "hover:shadow-[0_30px_60px_-22px_rgba(39,51,140,0.32)]",
      )}
    >
      {/* cursor-follow glow */}
      <div
        className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-300 group-hover:opacity-100"
        style={{
          background:
            "radial-gradient(440px circle at var(--mx,50%) var(--my,50%), rgba(73,85,159,0.10), transparent 60%)",
        }}
        aria-hidden
      />

      <div className="relative mb-6 flex items-start justify-between gap-4">
        <div
          className="grid h-14 w-14 place-items-center rounded-[15px] text-white shadow-[0_12px_24px_-10px_rgba(39,51,140,0.5)] transition-transform duration-300 group-hover:-translate-y-1 group-hover:rotate-[-6deg] group-hover:scale-105"
          style={{ background: `linear-gradient(140deg, ${tool.from}, ${tool.to})` }}
        >
          <Icon className="h-7 w-7" strokeWidth={2} />
        </div>
        {/* "Demo", not "Live". Nothing in this engagement runs in production:
            these are consoles walked through at the blueprint review, and the
            hero counter already labels them "Demoed at review". A chip reading
            "Live" next to a mock is the one claim this app cannot support. */}
        {tool.status === "live" ? (
          <Badge variant="live">
            <span
              className="h-1.5 w-1.5 rounded-full bg-brand-teal animate-pulse-ring"
              aria-hidden
            />
            Demo
          </Badge>
        ) : (
          <Badge variant="dev">
            <span className="h-1.5 w-1.5 rounded-full bg-brand-orange" aria-hidden />
            In development
          </Badge>
        )}
      </div>

      <h3 className="relative mb-2.5 text-2xl font-bold tracking-[-0.01em] text-brand-ink">
        {tool.name}
      </h3>
      <p className="relative mb-5 text-[15.5px] leading-relaxed text-foreground">
        {tool.description}
      </p>

      <ul className="relative mb-7 flex flex-wrap gap-2">
        {tool.tags.map((tag) => (
          <li
            key={tag}
            className="rounded-full border border-brand-accent/30 bg-brand-accent/[0.08] px-3 py-1 text-xs font-semibold text-brand-secondary"
          >
            {tag}
          </li>
        ))}
      </ul>

      <div className="relative mt-auto">
        {!live ? (
          <Button variant="locked" size="sm" className="w-full" disabled>
            Coming soon
          </Button>
        ) : external ? (
          <Button asChild variant="solid" size="sm" className="w-full">
            <a href={tool.url} target="_blank" rel="noopener noreferrer">
              Open dashboard
              <ArrowRight className="h-4 w-4 transition-transform duration-300 group-hover:translate-x-1" />
            </a>
          </Button>
        ) : (
          <Button asChild variant="solid" size="sm" className="w-full">
            <Link to={toolRoute(tool)}>
              Open dashboard
              <ArrowRight className="h-4 w-4 transition-transform duration-300 group-hover:translate-x-1" />
            </Link>
          </Button>
        )}
      </div>
    </motion.article>
  );
}
