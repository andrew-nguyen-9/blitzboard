// Access gating for the authenticated league plane (v2.6.1). Pure decision function so the
// access matrix — signed-out / signed-in-no-league / signed-in-with-(maybe-expired)-league —
// is provable by unit test, independent of the DB. Every non-"ok" state is a helpful prompt
// with a clear next step (login / import / reconnect), never a dead-end wall.
export type GateState = "ok" | "login" | "import" | "reconnect";

export interface GateInput {
  signedIn: boolean;
  hasLeague: boolean;
  credentialExpired?: boolean; // a connected ESPN/Sleeper credential that needs re-auth
}

export function gateFor(input: GateInput): GateState {
  if (!input.signedIn) return "login";
  if (!input.hasLeague) return "import"; // no league yet → import (even if a stray cred exists)
  if (input.credentialExpired) return "reconnect"; // has a league but its creds rotated out
  return "ok";
}

// Copy for each prompt state — the next step a user can actually take.
export const GATE_PROMPT: Record<Exclude<GateState, "ok">, { title: string; body: string; cta: string; href: string }> = {
  login: {
    title: "Sign in to open your league",
    body: "Your league's Overview, Waivers, and Trades are tailored to your imported rules. Sign in to get started.",
    cta: "Sign in",
    href: "/login",
  },
  import: {
    title: "Connect your league",
    body: "Import your Sleeper or ESPN league once and we'll tailor value, FAAB bids, and trades to your exact rules.",
    cta: "Import a league",
    href: "/league?import=1",
  },
  reconnect: {
    title: "Reconnect your league",
    body: "Your ESPN/Sleeper credentials expired (they rotate). Reconnect to refresh standings, rosters, and recommendations.",
    cta: "Reconnect",
    href: "/league?reconnect=1",
  },
};
