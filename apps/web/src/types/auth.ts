export type SessionState = "loading" | "error" | "expired" | "authenticated";

export type PublicUser = {
  id: string;
  username: string | null;
  first_name: string | null;
  last_name: string | null;
  phone?: string | null;
  role: string;
  status: string;
  terms_accepted_at?: string | null;
  terms_version?: string | null;
};

export type AuthResponse = {
  data?: {
    access_token: string;
    refresh_token: string;
    token_type: "Bearer";
    expires_in: number;
    user: PublicUser;
  };
  error?: {
    code: string;
    message: string;
  };
};
