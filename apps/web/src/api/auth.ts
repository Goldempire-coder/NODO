import type { AuthResponse } from "../types/auth";
import { resolveApiUrl } from "../lib/env";

export async function authenticateWithTelegram(initData: string): Promise<AuthResponse> {
  const response = await fetch(resolveApiUrl("/api/v1/auth/telegram"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Request-Id": `web_${Date.now()}`
    },
    body: JSON.stringify({ init_data: initData })
  });
  return (await response.json()) as AuthResponse;
}
