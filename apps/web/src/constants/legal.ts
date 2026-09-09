export const CURRENT_CLIENT_TERMS_VERSION = "2026-09-09";

export function hasAcceptedCurrentClientTerms(user: { terms_accepted_at?: string | null; terms_version?: string | null }) {
  return Boolean(user.terms_accepted_at && user.terms_version === CURRENT_CLIENT_TERMS_VERSION);
}
