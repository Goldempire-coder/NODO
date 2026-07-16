/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export",
  env: {
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL ?? "",
    NEXT_PUBLIC_APP_URL: process.env.NEXT_PUBLIC_APP_URL ?? "",
    NEXT_PUBLIC_TELEGRAM_BOT_USERNAME: process.env.NEXT_PUBLIC_TELEGRAM_BOT_USERNAME ?? "",
    NEXT_PUBLIC_APP_ENV: process.env.NEXT_PUBLIC_APP_ENV ?? "",
    NEXT_PUBLIC_OBSERVABILITY_INGEST_ENABLED: process.env.NEXT_PUBLIC_OBSERVABILITY_INGEST_ENABLED ?? ""
  },
  trailingSlash: true,
  images: {
    unoptimized: true
  },
  poweredByHeader: false,
  reactStrictMode: true
};

export default nextConfig;
