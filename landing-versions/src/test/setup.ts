// Vitest global test setup — runs before every test file.
// Adds jest-dom matchers (e.g. toBeInTheDocument) and clears the DOM
// between tests so component renders don't leak into one another.
import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

afterEach(() => {
  cleanup();
});
