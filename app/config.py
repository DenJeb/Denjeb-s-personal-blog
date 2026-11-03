"""
========== 应用配置 ==========
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    app_name: str = "Denjeb 的个人博客"
    author_name: str = "DenJeb"
    debug: bool = False
    session_https_only: bool = False
    trusted_hosts: str = "localhost,127.0.0.1,testserver"
    secret_key: str
    admin_email: str
    site_url: str = "http://localhost:8000"
    email_enabled: bool = True
    admin_login_code_enabled: bool = True
    database_url: str = (
        "mysql+pymysql://user:password@127.0.0.1:3306/blog?charset=utf8mb4"
    )
    test_database_url: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False
    mysqldump_path: str = "mysqldump"
    backup_keep: int = 14

    model_config = SettingsConfigDict(
        env_file=PROJECT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def admin_email_normalized(self) -> str:
        return self.admin_email.strip().lower()

    @property
    def trusted_hosts_list(self) -> list[str]:
        hosts = [host.strip() for host in self.trusted_hosts.split(",") if host.strip()]
        return hosts or ["localhost", "127.0.0.1"]


settings = Settings()
