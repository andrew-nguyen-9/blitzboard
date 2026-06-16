import { fileURLToPath } from "url";
import path from "path";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
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
