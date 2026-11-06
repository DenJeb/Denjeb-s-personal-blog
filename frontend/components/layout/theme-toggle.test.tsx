import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, beforeEach } from "vitest";

import { ThemeToggle } from "./theme-toggle";

describe("ThemeToggle", () => {
  beforeEach(() => {
    document.documentElement.dataset.theme = "light";
  });

  it("toggles data-theme", () => {
    render(<ThemeToggle />);
    fireEvent.click(screen.getByRole("button", { name: "切换主题" }));
    expect(document.documentElement.dataset.theme).toBe("dark");
  });
});
