"use client";

import { useEffect, useRef, useState } from "react";
import Script from "next/script";

// Captcha resilience (mirrors portfolio-website/components/Contact): "loading" until we know
// whether hCaptcha loaded; "hcaptcha" when ready; "fallback" (honeypot + timing + math) when
// blocked or no site key. No motion is used, so reduced-motion needs no special handling.
type State = "idle" | "submitting" | "success" | "error";
type CaptchaMode = "loading" | "hcaptcha" | "fallback";
const HCAPTCHA_SITE_KEY = process.env.NEXT_PUBLIC_HCAPTCHA_SITE_KEY ?? "";

declare global {
  interface Window {
    hcaptcha?: unknown;
  }
}

const fieldClass =
  "rounded-md border border-line bg-surface-elevated px-3 py-2 text-body text-ink outline-none transition-colors focus:border-accent placeholder:text-ink-muted/50";
const labelClass = "text-label text-ink-muted";

export default function SignupForm() {
  const formRef = useRef<HTMLFormElement>(null);
  const [state, setState] = useState<State>("idle");
  const [errMsg, setErrMsg] = useState("");
  const [mounted, setMounted] = useState(false);

  const [captchaMode, setCaptchaMode] = useState<CaptchaMode>(
    HCAPTCHA_SITE_KEY ? "loading" : "fallback",
  );
  const [engaged, setEngaged] = useState(false);
  const [math, setMath] = useState({ a: 0, b: 0 });
  const [mathAnswer, setMathAnswer] = useState("");
  const startRef = useRef(0);

  useEffect(() => {
    setMounted(true);
    startRef.current = Date.now();
    setMath({ a: Math.floor(Math.random() * 9), b: Math.floor(Math.random() * 9) });
  }, []);

  // If hCaptcha hasn't initialized shortly after engagement, a blocker stopped it → fallback.
  useEffect(() => {
    if (!engaged || !HCAPTCHA_SITE_KEY) return;
    const timer = setTimeout(() => {
      setCaptchaMode((m) => (m === "loading" && !window.hcaptcha ? "fallback" : m));
    }, 2800);
    return () => clearTimeout(timer);
  }, [engaged]);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (state === "submitting") return;
    const form = formRef.current;
    if (!form) return;

    const fd = new FormData(form);
    const password = String(fd.get("password") ?? "");
    const confirm = String(fd.get("confirm") ?? "");
    if (password !== confirm) {
      setErrMsg("Passwords do not match.");
      return;
    }

    const base = {
      firstName: String(fd.get("firstName") ?? ""),
      lastName: String(fd.get("lastName") ?? ""),
      email: String(fd.get("email") ?? ""),
      phone: String(fd.get("phone") ?? ""),
      password,
      confirm,
    };

    let payload: Record<string, unknown>;
    if (captchaMode === "hcaptcha") {
      const hToken = (form.querySelector('[name="h-captcha-response"]') as HTMLInputElement | null)?.value;
      if (!hToken) {
        setErrMsg("Please complete the captcha.");
        return;
      }
      payload = { ...base, hCaptchaToken: hToken };
    } else {
      if (mathAnswer.trim() === "") {
        setErrMsg("Please answer the verification question.");
        return;
      }
      payload = {
        ...base,
        fallback: {
          honeypot: String(fd.get("company") ?? ""),
          answer: Number(mathAnswer),
          a: math.a,
          b: math.b,
          elapsedMs: Date.now() - startRef.current,
        },
      };
    }

    setState("submitting");
    setErrMsg("");
    try {
      const res = await fetch("/api/auth/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const json = (await res.json().catch(() => ({}))) as { error?: string };
        throw new Error(json.error ?? "Something went wrong.");
      }
      setState("success");
      window.location.assign("/login?check=email");
    } catch (err) {
      setState("error");
      setErrMsg(err instanceof Error ? err.message : "Something went wrong.");
    }
  }

  return (
    <form
      ref={formRef}
      onSubmit={handleSubmit}
      onFocus={() => setEngaged(true)}
      onPointerDown={() => setEngaged(true)}
      className="flex flex-col gap-4"
      noValidate
    >
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="flex flex-col gap-1.5">
          <label htmlFor="firstName" className={labelClass}>First name</label>
          <input id="firstName" name="firstName" type="text" autoComplete="given-name" required className={fieldClass} />
        </div>
        <div className="flex flex-col gap-1.5">
          <label htmlFor="lastName" className={labelClass}>Last name</label>
          <input id="lastName" name="lastName" type="text" autoComplete="family-name" required className={fieldClass} />
        </div>
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="email" className={labelClass}>Email</label>
        <input id="email" name="email" type="email" autoComplete="email" required className={fieldClass} />
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="phone" className={labelClass}>Phone</label>
        <input id="phone" name="phone" type="tel" autoComplete="tel" required className={fieldClass} />
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="flex flex-col gap-1.5">
          <label htmlFor="password" className={labelClass}>Password</label>
          <input id="password" name="password" type="password" autoComplete="new-password" minLength={8} required className={fieldClass} />
        </div>
        <div className="flex flex-col gap-1.5">
          <label htmlFor="confirm" className={labelClass}>Confirm password</label>
          <input id="confirm" name="confirm" type="password" autoComplete="new-password" minLength={8} required className={fieldClass} />
        </div>
      </div>

      {/* Honeypot — hidden from humans; bots that fill it are rejected server-side. */}
      <div aria-hidden="true" style={{ position: "absolute", left: "-9999px", width: 1, height: 1, overflow: "hidden" }}>
        <label htmlFor="company">Company (leave blank)</label>
        <input id="company" name="company" type="text" tabIndex={-1} autoComplete="off" />
      </div>

      {engaged && HCAPTCHA_SITE_KEY && (
        <Script
          src="https://js.hcaptcha.com/1/api.js"
          strategy="afterInteractive"
          onLoad={() => setCaptchaMode((m) => (m === "loading" ? "hcaptcha" : m))}
          onError={() => setCaptchaMode("fallback")}
        />
      )}

      {captchaMode === "hcaptcha" && (
        <div className="h-captcha" data-sitekey={HCAPTCHA_SITE_KEY} />
      )}

      {captchaMode === "fallback" && mounted && (
        <div className="flex flex-col gap-1.5">
          <label htmlFor="math" className={labelClass}>
            Verify you&apos;re human — what is {math.a} + {math.b}?
          </label>
          <input
            id="math"
            name="math"
            type="text"
            inputMode="numeric"
            autoComplete="off"
            required
            value={mathAnswer}
            onChange={(e) => setMathAnswer(e.target.value)}
            className={`${fieldClass} max-w-[160px]`}
          />
        </div>
      )}

      {errMsg && (
        <p role="alert" className="text-label text-neg">{errMsg}</p>
      )}

      <button
        type="submit"
        disabled={state === "submitting"}
        className="mt-1 inline-flex items-center justify-center rounded-full bg-accent px-5 py-2.5 text-label text-bg transition hover:opacity-90 disabled:opacity-50"
      >
        {state === "submitting" ? "Creating account…" : "Sign up"}
      </button>
    </form>
  );
}
