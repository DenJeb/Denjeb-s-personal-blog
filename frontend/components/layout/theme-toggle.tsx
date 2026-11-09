"use client";

import { THEME_COOKIE, type Theme } from "@/lib/theme";

function currentTheme(): Theme {
  return document.documentElement.dataset.theme === "dark" ? "dark" : "light";
}

export function ThemeToggle() {
  function toggle() {
    const next: Theme = currentTheme() === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    // Drop the pre-v2 preference so older browsers fall back to dark once.
    document.cookie = "theme=; path=/; max-age=0; samesite=lax";
    document.cookie = `${THEME_COOKIE}=${next}; path=/; max-age=31536000; samesite=lax`;
  }

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label="切换主题"
      className="theme-toggle"
    >
      <span className="theme-icon-light" aria-hidden="true">
        ☾
      </span>
      <span className="theme-icon-dark" aria-hidden="true">
        ☀︎
      </span>
    </button>
  );
}
