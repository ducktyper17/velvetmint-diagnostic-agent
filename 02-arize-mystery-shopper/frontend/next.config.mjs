/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  env: {
    BACKEND_URL: process.env.BACKEND_URL || "http://localhost:8080",
  },
  async rewrites() {
    // Backend URL baked at build time. process.env.BACKEND_URL is unset during
    // `next build` (Cloud Run --source builds don't get build args), so we
    // hardcode the deployed backend Cloud Run URL here. If the backend URL
    // ever changes, update this value and rebuild.
    const backend =
      process.env.BACKEND_URL && process.env.BACKEND_URL !== "http://localhost:8080"
        ? process.env.BACKEND_URL
        : "https://self-improving-qa-backend-mwxstjbztq-uc.a.run.app";
    return [
      {
        source: "/api/proxy/:path*",
        destination: `${backend}/:path*`,
      },
    ];
  },
};

export default nextConfig;
