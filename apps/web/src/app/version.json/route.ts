import { publicBuildIdentity } from "../../lib/buildIdentity";

export const dynamic = "force-static";

export function GET() {
  return Response.json(publicBuildIdentity, {
    headers: {
      "Cache-Control": "no-store"
    }
  });
}
