"use client";

type Theme = "light" | "dark";

function currentTheme(): Theme {
  return document.documentElement.dataset.theme === "dark" ? "dark" : "light";
}

export function ThemeToggle() {
  function toggle() {
    const next: Theme = currentTheme() === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    document.cookie = `theme=${next}; path=/; max-age=31536000; samesite=lax`;
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
