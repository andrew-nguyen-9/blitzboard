import { fileURLToPath } from "url";
import path from "path";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Transport/surface hardening (v2.5.5). Supabase origin is allowlisted for auth+data XHR; the
// image CDNs match the images config below. Next injects inline runtime script/style, so
// script/style keep 'unsafe-inline' here — tightening to per-request nonces is a v2.7 item.
// frame-ancestors 'none' + X-Frame-Options block clickjacking; HSTS forces HTTPS (preload).
const supabaseOrigin = process.env.NEXT_PUBLIC_SUPABASE_URL || "";
const CSP = [
  "default-src 'self'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
  "object-src 'none'",
  "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: https://sleepercdn.com https://a.espncdn.com",
  "font-src 'self' data:",
  `connect-src 'self' ${supabaseOrigin}`.trim(),
].join("; ");

const SECURITY_HEADERS = [
  { key: "Content-Security-Policy", value: CSP },
  { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains; preload" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
];

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async headers() {
    return [{ source: "/:path*", headers: SECURITY_HEADERS }];
  },
  // Anchor file tracing to the repo root (parent of /frontend), not to any
  // lockfile-detected parent above it. Required when the repo is a subdirectory
  // of a larger workspace so Vercel bundles server-side dependencies correctly.
  outputFileTracingRoot: path.join(__dirname, "../"),
  images: {
    remotePatterns: [
      // Sleeper player headshots / team logos
      { protocol: "https", hostname: "sleepercdn.com" },
      // ESPN player + team art (league overview)
      { protocol: "https", hostname: "a.espncdn.com" },
    ],
  },
};

export default nextConfig;
