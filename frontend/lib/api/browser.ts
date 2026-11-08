/**
 * Client-side JSON helpers for same-origin FastAPI writes.
 * They fetch a session-bound CSRF token before every write and send it in
 * the `X-CSRF-Token` header; the browser talks to FastAPI directly, so
 * FastAPI owns the Set-Cookie for the session.
 */

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function readJson(response: Response): Promise<Record<string, unknown>> {
  try {
    const data: unknown = await response.json();
    return typeof data === "object" && data !== null
      ? (data as Record<string, unknown>)
      : {};
  } catch {
    return {};
  }
}

export async function getCsrfToken(): Promise<string> {
  const response = await fetch("/api/v1/auth/csrf", {
    credentials: "same-origin",
    cache: "no-store",
  });
  const data = await readJson(response);

  if (!response.ok || typeof data.csrf_token !== "string") {
    throw new ApiError(response.status, "无法获取 CSRF token");
  }

  return data.csrf_token;
}

export async function postJson<T = Record<string, unknown>>(
  url: string,
  body: unknown,
): Promise<T> {
  const token = await getCsrfToken();
  const response = await fetch(url, {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": token,
    },
    body: JSON.stringify(body),
  });
  const data = await readJson(response);

  if (!response.ok) {
    const detail =
      typeof data.detail === "string" ? data.detail : "请求失败，请稍后重试。";
    throw new ApiError(response.status, detail);
  }

  return data as T;
}
