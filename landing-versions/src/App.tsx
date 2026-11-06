import { Suspense, lazy } from "react";
import { useSearchParams } from "react-router-dom";
import { Header } from "@/components/Header";
import { Hero } from "@/components/Hero";
import { MarbleHero } from "@/components/MarbleHero";

/* The editorial landing is the default. The earlier heroes stay reachable rather
   than deleted, so either can come back without archaeology:
     ?variant=classic   sky loop + bouquet column (the previous default)
     ?variant=sky       sky loop, centred single column
     ?variant=gradient  the original gradient/grid/orb hero
     ?variant=marble    the previous marble landing
   Hero.tsx resolves those three itself.

     ?variant=1         the editorial still-life landing, with its own shell
                        (components/v1). Lazy, so its scene, fonts and styles
                        load only when this landing is selected.

   ToolsSection + Footer are intentionally not rendered — automations are
   reached via the "View automations" launcher in the hero. Components are
   kept in src/components in case they're wanted back. */
const PREVIOUS_HEROES = new Set(["classic", "sky", "gradient", "birds"]);

const V1Landing = lazy(() => import("@/components/v1/V1Landing"));

export default function App() {
  const [searchParams] = useSearchParams();
  const variant = searchParams.get("variant") ?? "";

  if (!PREVIOUS_HEROES.has(variant) && variant !== "marble") {
    return (
      <Suspense fallback={<div className="min-h-[100svh] bg-[#fdfdfd]" aria-hidden />}>
        <V1Landing />
      </Suspense>
    );
  }

  const previous = PREVIOUS_HEROES.has(variant);

  return (
    <>
      <Header />
      <main>{previous ? <Hero /> : <MarbleHero />}</main>
    </>
  );
}
