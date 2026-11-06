import { motion } from "framer-motion";
import { ToolCard } from "@/components/ToolCard";
import { toolsForRole } from "@/data/tools";
import { useAuth } from "@/context/auth";

export function ToolsSection() {
  const { user } = useAuth();
  const visibleTools = toolsForRole(user?.role);
  return (
    <section
      id="tools"
      className="relative bg-white px-6 pb-32 pt-28"
      style={{
        backgroundImage:
          "radial-gradient(900px 400px at 12% 0%, rgba(249,250,251,0.9), transparent 60%)",
      }}
    >
      <div className="container">
        <motion.header
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-60px" }}
          transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
          className="mb-16 max-w-2xl"
        >
          <p className="mb-3.5 text-[13px] font-bold uppercase tracking-[0.3em] text-brand-orange">
            Your Automations
          </p>
          <h2 className="mb-4 text-[clamp(2.1rem,4.6vw,3.5rem)] font-extrabold leading-[1.08] tracking-[-0.015em] text-brand-primary">
            Pick a dashboard
          </h2>
          <p className="text-lg text-foreground">
            Consoles demoed at the blueprint review open instantly. The rest are on the roadmap, being built by your E2M team.
          </p>
        </motion.header>

        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {visibleTools.map((tool, i) => (
            <ToolCard key={tool.id} tool={tool} index={i} />
          ))}
        </div>
      </div>
    </section>
  );
}
