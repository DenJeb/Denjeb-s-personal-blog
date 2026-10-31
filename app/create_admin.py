"""
========== 运维用：初始化或重置唯一管理员密码 ==========
"""

import argparse
import getpass

from pwdlib import PasswordHash
from sqlalchemy import func, select

from app.config import settings
from app.db import SessionLocal
from app.models import AdminUser

password_hash = PasswordHash.recommended()
PASSWORD_MIN_LENGTH = 8


def _prompt_password(label: str = "密码") -> str | None:
    password = getpass.getpass(f"{label}: ")
    if len(password) < PASSWORD_MIN_LENGTH:
        print(f"密码至少 {PASSWORD_MIN_LENGTH} 位。")
        return None

    confirm = getpass.getpass(f"再输入一次{label}: ")
    if password != confirm:
        print("两次密码不一致。")
        return None
    return password


def reset_admin_password(new_password: str) -> bool:
    """初始化或重置配置中的唯一管理员密码，成功返回 True。"""
    if len(new_password) < PASSWORD_MIN_LENGTH:
        return False

    admin_email = settings.admin_email_normalized
    with SessionLocal() as db:
        admin_count = db.scalar(select(func.count()).select_from(AdminUser)) or 0
        if admin_count > 1:
            return False

        admin = db.scalar(select(AdminUser).where(AdminUser.email == admin_email))
        if admin is None:
            # 唯一管理员不存在时允许初始化；但库里已有其他管理员则拒绝，
            # 避免在不知情的情况下产生多个管理员。
            if admin_count:
                return False

            username = admin_email.split("@", 1)[0][:50] or "admin"
            admin = AdminUser(
                username=username,
                email=admin_email,
                password_hash=password_hash.hash(new_password),
            )
            db.add(admin)
        else:
            admin.password_hash = password_hash.hash(new_password)
            admin.session_version += 1

        db.commit()
        return True


def reset_admin_password_flow() -> None:
    print(f"唯一管理员邮箱：{settings.admin_email_normalized}")

    password = _prompt_password("新密码")
    if password is None:
        return

    if reset_admin_password(password):
        print("管理员密码已设置。")
    else:
        print(
            "设置失败：新密码不符合要求，或数据库中已存在其他管理员。"
            "请先清理其他管理员账号。"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="初始化或重置唯一管理员密码")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="重置唯一管理员密码（默认行为相同）",
    )
    parser.parse_args()
    reset_admin_password_flow()


if __name__ == "__main__":
    main()
