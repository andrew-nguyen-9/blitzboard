/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
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
