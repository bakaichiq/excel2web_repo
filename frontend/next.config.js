/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  reactStrictMode: true,

  async rewrites() {
    return [
      // твой API-прокси (как было)
      { source: "/api/:path*", destination: "http://backend:8000/:path*" },

      // важно для Swagger: он запрашивает /openapi.json (без /api)
      { source: "/openapi.json", destination: "http://backend:8000/openapi.json" },

      // важно для Swagger assets и redirect
      { source: "/docs", destination: "http://backend:8000/docs" },
      { source: "/docs/:path*", destination: "http://backend:8000/docs/:path*" },

      // (опционально) если используешь Redoc
      { source: "/redoc", destination: "http://backend:8000/redoc" },
      { source: "/redoc/:path*", destination: "http://backend:8000/redoc/:path*" },
    ];
  },
};

module.exports = nextConfig;
