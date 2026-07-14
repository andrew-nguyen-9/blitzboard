import { describe, it, expect } from "vitest";
import { isJob, buildEngineInvocation, parseEngineResult } from "./engine";

describe("engine job validation", () => {
  it("accepts the four engine CLI verbs, rejects anything else", () => {
    for (const j of ["fit", "sim", "draft", "publish"]) expect(isJob(j)).toBe(true);
    for (const bad of ["deploy", "rm -rf", "", 3, null, undefined]) expect(isJob(bad)).toBe(false);
  });
});

describe("buildEngineInvocation", () => {
  it("targets the shared pipeline venv + engine cwd off the repo root", () => {
    const inv = buildEngineInvocation("fit", { repoRoot: "/repo", env: {} });
    expect(inv.cmd).toBe("/repo/pipeline/.venv/bin/python");
    expect(inv.args).toEqual(["-m", "blitz_engine.cli", "fit"]);
    expect(inv.cwd).toBe("/repo/engine");
  });

  it("honors env overrides + threads extra args after the job verb", () => {
    const inv = buildEngineInvocation("publish", {
      env: { BLITZ_REPO_ROOT: "/w", BLITZ_ENGINE_PYTHON: "/usr/bin/python3" },
      extraArgs: ["--version", "abc123"],
    });
    expect(inv.cmd).toBe("/usr/bin/python3");
    expect(inv.cwd).toBe("/w/engine");
    expect(inv.args).toEqual(["-m", "blitz_engine.cli", "publish", "--version", "abc123"]);
  });
});

describe("parseEngineResult", () => {
  it("extracts a trailing JSON receipt after log noise", () => {
    const out = "loading store...\nfit complete\n{\"version\":\"abc\",\"rhat_max\":1.01}\n";
    expect(parseEngineResult(out)).toEqual({ version: "abc", rhat_max: 1.01 });
  });

  it("returns null when stdout carries no JSON object", () => {
    expect(parseEngineResult("done, nothing structured")).toBeNull();
    expect(parseEngineResult("")).toBeNull();
  });
});
