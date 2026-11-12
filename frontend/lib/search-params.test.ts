import { describe, expect, it } from "vitest";

import { firstParam } from "./search-params";

describe("firstParam", () => {
  it("returns the first value for repeated params", () => {
    expect(firstParam(["hello", "world"])).toBe("hello");
    expect(firstParam("hello")).toBe("hello");
    expect(firstParam(undefined)).toBeUndefined();
  });
});
