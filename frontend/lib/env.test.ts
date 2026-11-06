import { describe, expect, it } from "vitest";

import { parseEnv } from "./env";

describe("parseEnv", () => {
  it("parses required values", () => {
    expect(
      parseEnv({
        API_BASE_URL: "http://127.0.0.1:8000",
        NEXT_PUBLIC_SITE_URL: "http://localhost:3000",
      }),
    ).toEqual({
      API_BASE_URL: "http://127.0.0.1:8000",
      NEXT_PUBLIC_SITE_URL: "http://localhost:3000",
    });
  });

  it("throws when API_BASE_URL is missing", () => {
    expect(() =>
      parseEnv({ NEXT_PUBLIC_SITE_URL: "http://localhost:3000" }),
    ).toThrow();
  });
});
