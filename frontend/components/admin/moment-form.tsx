"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { ApiError, sendJson } from "@/lib/api/browser";

export function MomentForm({
  momentId,
  initialContent,
}: {
  momentId?: number;
  initialContent: string;
}) {
  const router = useRouter();
  const [content, setContent] = useState(initialContent);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setPending(true);

    try {
      const endpoint = momentId
        ? `/api/v1/admin/moments/${momentId}`
        : "/api/v1/admin/moments";
      await sendJson(momentId ? "PUT" : "POST", endpoint, { content });
      router.push("/admin/moments");
      router.refresh();
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) {
        router.push("/admin/login");
        return;
      }
      setError(
        caught instanceof ApiError ? caught.message : "保存失败，请稍后重试。",
      );
    } finally {
      setPending(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="glass admin-form">
      <label>
        内容
        <textarea
          name="content"
          value={content}
          onChange={(event) => setContent(event.target.value)}
          rows={10}
          maxLength={2000}
          required
          className="form-input"
        />
      </label>

      {error ? (
        <p role="alert" className="form-error">
          {error}
        </p>
      ) : null}

      <div className="admin-form-actions">
        <button type="submit" className="btn btn-primary" disabled={pending}>
          {pending ? "保存中…" : "保存"}
        </button>
        <Link href="/admin/moments" className="btn btn-ghost">
          取消
        </Link>
      </div>
    </form>
  );
}
