"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  useRef,
  useState,
  type ChangeEvent,
  type ClipboardEvent,
  type DragEvent,
  type FormEvent,
  type KeyboardEvent,
} from "react";

import { AdminDeleteButton } from "./admin-delete-button";
import { ApiError, postForm, sendJson } from "@/lib/api/browser";

export type PostEditorInitial = {
  id: number;
  title: string;
  slug: string | null;
  summary: string;
  content: string;
  published_at: string;
  tags: string[];
  is_published: boolean;
};

export function PostEditor({
  initial,
  today,
}: {
  initial?: PostEditorInitial;
  today: string;
}) {
  const router = useRouter();
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [title, setTitle] = useState(initial?.title ?? "");
  const [slug, setSlug] = useState(initial?.slug ?? "");
  const [summary, setSummary] = useState(initial?.summary ?? "");
  const [content, setContent] = useState(initial?.content ?? "");
  const [publishedAt, setPublishedAt] = useState(
    initial?.published_at ?? today,
  );
  const [tags, setTags] = useState((initial?.tags ?? []).join(", "));
  const [published, setPublished] = useState(initial?.is_published ?? true);
  const [previewHtml, setPreviewHtml] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [uploading, setUploading] = useState(false);

  function handleError(caught: unknown) {
    if (caught instanceof ApiError && caught.status === 401) {
      router.push("/admin/login");
      return;
    }
    setError(
      caught instanceof ApiError ? caught.message : "操作失败，请稍后重试。",
    );
  }

  function insertText(text: string) {
    const textarea = textareaRef.current;
    if (!textarea) {
      setContent((value) => value + text);
      return;
    }

    // Read the live textarea value, not the render-time state: an image upload
    // can resolve after the user has typed more characters.
    const value = textarea.value;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    setContent(value.slice(0, start) + text + value.slice(end));
    requestAnimationFrame(() => {
      textarea.focus();
      const cursor = start + text.length;
      textarea.setSelectionRange(cursor, cursor);
    });
  }

  function wrapSelection(
    before: string,
    after: string,
    placeholder: string,
  ) {
    const textarea = textareaRef.current;
    if (!textarea) {
      return;
    }
    const value = textarea.value;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selected = value.slice(start, end) || placeholder;
    setContent(
      value.slice(0, start) + before + selected + after + value.slice(end),
    );
    requestAnimationFrame(() => {
      textarea.focus();
      textarea.setSelectionRange(
        start + before.length,
        start + before.length + selected.length,
      );
    });
  }

  function prefixSelectedLines(prefix: string) {
    const textarea = textareaRef.current;
    if (!textarea) {
      return;
    }
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
    const inserted = lines.join("\n");
    setContent(value.slice(0, lineStart) + inserted + value.slice(lineEnd));
    requestAnimationFrame(() => {
      textarea.focus();
      const cursor = lineStart + inserted.length;
      textarea.setSelectionRange(cursor, cursor);
    });
  }

  function insertLink() {
    const url = window.prompt("链接地址", "https://");
    if (url) {
      wrapSelection("[", `](${url})`, "链接文字");
    }
  }

  async function uploadImage(file: File) {
    setUploading(true);
    setError(null);
    try {
      const alt = window.prompt("图片说明（可留空）", "") ?? "";
      const form = new FormData();
      form.append("image", file);
      form.append("image_alt", alt);
      const data = await postForm<{ markdown: string }>(
        "/api/v1/admin/uploads/inline",
        form,
      );
      insertText(`\n\n${data.markdown}\n`);
    } catch (caught) {
      handleError(caught);
    } finally {
      setUploading(false);
    }
  }

  function onFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (file) {
      void uploadImage(file);
    }
    event.target.value = "";
  }

  function onDrop(event: DragEvent<HTMLTextAreaElement>) {
    const files = Array.from(event.dataTransfer.files).filter((file) =>
      file.type.startsWith("image/"),
    );
    if (!files.length) {
      return;
    }
    event.preventDefault();
    files.forEach((file) => void uploadImage(file));
  }

  function onPaste(event: ClipboardEvent<HTMLTextAreaElement>) {
    const files = Array.from(event.clipboardData.items)
      .filter((item) => item.type.startsWith("image/"))
      .map((item) => item.getAsFile())
      .filter((file): file is File => file !== null);
    if (!files.length) {
      return;
    }
    event.preventDefault();
    files.forEach((file) => void uploadImage(file));
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Tab") {
      event.preventDefault();
      if (event.shiftKey) {
        const textarea = event.currentTarget;
        const start = textarea.selectionStart;
        const lineStart = textarea.value.lastIndexOf("\n", start - 1) + 1;
        const beforeCursor = textarea.value.slice(lineStart, start);
        const remove = beforeCursor.endsWith("  ")
          ? 2
          : beforeCursor.endsWith(" ")
            ? 1
            : 0;
        if (remove) {
          const value = textarea.value;
          setContent(value.slice(0, start - remove) + value.slice(start));
          requestAnimationFrame(() => {
            textarea.focus();
            const cursor = start - remove;
            textarea.setSelectionRange(cursor, cursor);
          });
        }
      } else {
        insertText("  ");
      }
      return;
    }

    if (!(event.ctrlKey || event.metaKey)) {
      return;
    }
    const key = event.key.toLowerCase();
    if (key === "b") {
      event.preventDefault();
      wrapSelection("**", "**", "粗体");
    } else if (key === "i") {
      event.preventDefault();
      wrapSelection("*", "*", "斜体");
    } else if (key === "k") {
      event.preventDefault();
      insertLink();
    }
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      const body = {
        title,
        slug,
        summary,
        content,
        published_at: publishedAt,
        tags: tags
          .split(/[,，]/)
          .map((tag) => tag.trim())
          .filter(Boolean),
        is_published: published,
      };
      const endpoint = initial
        ? `/api/v1/admin/posts/${initial.id}`
        : "/api/v1/admin/posts";
      await sendJson(initial ? "PUT" : "POST", endpoint, body);
      router.push("/admin/posts");
      router.refresh();
    } catch (caught) {
      handleError(caught);
    } finally {
      setPending(false);
    }
  }

  async function preview() {
    setError(null);
    try {
      const data = await sendJson<{ html: string }>(
        "POST",
        "/api/v1/admin/posts/preview",
        { content },
      );
      setPreviewHtml(data.html);
    } catch (caught) {
      handleError(caught);
    }
  }

  return (
    <form onSubmit={onSubmit} className="glass admin-form post-editor">
      <label>
        标题
        <input
          type="text"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          maxLength={200}
          required
          className="form-input"
        />
      </label>

      <label>
        链接标识
        <input
          type="text"
          value={slug}
          onChange={(event) => setSlug(event.target.value)}
          maxLength={200}
          placeholder="留空则根据标题生成，例如 bo-ke-kai-zhang"
          className="form-input"
        />
        <small>文章地址为 /posts/链接标识，发布后尽量不要再改。</small>
      </label>

      <label>
        摘要
        <input
          type="text"
          value={summary}
          onChange={(event) => setSummary(event.target.value)}
          maxLength={500}
          className="form-input"
        />
      </label>

      <label>
        发布日期
        <input
          type="date"
          value={publishedAt}
          onChange={(event) => setPublishedAt(event.target.value)}
          required
          className="form-input"
        />
      </label>

      <label>
        标签（逗号分隔）
        <input
          type="text"
          value={tags}
          onChange={(event) => setTags(event.target.value)}
          placeholder="例如：FastAPI, 博客"
          className="form-input"
        />
      </label>

      <label className="admin-checkbox">
        <input
          type="checkbox"
          checked={published}
          onChange={(event) => setPublished(event.target.checked)}
        />
        发布到前台（不勾选则保存为草稿）
      </label>

      <div>
        <span className="admin-editor-label">正文</span>
        <div
          className="admin-editor-toolbar"
          role="toolbar"
          aria-label="Markdown 工具栏"
        >
          <button
            type="button"
            className="btn btn-ghost"
            title="粗体 (Ctrl+B)"
            aria-label="粗体"
            onClick={() => wrapSelection("**", "**", "粗体")}
          >
            <strong>B</strong>
          </button>
          <button
            type="button"
            className="btn btn-ghost"
            title="斜体 (Ctrl+I)"
            aria-label="斜体"
            onClick={() => wrapSelection("*", "*", "斜体")}
          >
            <em>I</em>
          </button>
          <button
            type="button"
            className="btn btn-ghost"
            title="标题格式"
            aria-label="标题格式"
            onClick={() => wrapSelection("## ", "", "标题")}
          >
            H
          </button>
          <button
            type="button"
            className="btn btn-ghost"
            title="链接 (Ctrl+K)"
            aria-label="链接"
            onClick={insertLink}
          >
            链接
          </button>
          <button
            type="button"
            className="btn btn-ghost"
            title="行内代码"
            aria-label="行内代码"
            onClick={() => wrapSelection("`", "`", "代码")}
          >
            &lt;/&gt;
          </button>
          <button
            type="button"
            className="btn btn-ghost"
            title="引用"
            aria-label="引用"
            onClick={() => prefixSelectedLines("> ")}
          >
            引用
          </button>
          <button
            type="button"
            className="btn btn-ghost"
            title="无序列表"
            aria-label="无序列表"
            onClick={() => prefixSelectedLines("- ")}
          >
            列表
          </button>
          <button
            type="button"
            className="btn btn-ghost"
            title="上传图片"
            aria-label="上传图片"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
          >
            图片
          </button>
          <button
            type="button"
            className="btn btn-ghost"
            title="预览"
            aria-label="预览"
            onClick={preview}
          >
            预览
          </button>
        </div>

        <label htmlFor="post-content" className="sr-only">
          正文
        </label>
        <textarea
          id="post-content"
          ref={textareaRef}
          name="content"
          value={content}
          onChange={(event) => setContent(event.target.value)}
          onKeyDown={onKeyDown}
          onDrop={onDrop}
          onDragOver={(event) => event.preventDefault()}
          onPaste={onPaste}
          rows={18}
          required
          className="form-input admin-editor-textarea"
        />

        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png,image/gif,image/webp"
          className="sr-only"
          onChange={onFileChange}
        />
      </div>

      {error ? (
        <p role="alert" className="form-error">
          {error}
        </p>
      ) : null}

      {previewHtml !== null ? (
        <section className="glass admin-editor-preview" aria-label="Markdown 预览">
          <div
            className="markdown-body"
            dangerouslySetInnerHTML={{ __html: previewHtml }}
          />
        </section>
      ) : null}

      <div className="admin-form-actions">
        <button type="submit" className="btn btn-primary" disabled={pending}>
          {pending ? "保存中…" : "保存"}
        </button>
        <Link href="/admin/posts" className="btn btn-ghost">
          取消
        </Link>
      </div>

      {initial ? (
        <p>
          <AdminDeleteButton
            endpoint={`/api/v1/admin/posts/${initial.id}`}
            label="删除这篇文章"
            confirmMessage="确定删除这篇文章吗？"
            redirectTo="/admin/posts"
          />
        </p>
      ) : null}
    </form>
  );
}
