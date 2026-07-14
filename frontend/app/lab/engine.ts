// Pure wiring for triggering engine CLI jobs from the Lab (E0-scaffold.done.md:
// `blitz-engine fit|sim|draft|publish`, editable-installed into pipeline/.venv).
// Kept side-effect-free + unit-tested; the API route (engine spawn) is the only
// place that actually touches child_process, so validation/argv/parse logic is
// verifiable without a Python runtime.

export const JOBS = ["fit", "sim", "draft", "publish"] as const;
export type Job = (typeof JOBS)[number];

export function isJob(x: unknown): x is Job {
  return typeof x === "string" && (JOBS as readonly string[]).includes(x);
}

export interface EngineInvocation {
  cmd: string; // python interpreter
  args: string[]; // ["-m", "blitz_engine.cli", <job>, ...extra]
  cwd: string; // engine package dir
}

// Resolve the invocation for a job. Interpreter + repo root are overridable via
// env so a workstation can point at its own venv without code changes:
//   BLITZ_ENGINE_PYTHON  → interpreter (default: pipeline/.venv/bin/python)
//   BLITZ_REPO_ROOT      → repo root   (default: cwd's parent, i.e. above /frontend)
export function buildEngineInvocation(
  job: Job,
  opts: { repoRoot?: string; python?: string; extraArgs?: string[]; env?: Record<string, string | undefined> } = {},
): EngineInvocation {
  const env = opts.env ?? process.env;
  const repoRoot = opts.repoRoot ?? env.BLITZ_REPO_ROOT ?? joinPath(cwd(env), "..");
  const python = opts.python ?? env.BLITZ_ENGINE_PYTHON ?? joinPath(repoRoot, "pipeline/.venv/bin/python");
  return {
    cmd: python,
    args: ["-m", "blitz_engine.cli", job, ...(opts.extraArgs ?? [])],
    cwd: joinPath(repoRoot, "engine"),
  };
}

// A CLI job may emit a trailing JSON object (diagnostics / publish receipt). Parse
// the last balanced JSON object from stdout, tolerating log lines before it; null
// when there's nothing structured to render (caller shows the raw log instead).
export function parseEngineResult(stdout: string): Record<string, unknown> | null {
  const start = stdout.lastIndexOf("{");
  const end = stdout.lastIndexOf("}");
  if (start === -1 || end === -1 || end < start) return null;
  try {
    const parsed = JSON.parse(stdout.slice(start, end + 1));
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

// Tiny path helpers so this stays a pure module (no node:path import → runnable in
// the node vitest env and importable from the edge-agnostic route alike).
function cwd(env: Record<string, string | undefined>): string {
  return env.BLITZ_REPO_ROOT ? env.BLITZ_REPO_ROOT : typeof process !== "undefined" ? process.cwd() : ".";
}
function joinPath(a: string, b: string): string {
  if (b === "..") {
    const trimmed = a.replace(/\/+$/, "");
    return trimmed.slice(0, trimmed.lastIndexOf("/")) || "/";
  }
  return `${a.replace(/\/+$/, "")}/${b.replace(/^\/+/, "")}`;
}
