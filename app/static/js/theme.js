(() => {
  const root = document.documentElement;
  const button = document.getElementById("theme-toggle");
  if (!button) {
    return;
  }

  const isDark = () => {
    const current = root.getAttribute("data-theme");
    if (current === "dark") {
      return true;
    }
    if (current === "light") {
      return false;
    }
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
  };

  const updateButton = () => {
    button.textContent = isDark() ? "☀️" : "🌙";
  };

  button.addEventListener("click", () => {
    const next = isDark() ? "light" : "dark";
    root.setAttribute("data-theme", next);
    document.cookie = `theme-v2=${next}; path=/; max-age=31536000; samesite=lax`;
    document.cookie = "theme=; path=/; max-age=0; samesite=lax";
    try {
      localStorage.setItem("theme", next);
    } catch (error) {
      // 忽略隐私模式下的存储错误
    }
    updateButton();
  });

  updateButton();
})();
