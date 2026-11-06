import React from 'react';

/* A view that renders from the built-in examples in src/data instead of the backend carries this marker until it is
   replaced (plan 1.F4), so nobody mistakes an example for a stored call, card or brief. */
export function SampleDataMarker() {
  return <div role="note" data-sample-data className="mb-4 flex items-start gap-3 rounded-xl border border-dashed border-[#C6A56A] bg-[#FBF6EA] px-4 py-3 text-sm text-[#7A5E1E]">
    <span className="rounded-full bg-[#C6A56A] px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-white">Sample data</span>
    <span>This screen shows built-in examples, not your stored calls, ideas or briefs. Nothing here is saved to the workspace.</span>
  </div>;
}
