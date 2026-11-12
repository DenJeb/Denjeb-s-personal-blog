import { describe, expect, it } from "vitest";

import { formatDateTime } from "./date";

describe("formatDateTime", () => {
  it("formats site-local ISO strings", () => {
    expect(formatDateTime("2026-11-12T09:05:00")).toBe("2026-11-12 09:05");
    expect(formatDateTime("2026-11-12T09:05:00+08:00")).toBe(
      "2026-11-12 09:05",
    );
    expect(formatDateTime("2026-11-12")).toBe("2026-11-12");
  });
});
