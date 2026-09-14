/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  agentRules: false,
  turbopack: {
    root: process.cwd(),
  },
};

export default nextConfig;
