import { createContext, useContext } from "react";
import type { V1Action } from "./destinations";

/* The landing owns the overlays (automations fan, overview, palette), so the
   pieces that trigger them — sidebar, cards, palette rows — reach them
   through this rather than threading callbacks through the scene. */
export const V1ActionContext = createContext<(action: V1Action) => void>(() => {});

export function useV1Action() {
  return useContext(V1ActionContext);
}
