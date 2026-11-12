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

async function csrfFetch(
  method: string,
  url: string,
  init: Omit<RequestInit, "method"> = {},
): Promise<Response> {
  const token = await getCsrfToken();
  return fetch(url, {
    ...init,
    method,
    credentials: "same-origin",
    cache: "no-store",
    headers: {
      ...(init.headers as Record<string, string> | undefined),
      "X-CSRF-Token": token,
    },
  });
}

function errorFrom(response: Response, data: Record<string, unknown>): ApiError {
  const detail =
    typeof data.detail === "string" ? data.detail : "请求失败，请稍后重试。";
  return new ApiError(response.status, detail);
}

export async function sendJson<T = Record<string, unknown>>(
  method: "POST" | "PUT" | "DELETE",
  url: string,
  body?: unknown,
): Promise<T> {
  const headers: Record<string, string> = {};
  const init: RequestInit = {};
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(body);
  }

  const response = await csrfFetch(method, url, { ...init, headers });
  const data = await readJson(response);

  if (!response.ok) {
    throw errorFrom(response, data);
  }

  return data as T;
}

export async function postForm<T = Record<string, unknown>>(
  url: string,
  formData: FormData,
): Promise<T> {
  // Do not set Content-Type: the browser must add the multipart boundary.
  const response = await csrfFetch("POST", url, { body: formData });
  const data = await readJson(response);

  if (!response.ok) {
    throw errorFrom(response, data);
  }

  return data as T;
}

export async function postJson<T = Record<string, unknown>>(
  url: string,
  body: unknown,
): Promise<T> {
  return sendJson<T>("POST", url, body);
}
