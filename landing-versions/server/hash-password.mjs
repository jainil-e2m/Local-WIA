/* Generate an scrypt hash for any account's *_PASSWORD_HASH variable —
   AUTH_PASSWORD_HASH, CLIENT_PASSWORD_HASH or a numbered USER_n_PASSWORD_HASH:
     node server/hash-password.mjs "your-new-password"
   Set the printed value as a Railway service variable (or in .env.local) to
   rotate a password, or to add a whole account, without touching the code. */

import crypto from "node:crypto";

const password = process.argv[2];
if (!password) {
  console.error('Usage: node server/hash-password.mjs "your-new-password"');
  process.exit(1);
}

const N = 16384,
  r = 8,
  p = 1;
const salt = crypto.randomBytes(16);
const hash = crypto.scryptSync(password, salt, 64, { N, r, p });
console.log(["scrypt", N, r, p, salt.toString("base64"), hash.toString("base64")].join("$"));
