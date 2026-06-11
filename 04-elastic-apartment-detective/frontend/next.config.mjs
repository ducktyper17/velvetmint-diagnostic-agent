/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  // NOTE: deliberately no `env: { BACKEND_URL }` block. Next's `env` config
  // inlines values at BUILD time, which would freeze BACKEND_URL to whatever it
  // was when the image was built and ignore the runtime value Cloud Run injects.
  // The proxy route reads process.env.BACKEND_URL at request time instead, so
  // the same image works locally and in prod.
};

export default nextConfig;
