import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: ["192.168.31.52", "192.168.31.25"],
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "lh3.googleusercontent.com" },
    ],
  },
  async rewrites() {
    // 使用 127.0.0.1 而非 localhost，避免 ALL_PROXY 将请求路由到 SOCKS 代理
    const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api/v1";
    return [
      {
        source: "/api/v1/:path*",
        destination: `${apiBase}/:path*`,
      },
    ];
  },
};

export default nextConfig;
