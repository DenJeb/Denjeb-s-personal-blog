"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { ApiError, sendJson } from "@/lib/api/browser";

type SecurityState = {
  totp_enabled: boolean;
  setup_secret?: string | null;
  setup_uri?: string | null;
};

export function SecurityPanel({ initial }: { initial: SecurityState }) {
  const router = useRouter();
  const [state, setState] = useState(initial);
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  function handleError(caught: unknown) {
    if (caught instanceof ApiError && caught.status === 401) {
      router.push("/admin/login");
      return;
    }
    setError(
      caught instanceof ApiError ? caught.message : "操作失败，请稍后重试。",
    );
  }

  async function start() {
    setPending(true);
    setError(null);
    try {
      const data = await sendJson<SecurityState>(
        "POST",
        "/api/v1/admin/security/totp/start",
      );
      setState(data);
      router.refresh();
    } catch (caught) {
      handleError(caught);
    } finally {
      setPending(false);
    }
  }

  async function enable(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      await sendJson("POST", "/api/v1/admin/security/totp/enable", { code });
      setState({ totp_enabled: true });
      setCode("");
      router.refresh();
    } catch (caught) {
      handleError(caught);
    } finally {
      setPending(false);
    }
  }

  async function disable(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      await sendJson("POST", "/api/v1/admin/security/totp/disable", {
        password,
        code,
      });
      setState({ totp_enabled: false });
      setPassword("");
      setCode("");
      router.refresh();
    } catch (caught) {
      handleError(caught);
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="glass admin-panel admin-security">
      <h2>两步验证（TOTP）</h2>

      {error ? (
        <p role="alert" className="form-error">
          {error}
        </p>
      ) : null}

      {state.totp_enabled ? (
        <>
          <p>已启用。每次登录除了密码，还需要输入认证器中的 6 位验证码。</p>
          <details>
            <summary>关闭两步验证</summary>
            <form onSubmit={disable}>
              <div className="form-field">
                <label htmlFor="totp-password" className="form-label">
                  当前密码
                </label>
                <input
                  id="totp-password"
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  autoComplete="current-password"
                  required
                  className="form-input"
                />
              </div>
              <div className="form-field">
                <label htmlFor="totp-disable-code" className="form-label">
                  认证器验证码
                </label>
                <input
                  id="totp-disable-code"
                  type="text"
                  value={code}
                  onChange={(event) => setCode(event.target.value)}
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  pattern="[0-9]{6}"
                  maxLength={6}
                  required
                  className="form-input"
                />
              </div>
              <button
                type="submit"
                className="btn btn-ghost"
                disabled={pending}
              >
                关闭两步验证
              </button>
            </form>
          </details>
        </>
      ) : state.setup_secret ? (
        <>
          <p>1. 在认证器中手动添加以下密钥（或导入下方的 otpauth 链接）：</p>
          <p>
            <code data-totp-secret>{state.setup_secret}</code>
          </p>
          <p>
            <small>{state.setup_uri}</small>
          </p>
          <p>2. 输入认证器生成的 6 位验证码完成启用：</p>
          <form onSubmit={enable}>
            <div className="form-field">
              <label htmlFor="totp-enable-code" className="form-label">
                验证码
              </label>
              <input
                id="totp-enable-code"
                type="text"
                value={code}
                onChange={(event) => setCode(event.target.value)}
                inputMode="numeric"
                autoComplete="one-time-code"
                pattern="[0-9]{6}"
                maxLength={6}
                required
                className="form-input"
              />
            </div>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={pending}
            >
              启用两步验证
            </button>
          </form>
        </>
      ) : (
        <>
          <p>未启用。建议开启，避免密码泄露后直接进入后台。</p>
          <button
            type="button"
            className="btn btn-primary"
            onClick={start}
            disabled={pending}
          >
            开始设置
          </button>
        </>
      )}

      <p>
        <small>
          如果丢失认证器，可在服务器运行{" "}
          <code>python -m app.create_admin --reset-totp</code>。
        </small>
      </p>
    </div>
  );
}
