/** @type {import('next').NextConfig} */
const API_URL =
  process.env.API_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "http://127.0.0.1:8000";

const nextConfig = {
  async rewrites() {
    return [
      // Proxy Next.js /api/* -> FastAPI
      {
        source: "/api/:path*",
        destination: `${API_URL}/api/:path*`,
      },
      // Proxy /auth/* -> FastAPI
      {
        source: "/auth/:path*",
        destination: `${API_URL}/auth/:path*`,
      },
      // Proxy /v1/* -> FastAPI
      {
        source: "/v1/:path*",
        destination: `${API_URL}/v1/:path*`,
      },
      // Proxy /2fa/* -> FastAPI
      {
        source: "/2fa/:path*",
        destination: `${API_URL}/2fa/:path*`,
      },
    ];
  },
};

export default nextConfig;
