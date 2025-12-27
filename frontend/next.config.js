/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  reactStrictMode: true,

  async rewrites() {
    const backend = process.env.BACKEND_URL || "http://localhost:8000";
    return [
      // твой API-прокси (как было)
      { source: "/api/:path*", destination: `${backend}/:path*` },

      // важно для Swagger: он запрашивает /openapi.json (без /api)
      { source: "/openapi.json", destination: `${backend}/openapi.json` },

      // важно для Swagger assets и redirect
      { source: "/docs", destination: `${backend}/docs` },
      { source: "/docs/:path*", destination: `${backend}/docs/:path*` },

      // (опционально) если используешь Redoc
      { source: "/redoc", destination: `${backend}/redoc` },
      { source: "/redoc/:path*", destination: `${backend}/redoc/:path*` },
    ];
  },
};

module.exports = nextConfig;
