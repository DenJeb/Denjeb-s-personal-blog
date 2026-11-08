"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useId, useState, type FormEvent } from "react";

import { ApiError, postJson } from "@/lib/api/browser";

type WriteResponse = {
  ok: boolean;
  message: string;
};

export function WriteForm({
  endpoint,
  maxLength,
  isLoggedIn,
  nextPath,
  placeholder,
  buttonLabel,
  loginPrompt,
}: {
  endpoint: string;
  maxLength: number;
  isLoggedIn: boolean;
  nextPath: string;
  placeholder: string;
  buttonLabel: string;
  loginPrompt: string;
}) {
  const router = useRouter();
  const inputId = useId();
  const [content, setContent] = useState("");
  const [website, setWebsite] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  if (!isLoggedIn) {
    return (
      <p className="comment-login-hint">
        <Link
          href={`/login?next=${encodeURIComponent(nextPath)}`}
          className="btn btn-ghost"
        >
          {loginPrompt}
        </Link>
      </p>
    );
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setMessage(null);
    setPending(true);

    try {
      const result = await postJson<WriteResponse>(endpoint, {
        content,
        website,
      });
      setMessage(result.message);
      setContent("");
      router.refresh();
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) {
        router.push(`/login?next=${encodeURIComponent(nextPath)}`);
        return;
      }
      setError(
        caught instanceof ApiError ? caught.message : "提交失败，请稍后重试。",
      );
    } finally {
      setPending(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="comment-form">
      <label htmlFor={inputId} className="sr-only">
        {placeholder}
      </label>
      <textarea
        id={inputId}
        name="content"
        value={content}
        onChange={(event) => setContent(event.target.value)}
        maxLength={maxLength}
        required
        placeholder={placeholder}
        className="form-input comment-textarea"
      />

      <input
        type="text"
        name="website"
        value={website}
        onChange={(event) => setWebsite(event.target.value)}
        className="honeypot"
        tabIndex={-1}
        autoComplete="off"
        aria-hidden="true"
      />

      {error ? (
        <p role="alert" className="form-error">
          {error}
        </p>
      ) : null}
      {message ? (
        <p role="status" className="form-success">
          {message}
        </p>
      ) : null}

      <div className="comment-form-actions">
        <button type="submit" className="btn btn-primary" disabled={pending}>
          {pending ? "提交中…" : buttonLabel}
        </button>
        <span className="comment-form-hint">提交后按站点规则展示</span>
      </div>
    </form>
  );
}
