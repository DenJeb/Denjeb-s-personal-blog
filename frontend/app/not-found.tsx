import Link from "next/link";

export default function NotFound() {
  return (
    <section className="status-page">
      <div className="glass status-card">
        <h1 className="status-title">页面不存在</h1>
        <p className="status-text">你访问的页面可能已被移动或删除。</p>
        <div className="status-actions">
          <Link href="/" className="btn btn-ghost">
            返回首页
          </Link>
        </div>
      </div>
    </section>
  );
}
