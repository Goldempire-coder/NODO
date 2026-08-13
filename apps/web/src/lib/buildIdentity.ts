const COMMIT_SHA_PATTERN = /^[0-9a-f]{40,64}$/i;
const ENVIRONMENT_PATTERN = /^[a-z][a-z0-9_-]{0,31}$/;
const UNKNOWN = "unknown";

type BuildIdentitySource =
  | "cloudflare_pages"
  | "release_env"
  | "release_env+cloudflare_pages"
  | "conflict"
  | "unknown";

export type PublicBuildIdentity = {
  service: "nodo-web";
  environment: string;
  commit_sha: string;
  build_id: string;
  source: BuildIdentitySource;
};

type BuildEnvironment = Readonly<Record<string, string | undefined>>;

function normalizedCommitSha(value: string | undefined): string | null {
  const candidate = value?.trim().toLowerCase() ?? "";
  return COMMIT_SHA_PATTERN.test(candidate) ? candidate : null;
}

function normalizedEnvironment(value: string | undefined): string {
  const candidate = value?.trim().toLowerCase() ?? "";
  return ENVIRONMENT_PATTERN.test(candidate) ? candidate : UNKNOWN;
}

function resolveCommit(env: BuildEnvironment): { commitSha: string; source: BuildIdentitySource } {
  const releaseCommit = normalizedCommitSha(env.NODO_RELEASE_COMMIT_SHA);
  const cloudflareCommit = normalizedCommitSha(env.CF_PAGES_COMMIT_SHA);

  if (releaseCommit && cloudflareCommit && releaseCommit !== cloudflareCommit) {
    return { commitSha: UNKNOWN, source: "conflict" };
  }
  if (releaseCommit && cloudflareCommit) {
    return { commitSha: releaseCommit, source: "release_env+cloudflare_pages" };
  }
  if (cloudflareCommit) {
    return { commitSha: cloudflareCommit, source: "cloudflare_pages" };
  }
  if (releaseCommit) {
    return { commitSha: releaseCommit, source: "release_env" };
  }
  return { commitSha: UNKNOWN, source: "unknown" };
}

export function createPublicBuildIdentity(env: BuildEnvironment = process.env): PublicBuildIdentity {
  const environment = normalizedEnvironment(env.NEXT_PUBLIC_APP_ENV);
  const { commitSha, source } = resolveCommit(env);
  const buildId =
    environment === UNKNOWN || commitSha === UNKNOWN
      ? UNKNOWN
      : `${environment}-${commitSha.slice(0, 7)}`;

  return {
    service: "nodo-web",
    environment,
    commit_sha: commitSha,
    build_id: buildId,
    source
  };
}

export const publicBuildIdentity = createPublicBuildIdentity();
