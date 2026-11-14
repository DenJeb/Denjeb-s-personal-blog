import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, postForm, sendJson } from "./browser";

function jsonResponse(body: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  };
}

describe("browser API helpers", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("fetches a CSRF token before sending JSON", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ csrf_token: "token-1" }))
      .mockResolvedValueOnce(jsonResponse({ ok: true }));
    vi.stubGlobal("fetch", fetchMock);

    const result = await sendJson<{ ok: boolean }>("POST", "/api/v1/test", {
      value: 1,
    });

    expect(result).toEqual({ ok: true });
    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/v1/auth/csrf",
      expect.objectContaining({ credentials: "same-origin", cache: "no-store" }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/v1/test",
      expect.objectContaining({
        method: "POST",
        credentials: "same-origin",
        headers: expect.objectContaining({
          "Content-Type": "application/json",
          "X-CSRF-Token": "token-1",
        }),
        body: JSON.stringify({ value: 1 }),
      }),
    );
  });

  it("returns an empty object for a 204 response", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ csrf_token: "token-1" }))
      .mockResolvedValueOnce({
        ok: true,
        status: 204,
        json: async () => {
          throw new Error("no body");
        },
      });
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      sendJson("DELETE", "/api/v1/test/1"),
    ).resolves.toEqual({});
  });

  it("throws ApiError with the response detail", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ csrf_token: "token-1" }))
      .mockResolvedValueOnce(
        jsonResponse({ detail: "请先登录后台" }, 401),
      );
    vi.stubGlobal("fetch", fetchMock);

    const error = await sendJson("POST", "/api/v1/test").catch(
      (caught) => caught,
    );
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      status: 401,
      message: "请先登录后台",
    });
  });

  it("uses the first validation message from an array detail", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ csrf_token: "token-1" }))
      .mockResolvedValueOnce(
        jsonResponse(
          { detail: [{ msg: "字段不能为空", type: "value_error" }] },
          422,
        ),
      );
    vi.stubGlobal("fetch", fetchMock);

    const error = await sendJson("POST", "/api/v1/test", {}).catch(
      (caught) => caught,
    );
    expect(error).toBeInstanceOf(ApiError);
    expect(error.message).toBe("字段不能为空");
  });

  it("sends multipart form data without a JSON content type", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ csrf_token: "token-1" }))
      .mockResolvedValueOnce(jsonResponse({ url: "/static/uploads/x.webp" }));
    vi.stubGlobal("fetch", fetchMock);

    const form = new FormData();
    form.append("image_alt", "Cover");
    const result = await postForm<{ url: string }>(
      "/api/v1/admin/uploads/inline",
      form,
    );

    expect(result.url).toBe("/static/uploads/x.webp");
    const options = fetchMock.mock.calls[1][1] as RequestInit;
    expect(options.method).toBe("POST");
    expect(options.body).toBe(form);
    expect(options.headers).toEqual({ "X-CSRF-Token": "token-1" });
  });
});
