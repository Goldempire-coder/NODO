export type PublicEnv = {
  NEXT_PUBLIC_API_BASE_URL: string;
  NEXT_PUBLIC_APP_URL: string;
  NEXT_PUBLIC_TELEGRAM_BOT_USERNAME: string;
  NEXT_PUBLIC_APP_ENV: string;
  NEXT_PUBLIC_OBSERVABILITY_INGEST_ENABLED: string;
};

function readPublicValue(key: keyof PublicEnv): string {
  switch (key) {
    case "NEXT_PUBLIC_API_BASE_URL":
      return process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
    case "NEXT_PUBLIC_APP_URL":
      return process.env.NEXT_PUBLIC_APP_URL ?? "";
    case "NEXT_PUBLIC_TELEGRAM_BOT_USERNAME":
      return process.env.NEXT_PUBLIC_TELEGRAM_BOT_USERNAME ?? "";
    case "NEXT_PUBLIC_APP_ENV":
      return process.env.NEXT_PUBLIC_APP_ENV ?? "";
    case "NEXT_PUBLIC_OBSERVABILITY_INGEST_ENABLED":
      return process.env.NEXT_PUBLIC_OBSERVABILITY_INGEST_ENABLED ?? "";
    default:
      return "";
  }
}

export function getPublicEnv(): PublicEnv {
  const appUrl = readPublicValue("NEXT_PUBLIC_APP_URL") || "http://localhost:3000";

  return {
    NEXT_PUBLIC_API_BASE_URL: readPublicValue("NEXT_PUBLIC_API_BASE_URL"),
    NEXT_PUBLIC_APP_URL: appUrl,
    NEXT_PUBLIC_TELEGRAM_BOT_USERNAME: readPublicValue("NEXT_PUBLIC_TELEGRAM_BOT_USERNAME"),
    NEXT_PUBLIC_APP_ENV: readPublicValue("NEXT_PUBLIC_APP_ENV"),
    NEXT_PUBLIC_OBSERVABILITY_INGEST_ENABLED: readPublicValue("NEXT_PUBLIC_OBSERVABILITY_INGEST_ENABLED")
  };
}

export function resolveApiUrl(path: string): string {
  const baseUrl = readPublicValue("NEXT_PUBLIC_API_BASE_URL").replace(/\/$/, "");
  return baseUrl ? `${baseUrl}${path}` : path;
}
