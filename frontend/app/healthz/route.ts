import { env } from "@/lib/env";

export const dynamic = "force-dynamic";

export async function GET() {
  const apiBase = env.API_BASE_URL.replace(/\/$/, "");

  try {
    const response = await fetch(`${apiBase}/healthz`, {
      cache: "no-store",
      signal: AbortSignal.timeout(3000),
    });
    if (!response.ok) {
      return Response.json(
        { status: "error", api: "unhealthy" },
        { status: 503 },
      );
    }
    return Response.json({ status: "ok" });
  } catch {
    return Response.json(
      { status: "error", api: "unreachable" },
      { status: 503 },
    );
  }
}
