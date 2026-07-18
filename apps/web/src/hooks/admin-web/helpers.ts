import { createIdempotencyKey } from "../useStableIdempotencyKeys";

export function idempotencyKey(prefix: string) {
  return createIdempotencyKey(prefix);
}
