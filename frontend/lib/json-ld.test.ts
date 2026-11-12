import { describe, expect, it } from "vitest";

import { serializeJsonLd } from "./json-ld";

describe("serializeJsonLd", () => {
  it("escapes closing script tags", () => {
    const value = { headline: "</script><script>alert(1)</script>" };

    expect(serializeJsonLd(value)).not.toContain("</script>");
    expect(serializeJsonLd(value)).toContain("\\u003c/script>");
  });
});
