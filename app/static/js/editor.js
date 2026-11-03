(() => {
  const root = document.querySelector("[data-markdown-editor]");
  if (!root) return;

  const textarea = root.querySelector("[data-editor-input]");
  const preview = root.querySelector("[data-editor-preview]");
  const status = root.querySelector("[data-editor-status]");
  const imageInput = root.querySelector("[data-editor-image-input]");
  const form = root.closest("form");
  const csrf = form ? form.querySelector('input[name="csrf_token"]') : null;

  if (!textarea || !preview || !status || !imageInput || !csrf) return;

  const previewUrl = root.dataset.previewUrl;
  const uploadUrl = root.dataset.uploadUrl;
  const previewButton = root.querySelector('[data-action="preview"]');
  if (!previewButton) return;

  function setStatus(message, isError = false) {
    status.textContent = message;
    status.classList.toggle("is-error", isError);
  }

  function insertText(before, after = "", placeholder = "") {
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selected = textarea.value.slice(start, end) || placeholder;
    textarea.setRangeText(before + selected + after, start, end, "end");
    textarea.focus();

    if (start === end) {
      const cursor = start + before.length + selected.length;
      textarea.setSelectionRange(cursor, cursor);
    }
  }

  function prefixSelectedLines(prefix) {
    const value = textarea.value;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const lineStart = value.lastIndexOf("\n", start - 1) + 1;
    const nextBreak = value.indexOf("\n", end);
    const lineEnd = nextBreak === -1 ? value.length : nextBreak;
    const lines = value
      .slice(lineStart, lineEnd)
      .split("\n")
      .map((line) => prefix + line);
    textarea.setRangeText(lines.join("\n"), lineStart, lineEnd, "end");
    textarea.focus();
  }

  async function togglePreview() {
    if (!preview.hidden) {
      preview.hidden = true;
      textarea.hidden = false;
      previewButton.textContent = "预览";
      previewButton.classList.remove("is-active");
      textarea.focus();
      return;
    }

    const body = new FormData();
    body.append("csrf_token", csrf.value);
    body.append("content", textarea.value);
    setStatus("正在生成预览…");

    try {
      const response = await fetch(previewUrl, { method: "POST", body });
      if (response.redirected) {
        throw new Error("登录已过期，请重新登录。");
      }
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail || "预览失败，请稍后重试。");
      }
      preview.innerHTML = await response.text();
      preview.hidden = false;
      textarea.hidden = true;
      previewButton.textContent = "编辑";
      previewButton.classList.add("is-active");
      setStatus("");
    } catch (error) {
      setStatus(error.message, true);
    }
  }

  async function uploadImage(file) {
    if (!file) return;

    const body = new FormData();
    body.append("csrf_token", csrf.value);
    body.append("image", file);
    body.append("image_alt", "");
    setStatus("正在上传图片…");

    try {
      const response = await fetch(uploadUrl, { method: "POST", body });
      if (response.redirected) {
        throw new Error("登录已过期，请重新登录。");
      }
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload.detail || "上传失败，请稍后重试。");
      }
      insertText(payload.markdown, "", "");
      setStatus("图片已插入正文。");
    } catch (error) {
      setStatus(error.message, true);
    }
  }

  const actions = {
    bold: () => insertText("**", "**", "粗体"),
    italic: () => insertText("*", "*", "斜体"),
    heading: () => insertText("## ", "", "标题"),
    link: () => {
      const url = window.prompt("链接地址", "https://");
      if (url) insertText("[", `](${url})`, "链接文字");
    },
    code: () => insertText("`", "`", "代码"),
    quote: () => prefixSelectedLines("> "),
    ul: () => prefixSelectedLines("- "),
    image: () => imageInput.click(),
    preview: togglePreview,
  };

  root.querySelectorAll("[data-action]").forEach((button) => {
    button.addEventListener("click", () => {
      const action = actions[button.dataset.action];
      if (action) action();
    });
  });

  textarea.addEventListener("keydown", (event) => {
    if (event.key === "Tab") {
      event.preventDefault();
      if (event.shiftKey) {
        const start = textarea.selectionStart;
        const lineStart = textarea.value.lastIndexOf("\n", start - 1) + 1;
        const beforeCursor = textarea.value.slice(lineStart, start);
        const remove = beforeCursor.endsWith("  ")
          ? 2
          : beforeCursor.endsWith(" ")
            ? 1
            : 0;
        if (remove) {
          textarea.setRangeText("", start - remove, start, "end");
        }
      } else {
        insertText("  ", "", "");
      }
      return;
    }

    if (!(event.ctrlKey || event.metaKey)) return;
    const shortcut = { b: "bold", i: "italic", k: "link" }[event.key.toLowerCase()];
    if (shortcut) {
      event.preventDefault();
      actions[shortcut]();
    }
  });

  imageInput.addEventListener("change", () => {
    const file = imageInput.files && imageInput.files[0];
    imageInput.value = "";
    uploadImage(file);
  });

  ["dragenter", "dragover"].forEach((name) => {
    root.addEventListener(name, (event) => {
      event.preventDefault();
      root.classList.add("is-dragging");
    });
  });

  ["dragleave", "drop"].forEach((name) => {
    root.addEventListener(name, (event) => {
      event.preventDefault();
      root.classList.remove("is-dragging");
    });
  });

  root.addEventListener("drop", async (event) => {
    const files = Array.from(event.dataTransfer?.files || []).filter((file) =>
      file.type.startsWith("image/"),
    );
    for (const file of files) {
      await uploadImage(file);
    }
  });

  textarea.addEventListener("paste", async (event) => {
    const items = Array.from(event.clipboardData?.items || []);
    const files = items
      .filter((item) => item.type.startsWith("image/"))
      .map((item) => item.getAsFile())
      .filter(Boolean);
    if (!files.length) return;

    event.preventDefault();
    for (const file of files) {
      await uploadImage(file);
    }
  });
})();
