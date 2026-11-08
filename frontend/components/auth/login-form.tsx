"use client";

import { useState, type FormEvent } from "react";

import { ApiError, postJson } from "@/lib/api/browser";

export function LoginForm({ next }: { next: string }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setPending(true);

    try {
      await postJson("/api/v1/auth/login", { email, password });
      // Full navigation so the server-rendered layout sees the new session
      // cookie instead of reusing the pre-login client router cache.
      window.location.assign(next);
    } catch (caught) {
      setError(
        caught instanceof ApiError ? caught.message : "登录失败，请稍后重试。",
      );
    } finally {
      setPending(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="auth-form">
      <div className="form-field">
        <label htmlFor="login-email" className="form-label">
          邮箱
        </label>
        <input
          id="login-email"
          type="email"
          name="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          autoComplete="email"
          required
          className="form-input"
        />
      </div>

      <div className="form-field">
        <label htmlFor="login-password" className="form-label">
          密码
        </label>
        <input
          id="login-password"
          type="password"
          name="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          autoComplete="current-password"
          required
          className="form-input"
        />
      </div>

      {error ? (
        <p role="alert" className="form-error">
          {error}
        </p>
      ) : null}

      <button type="submit" className="btn btn-primary" disabled={pending}>
        {pending ? "登录中…" : "登录"}
      </button>

      <div className="auth-links">
        <a href="/register">还没有账号？注册</a>
        <a href="/login/code">使用邮箱验证码登录</a>
        <a href="/forgot-password">忘记密码？</a>
      </div>
    </form>
  );
}
