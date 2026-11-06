import { siteConfig } from "@/lib/site-config";

export function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="site-footer-inner">
        <p>
          © {new Date().getFullYear()} {siteConfig.author} · 记录学习、开发与生活
        </p>
        <div className="site-footer-links">
          <a href="/rss.xml">RSS</a>
          <a href={siteConfig.github} target="_blank" rel="noopener noreferrer">
            GitHub
          </a>
          <a href={`mailto:${siteConfig.email}`}>邮箱</a>
        </div>
      </div>
    </footer>
  );
}
