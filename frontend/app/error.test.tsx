import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import ErrorPage from "./error";

describe("ErrorPage", () => {
  it("shows a friendly message without the raw error", () => {
    render(<ErrorPage error={new Error("secret detail")} reset={() => {}} />);
    expect(screen.getByText("页面暂时无法加载")).toBeInTheDocument();
    expect(screen.queryByText("secret detail")).not.toBeInTheDocument();
  });
});
