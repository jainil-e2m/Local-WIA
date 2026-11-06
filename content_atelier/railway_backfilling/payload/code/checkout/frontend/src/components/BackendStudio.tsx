import React, { useState } from "react";
import { SQLWeeklyAngles } from "./SQLWeeklyAngles";
import { SQLBriefs } from "./SQLBriefs";
import { StoredPacks } from "./StoredPacks";

export function BackendStudio() {
  const [tab, setTab] = useState("angles");
  return (
    <div className="space-y-6">
      <h1 className="font-editorial text-4xl text-[#173354]">Weekly Studio</h1>
      <nav aria-label="Editorial pipeline" className="flex gap-3 flex-wrap">
        {[
          ["angles", "Content Angles"],
          ["briefs", "Content Briefing"],
          ["packs", "Content Packs"],
          ["scheduled", "Scheduled Content"],
        ].map(([id, label]) => (
          <button
            key={id}
            aria-pressed={tab === id}
            className={`rounded-full border px-5 py-3 text-sm ${tab === id ? "bg-[#173354] text-white" : "bg-white"}`}
            onClick={() => setTab(id)}
          >
            {label}
          </button>
        ))}
      </nav>
      {tab === "angles" && <SQLWeeklyAngles />}
      {tab === "briefs" && <SQLBriefs />}
      {tab === "packs" && <StoredPacks />}
      {tab === "scheduled" && <StoredPacks scheduledOnly />}
    </div>
  );
}
