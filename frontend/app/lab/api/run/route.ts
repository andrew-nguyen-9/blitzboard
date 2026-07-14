import { spawn } from "node:child_process";
import { NextResponse } from "next/server";
import { labEnabled } from "../../lab-flags";
import { buildEngineInvocation, isJob, parseEngineResult } from "../../engine";

// Local-only job trigger: POSTs a job verb, spawns the engine CLI, returns the log
// + any structured diagnostics receipt. Guarded by labEnabled() so it 404s in a
// prod build (the whole Lab is excluded there). Node runtime (child_process) and
// always dynamic (never cached / never statically evaluated at build).
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const TIMEOUT_MS = 5 * 60_000;

export async function POST(req: Request): Promise<Response> {
  if (!labEnabled()) return NextResponse.json({ error: "not found" }, { status: 404 });

  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "invalid JSON body" }, { status: 400 });
  }
  const job = (body as { job?: unknown })?.job;
  if (!isJob(job)) {
    return NextResponse.json({ error: `unknown job: ${String(job)}` }, { status: 400 });
  }

  const { cmd, args, cwd } = buildEngineInvocation(job);

  try {
    const { code, stdout, stderr } = await runProcess(cmd, args, cwd);
    const receipt = parseEngineResult(stdout);
    return NextResponse.json({
      ok: code === 0,
      job,
      code,
      log: [stdout, stderr].filter(Boolean).join("\n"),
      diagnostics: receipt && typeof receipt === "object" ? receipt : null,
    });
  } catch (e) {
    return NextResponse.json(
      { ok: false, job, error: e instanceof Error ? e.message : "spawn failed" },
      { status: 500 },
    );
  }
}

function runProcess(
  cmd: string,
  args: string[],
  cwd: string,
): Promise<{ code: number | null; stdout: string; stderr: string }> {
  return new Promise((resolve, reject) => {
    const child = spawn(cmd, args, { cwd });
    let stdout = "";
    let stderr = "";
    const timer = setTimeout(() => {
      child.kill("SIGKILL");
      reject(new Error(`engine job timed out after ${TIMEOUT_MS / 1000}s`));
    }, TIMEOUT_MS);
    child.stdout.on("data", (d) => (stdout += d.toString()));
    child.stderr.on("data", (d) => (stderr += d.toString()));
    child.on("error", (err) => {
      clearTimeout(timer);
      reject(err);
    });
    child.on("close", (code) => {
      clearTimeout(timer);
      resolve({ code, stdout, stderr });
    });
  });
}
