import { useEffect } from "react";

/** Share the landing's display faces with pages opened directly, including login. */
export function useEditorialFonts() {
  useEffect(() => {
    if (document.querySelector("link[data-v1-fonts]")) return;
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = "https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Jost:wght@400;500;600&family=Great+Vibes&family=Mrs+Saint+Delafield&display=swap";
    link.dataset.v1Fonts = "";
    document.head.appendChild(link);
  }, []);
}
