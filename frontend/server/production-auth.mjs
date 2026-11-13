/* ────────────────────────────────────────────────────────────────
   What a production start must have in place before it serves anything (S.C1).

   Command Center is the sign-in for the Content Atelier: its session decides who
   may approve content. Two things used to be allowed in production that must
   not be, because either one makes "signed in" meaningless:

     1. AUTH_DISABLED. It opens every /api route and lets /api/auth/login accept
        any email with any password. It was honoured in production with a warning
        so a demo could run from a production build; with real approvals behind
        the session that is no longer acceptable, so a production start refuses
        it. It remains a development switch (NODE_ENV other than "production").
     2. A missing SESSION_SECRET or AUTH_PASSWORD_HASH. Without the first, every
        restart signs everyone out and the key is per-process (a second replica
        cannot read the first's cookies). Without the second, the committed
        default hash, a credential in the repository's history, would still open
        the team account.

   This is a separate module so it can be unit-tested without importing
   index.mjs, which calls app.listen() at module scope.
   ──────────────────────────────────────────────────────────────── */

const FALSE_VALUES = new Set(["", "0", "false", "no", "off"]);

const present = (source, name) => {
  const value = source[name];
  return typeof value === "string" && value.trim() !== "";
};

/**
 * Why a production start must be refused, one message per problem; empty when the
 * process is not production or everything required is set.
 *
 * @param {Record<string, string | undefined>} [source] defaults to process.env
 * @returns {string[]}
 */
export function productionAuthProblems(source = process.env) {
  if (source.NODE_ENV !== "production") return [];
  const problems = [];
  const disabled = source.AUTH_DISABLED;
  if (typeof disabled === "string" && !FALSE_VALUES.has(disabled.trim().toLowerCase())) {
    problems.push(
      "AUTH_DISABLED is set. It opens every API route and lets any email and password sign in, " +
        "so it is refused when NODE_ENV=production. Unset AUTH_DISABLED (and remove VITE_AUTH_DISABLED " +
        "from the build) and give the team real accounts; see DEPLOY.md, \"Cutting over to real accounts\".",
    );
  }
  if (!present(source, "SESSION_SECRET")) {
    problems.push(
      "SESSION_SECRET is not set. Production needs one fixed key so sessions survive a restart and every " +
        "replica reads the same cookies. Generate one with: node -e \"console.log(require('crypto').randomBytes(32).toString('hex'))\"",
    );
  }
  if (!present(source, "AUTH_PASSWORD_HASH")) {
    problems.push(
      "AUTH_PASSWORD_HASH is not set. Production must not fall back to the hash committed in the repository. " +
        "Generate one with: node server/hash-password.mjs \"<password>\" (and set AUTH_EMAIL, plus USER_n_* for each further account).",
    );
  }
  return problems;
}

/** Throws one error naming every problem, so an operator fixes them in one deploy. */
export function assertProductionAuth(source = process.env) {
  const problems = productionAuthProblems(source);
  if (problems.length) {
    throw new Error(
      `Refusing to start in production (S.C1): ${problems.length} authentication problem${problems.length === 1 ? "" : "s"}.\n` +
        problems.map((p, i) => `  ${i + 1}. ${p}`).join("\n"),
    );
  }
}
