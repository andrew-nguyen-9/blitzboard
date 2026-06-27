import { describe, it, expect } from "vitest";
import { gateFor, GATE_PROMPT } from "./gate";

// The v2.6 HARD acceptance: the access matrix for the authenticated plane is correct for
// every state, and every gate is a prompt with a next step (never a dead end).
describe("gateFor — access matrix", () => {
  it("signed-out → login prompt", () => {
    expect(gateFor({ signedIn: false, hasLeague: false })).toBe("login");
    expect(gateFor({ signedIn: false, hasLeague: true })).toBe("login"); // session is the first gate
  });

  it("signed-in, no league → import prompt", () => {
    expect(gateFor({ signedIn: true, hasLeague: false })).toBe("import");
  });

  it("signed-in, with league → content (ok)", () => {
    expect(gateFor({ signedIn: true, hasLeague: true })).toBe("ok");
  });

  it("signed-in, league present but credentials expired → reconnect prompt", () => {
    expect(gateFor({ signedIn: true, hasLeague: true, credentialExpired: true })).toBe("reconnect");
  });

  it("expired credentials never override a missing session (login wins)", () => {
    expect(gateFor({ signedIn: false, hasLeague: true, credentialExpired: true })).toBe("login");
  });

  it("no league takes precedence over a stray expired credential (import, not reconnect)", () => {
    expect(gateFor({ signedIn: true, hasLeague: false, credentialExpired: true })).toBe("import");
  });
});

describe("gate prompts are helpful next steps, not walls", () => {
  it("every non-ok state has a title, body, CTA and a destination", () => {
    for (const state of ["login", "import", "reconnect"] as const) {
      const p = GATE_PROMPT[state];
      expect(p.title).toBeTruthy();
      expect(p.cta).toBeTruthy();
      expect(p.href).toMatch(/^\//); // a real route to go to
    }
  });
});
