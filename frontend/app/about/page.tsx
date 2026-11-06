import type { Metadata } from "next";

import { PageHeader } from "@/components/ui/page-header";
import { pageMetadata } from "@/lib/page-metadata";
import { siteConfig } from "@/lib/site-config";

export const metadata: Metadata = pageMetadata({
  title: "关于",
  description: "关于 DenJeb 和本站",
  path: "/about",
});

export default function AboutPage() {
  return (
    <section className="shell">
      <PageHeader title="关于" description="关于 DenJeb，和这个正在生长的博客。" />

      <div className="about-grid">
        <section className="glass about-card">
          <div className="profile-top">
            <div className="avatar" aria-hidden="true">
              D
            </div>
            <div>
              <div className="profile-name">DenJeb</div>
              <div className="profile-role">大学生 / 计算机科学与技术</div>
            </div>
          </div>

          <ul className="about-list">
            <li>
              <strong>昵称：</strong>DenJeb
            </li>
            <li>
              <strong>身份：</strong>大学生
            </li>
            <li>
              <strong>专业：</strong>计算机科学与技术
            </li>
            <li>
              <strong>爱好：</strong>
              游戏、摄影、音乐、电影、篮球、羽毛球、乒乓球、旅游、记录
            </li>
            <li>
              <strong>GitHub：</strong>
              <a
                href={siteConfig.github}
                target="_blank"
                rel="noopener noreferrer"
              >
                {siteConfig.github}
              </a>
            </li>
            <li>
              <strong>邮箱：</strong>
              <a href={`mailto:${siteConfig.email}`}>{siteConfig.email}</a>
            </li>
          </ul>
        </section>

        <section className="glass about-card">
          <h2>关于本站</h2>
          <p className="about-text">
            本站使用 Next.js 前台 + FastAPI 后端，数据存储使用 MySQL，数据库迁移由
            Alembic 管理。
          </p>
          <p className="about-text">
            这里主要记录学习、开发和生活。文章之外，也会发一些动态、照片和零碎的想法。
          </p>
          <p className="about-text">内容持续更新中。</p>
        </section>
      </div>
    </section>
  );
}
