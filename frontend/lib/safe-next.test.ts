import { describe, expect, it } from "vitest";

import { safeNext } from "./safe-next";

describe("safeNext", () => {
  it("keeps same-origin paths", () => {
    expect(safeNext("/posts")).toBe("/posts");
    expect(safeNext("/posts?page=2#comments")).toBe("/posts?page=2#comments");
  });

  it("rejects external and backslash redirects", () => {
    expect(safeNext("https://evil.com")).toBe("/");
    expect(safeNext("//evil.com")).toBe("/");
    expect(safeNext("/\\evil.com")).toBe("/");
    expect(safeNext("/posts\n")).toBe("/");
    expect(safeNext(undefined)).toBe("/");
  });
});
