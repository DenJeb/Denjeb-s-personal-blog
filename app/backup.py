"""
========== 完整备份：MySQL + 上传图片 + 内容 JSON ==========
"""

import os
import re
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.engine import make_url

from app.config import PROJECT_DIR, settings

APP_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = APP_DIR / "static" / "uploads"
CONTENT_BACKUP = PROJECT_DIR / "content" / "content-backup.json"
BACKUP_ROOT = PROJECT_DIR / "backups"
BACKUP_NAME_RE = re.compile(r"^\d{8}-\d{6}$")


def prune_old_backups(keep: int | None = None) -> None:
    keep = settings.backup_keep if keep is None else keep
    if keep < 1 or not BACKUP_ROOT.is_dir():
        return

    backups = sorted(
        (
            path
            for path in BACKUP_ROOT.iterdir()
            if path.is_dir() and BACKUP_NAME_RE.fullmatch(path.name)
        ),
        key=lambda path: path.name,
        reverse=True,
    )
    for path in backups[keep:]:
        shutil.rmtree(path, ignore_errors=True)


def backup() -> Path:
    url = make_url(settings.database_url)
    mysqldump = settings.mysqldump_path
    if not Path(mysqldump).is_file() and shutil.which(mysqldump) is None:
        raise SystemExit(
            "找不到 mysqldump，请在 .env 里把 MYSQLDUMP_PATH 设为完整路径。"
        )

    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    BACKUP_ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
    target = BACKUP_ROOT / timestamp
    target.mkdir(parents=True, exist_ok=False, mode=0o700)
    try:
        os.chmod(BACKUP_ROOT, 0o700)
        os.chmod(target, 0o700)
    except OSError:
        pass

    command = [
        mysqldump,
        f"--host={url.host}",
        f"--port={url.port or 3306}",
        f"--user={url.username}",
        "--single-transaction",
        "--no-tablespaces",
        "--default-character-set=utf8mb4",
        url.database,
    ]
    env = {**os.environ, "MYSQL_PWD": url.password or ""}

    try:
        with (target / "database.sql").open("wb") as dump_file:
            subprocess.run(
                command,
                stdout=dump_file,
                stderr=subprocess.PIPE,
                check=True,
                env=env,
            )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", "replace") if exc.stderr else ""
        raise SystemExit(f"mysqldump 失败：{stderr}") from exc

    if UPLOAD_DIR.is_dir():
        shutil.copytree(UPLOAD_DIR, target / "uploads", dirs_exist_ok=True)

    if CONTENT_BACKUP.is_file():
        shutil.copy2(CONTENT_BACKUP, target / "content-backup.json")

    prune_old_backups()
    print(f"备份完成：{target}")
    return target


if __name__ == "__main__":
    backup()
