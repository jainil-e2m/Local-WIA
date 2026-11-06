import { describe, it, expect } from "vitest";
import { assertProductionAuth, productionAuthProblems } from "./production-auth.mjs";

const REAL = { NODE_ENV: "production", SESSION_SECRET: "a".repeat(64), AUTH_PASSWORD_HASH: "scrypt$16384$8$1$salt$hash" };

describe("productionAuthProblems", () => {
  it("accepts a production start with a session secret and a password hash", () => {
    expect(productionAuthProblems(REAL)).toEqual([]);
    expect(() => assertProductionAuth(REAL)).not.toThrow();
  });

  it("refuses AUTH_DISABLED in production, whatever else is set", () => {
    for (const value of ["1", "true", "yes", "anything"]) {
      const problems = productionAuthProblems({ ...REAL, AUTH_DISABLED: value });
      expect(problems).toHaveLength(1);
      expect(problems[0]).toMatch(/AUTH_DISABLED is set/);
    }
  });

  it("treats an explicit false value as unset", () => {
    for (const value of ["", "0", "false", "off", " No "]) {
      expect(productionAuthProblems({ ...REAL, AUTH_DISABLED: value })).toEqual([]);
    }
  });

  it("requires SESSION_SECRET and AUTH_PASSWORD_HASH, blank counting as missing", () => {
    expect(productionAuthProblems({ NODE_ENV: "production" })).toHaveLength(2);
    expect(productionAuthProblems({ ...REAL, SESSION_SECRET: "   " })[0]).toMatch(/SESSION_SECRET is not set/);
    expect(productionAuthProblems({ ...REAL, AUTH_PASSWORD_HASH: "" })[0]).toMatch(/AUTH_PASSWORD_HASH is not set/);
  });

  it("names every problem in one error so one deploy fixes them all", () => {
    expect(() => assertProductionAuth({ NODE_ENV: "production", AUTH_DISABLED: "1" })).toThrow(
      /3 authentication problems[\s\S]*AUTH_DISABLED[\s\S]*SESSION_SECRET[\s\S]*AUTH_PASSWORD_HASH/,
    );
  });

  it("changes nothing outside production: AUTH_DISABLED stays a development switch", () => {
    expect(productionAuthProblems({ AUTH_DISABLED: "1" })).toEqual([]);
    expect(productionAuthProblems({ NODE_ENV: "development", AUTH_DISABLED: "1" })).toEqual([]);
    expect(productionAuthProblems({ NODE_ENV: "test" })).toEqual([]);
  });
});
