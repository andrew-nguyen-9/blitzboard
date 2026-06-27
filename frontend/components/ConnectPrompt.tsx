import Link from "next/link";
import { GATE_PROMPT, type GateState } from "@/lib/auth/gate";

// The friendly gate for the authenticated league plane (v2.6.1). Renders the right next-step
// for a non-"ok" gate state — login / import / reconnect — never a dead end. Server component
// (no interactivity); inherits theme tokens so it works in light/dark and reduced-motion.
export default function ConnectPrompt({ state }: { state: Exclude<GateState, "ok"> }) {
  const p = GATE_PROMPT[state];
  return (
    <div className="mx-auto max-w-lg">
      <div className="glass p-8 text-center">
        <h2 className="font-display text-heading">{p.title}</h2>
        <p className="mx-auto mt-3 max-w-md text-body text-ink-muted">{p.body}</p>
        <Link
          href={p.href}
          className="mt-6 inline-flex items-center rounded-full bg-accent px-5 py-2.5 text-label text-bg transition hover:opacity-90"
        >
          {p.cta}
        </Link>
        {state !== "login" && (
          <p className="mt-4 text-label text-ink-muted/70">
            Just exploring?{" "}
            <Link href="/waivers" className="underline transition hover:text-accent">
              Try the public tools
            </Link>{" "}
            — no league needed.
          </p>
        )}
      </div>
    </div>
  );
}
