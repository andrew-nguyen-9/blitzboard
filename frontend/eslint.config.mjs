import { FlatCompat } from "@eslint/eslintrc";

const compat = new FlatCompat({ baseDirectory: import.meta.dirname });

// Next.js recommended rules (core-web-vitals) via flat-config compat.
// v1 code is linted but lint is non-blocking in CI until it is remediated
// alongside the rewrites in later phases; see .github/workflows/ci.yml.
const config = [
  { ignores: [".next/**", "node_modules/**", "next-env.d.ts"] },
  ...compat.extends("next/core-web-vitals"),
];

export default config;
