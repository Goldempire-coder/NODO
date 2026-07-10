export type PublicEnv = {
  NEXT_PUBLIC_API_BASE_URL: string;
  NEXT_PUBLIC_APP_URL: string;
  NEXT_PUBLIC_TELEGRAM_BOT_USERNAME: string;
  NEXT_PUBLIC_SUPABASE_URL: string;
  NEXT_PUBLIC_SUPABASE_ANON_KEY: string;
};

function readPublicValue(key: keyof PublicEnv): string {
  switch (key) {
    case "NEXT_PUBLIC_API_BASE_URL":
      return process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
    case "NEXT_PUBLIC_APP_URL":
      return process.env.NEXT_PUBLIC_APP_URL ?? "";
    case "NEXT_PUBLIC_TELEGRAM_BOT_USERNAME":
      return process.env.NEXT_PUBLIC_TELEGRAM_BOT_USERNAME ?? "";
    case "NEXT_PUBLIC_SUPABASE_URL":
      return process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
    case "NEXT_PUBLIC_SUPABASE_ANON_KEY":
      return process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "";
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
    NEXT_PUBLIC_SUPABASE_URL: readPublicValue("NEXT_PUBLIC_SUPABASE_URL"),
    NEXT_PUBLIC_SUPABASE_ANON_KEY: readPublicValue("NEXT_PUBLIC_SUPABASE_ANON_KEY")
  };
}

export function resolveApiUrl(path: string): string {
  const baseUrl = readPublicValue("NEXT_PUBLIC_API_BASE_URL").replace(/\/$/, "");
  return baseUrl ? `${baseUrl}${path}` : path;
}
