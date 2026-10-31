"""
========== 备份恢复演练：空库迁移 + 恢复 MySQL 备份 ==========
"""

import argparse
import os
import re
import shutil
import subprocess
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError

from app.config import PROJECT_DIR, settings

DEFAULT_BACKUP_ROOT = PROJECT_DIR / "backups"
REQUIRED_SUFFIX = "_rehearsal"


def _latest_backup() -> Path:
    if not DEFAULT_BACKUP_ROOT.is_dir():
        raise SystemExit("找不到 backups/ 目录，请先运行 python -m app.backup。")

    candidates = sorted(
        (path for path in DEFAULT_BACKUP_ROOT.iterdir() if path.is_dir()),
        reverse=True,
    )
    if not candidates:
        raise SystemExit("backups/ 里没有备份目录。")
    return candidates[0]


def _mysql_client() -> str:
    found = shutil.which("mysql")
    if found:
        return found

    dump_path = Path(settings.mysqldump_path)
    candidate = dump_path.with_name("mysql.exe" if os.name == "nt" else "mysql")
    if candidate.is_file():
        return str(candidate)
    raise SystemExit("找不到 mysql 客户端，请用 --mysql 指定路径。")


def _count_rows(engine, table: str, existing: set[str]) -> int | None:
    if table not in existing:
        return None
    with engine.connect() as connection:
        return connection.scalar(text(f"SELECT COUNT(*) FROM `{table}`")) or 0


def main() -> None:
    parser = argparse.ArgumentParser(description="在空库上演练迁移与备份恢复")
    parser.add_argument(
        "backup_dir",
        nargs="?",
        help="备份目录，默认取 backups/ 里最新一个",
    )
    parser.add_argument(
        "--database",
        default="blog_rehearsal",
        help="演练库名，必须以 _rehearsal 结尾",
    )
    parser.add_argument("--mysql", default="", help="mysql 客户端路径")
    parser.add_argument(
        "--keep",
        action="store_true",
        help="演练完成后保留演练库，方便手动检查",
    )
    args = parser.parse_args()

    if re.fullmatch(
        r"[A-Za-z0-9_]+", args.database
    ) is None or not args.database.endswith(REQUIRED_SUFFIX):
        raise SystemExit(
            "演练库名只能包含字母、数字、下划线，且必须以 _rehearsal 结尾。"
        )

    backup_dir = Path(args.backup_dir) if args.backup_dir else _latest_backup()
    dump_file = backup_dir / "database.sql"
    if not dump_file.is_file():
        raise SystemExit(f"备份目录里没有 database.sql：{backup_dir}")

    base_url = make_url(settings.database_url)
    rehearsal_url = base_url.set(database=args.database)
    rehearsal_url_string = rehearsal_url.render_as_string(hide_password=False)
    server_engine = create_engine(
        rehearsal_url._replace(database=None),
        pool_pre_ping=True,
    )

    try:
        try:
            with server_engine.connect() as connection:
                connection.execute(text(f"DROP DATABASE IF EXISTS `{args.database}`"))
                connection.execute(
                    text(
                        f"CREATE DATABASE `{args.database}` "
                        "CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci"
                    )
                )
                connection.commit()
        except OperationalError as exc:
            raise SystemExit(
                f"无法创建演练库 {args.database}。请用 MySQL 管理员执行：\n"
                f"  GRANT ALL PRIVILEGES ON `{args.database}`.* "
                "TO '<数据库用户>'@'localhost';\n"
                "或检查 DATABASE_URL 中的账号权限。"
            ) from exc

        # 让 Alembic 和 app.db 都指向演练库
        settings.database_url = rehearsal_url_string
        os.environ["DATABASE_URL"] = rehearsal_url_string

        from alembic import command
        from alembic.config import Config

        command.upgrade(Config(str(PROJECT_DIR / "alembic.ini")), "head")
        print(f"空库迁移完成：{args.database}")

        mysql = args.mysql or _mysql_client()
        mysql_command = [
            mysql,
            f"--host={rehearsal_url.host}",
            f"--port={rehearsal_url.port or 3306}",
            f"--user={rehearsal_url.username}",
            "--default-character-set=utf8mb4",
            args.database,
        ]
        env = {**os.environ, "MYSQL_PWD": rehearsal_url.password or ""}
        try:
            with dump_file.open("rb") as dump:
                subprocess.run(
                    mysql_command,
                    stdin=dump,
                    check=True,
                    env=env,
                )
        except FileNotFoundError as exc:
            raise SystemExit(f"找不到 mysql 客户端：{mysql}") from exc
        except subprocess.CalledProcessError as exc:
            raise SystemExit(f"mysql 恢复失败，退出码 {exc.returncode}") from exc
        print(f"备份已恢复：{dump_file}")

        rehearsal_engine = create_engine(rehearsal_url_string)
        try:
            existing = set(inspect(rehearsal_engine).get_table_names())
            for table in (
                "alembic_version",
                "categories",
                "blog_posts",
                "notes",
                "comments",
                "users",
                "admin_users",
                "verification_codes",
                "email_registration_blocks",
                "rate_limit_events",
            ):
                count = _count_rows(rehearsal_engine, table, existing)
                value = "缺失" if count is None else f"{count} 行"
                print(f"  {table:16} {value}")
        finally:
            rehearsal_engine.dispose()

        if args.keep:
            print(f"已保留演练库 {args.database}，可手动检查。")
        else:
            with server_engine.connect() as connection:
                connection.execute(text(f"DROP DATABASE IF EXISTS `{args.database}`"))
                connection.commit()
            print(f"演练库已删除：{args.database}")
    finally:
        server_engine.dispose()


if __name__ == "__main__":
    main()
