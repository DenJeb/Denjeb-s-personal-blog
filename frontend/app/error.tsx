"use client";

export default function ErrorPage({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <section className="status-page">
      <div className="glass status-card">
        <h1 className="status-title">页面暂时无法加载</h1>
        <p className="status-text">请稍后重试。</p>
        <div className="status-actions">
          <button type="button" onClick={reset} className="btn btn-primary">
            重试
          </button>
        </div>
      </div>
    </section>
  );
}
