// Prod-exclusion gate for the Model Lab (docs/design/v4-engine-architecture.md:
// the Lab is engine-tier + LOCAL-ONLY — it triggers engine CLI jobs and inspects
// raw MCMC/calibration internals that must never ship in the public bundle).
//
// Mechanism: a single pure predicate consumed by BOTH the route layout (which
// calls notFound() when disabled → the page + API 404 in prod) and the job API
// route. It is off unless BOTH hold:
//   1. not a production build  (NODE_ENV !== "production")  — hard floor
//   2. opt-in flag set          (NEXT_PUBLIC_ENABLE_LAB === "1")
// So a prod build can never expose the Lab even if the flag leaks into the env,
// and a local build stays dark until you explicitly opt in.

type EnvLike = Record<string, string | undefined>;

export function labEnabled(env: EnvLike = process.env): boolean {
  if (env.NODE_ENV === "production") return false; // hard floor — prod excludes the Lab
  return env.NEXT_PUBLIC_ENABLE_LAB === "1";
}
