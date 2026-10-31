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
    try {
      localStorage.setItem("theme", next);
    } catch (error) {
      // 忽略隐私模式下的存储错误
    }
    updateButton();
  });

  updateButton();
})();
