"""
========== 账号服务：验证码、注销邮箱锁与输入规则 ==========
"""

import hashlib
import hmac
import re
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import settings
from app.mailer import send_code
from app.models import EmailRegistrationBlock, VerificationCode

CODE_TTL_SECONDS = 600
CODE_MAX_ATTEMPTS = 5
EMAIL_BLOCK_HOURS = 24

PURPOSE_REGISTER = "register"
PURPOSE_LOGIN_CODE = "login_code"
PURPOSE_RESET = "reset"
PURPOSE_ADMIN_LOGIN = "admin_login"
PURPOSE_LABELS = {
    PURPOSE_REGISTER: "注册验证码",
    PURPOSE_LOGIN_CODE: "登录验证码",
    PURPOSE_RESET: "密码重置验证码",
    PURPOSE_ADMIN_LOGIN: "后台登录验证码",
}


def now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def hash_code(code: str) -> str:
    return hmac.new(
        settings.secret_key.encode("utf-8"),
        code.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def purge_expired_codes(db: Session) -> None:
    db.execute(
        delete(VerificationCode).where(VerificationCode.expires_at < now_naive())
    )


def create_verification_code(
    db: Session,
    email: str,
    purpose: str,
    code: str,
    payload: dict | None = None,
) -> VerificationCode:
    purge_expired_codes(db)
    row = VerificationCode(
        email=email,
        purpose=purpose,
        code_hash=hash_code(code),
        payload=payload,
        expires_at=now_naive() + timedelta(seconds=CODE_TTL_SECONDS),
    )
    db.add(row)
    db.commit()
    return row


def generate_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def send_verification_code(
    db: Session,
    email: str,
    purpose: str,
    payload: dict | None = None,
) -> VerificationCode | None:
    code = generate_code()
    row = create_verification_code(db, email, purpose, code, payload=payload)
    if not send_code(email, code, PURPOSE_LABELS[purpose]):
        db.delete(row)
        db.commit()
        return None

    db.execute(
        delete(VerificationCode).where(
            VerificationCode.email == email,
            VerificationCode.purpose == purpose,
            VerificationCode.id != row.id,
        )
    )
    db.commit()
    return row


def load_pending_code(
    db: Session,
    pending: dict | None,
    purpose: str,
) -> VerificationCode | None:
    if not pending:
        return None

    code_id = pending.get("code_id")
    if code_id is None:
        return None

    row = db.get(VerificationCode, code_id)
    if row is None:
        return None
    if row.purpose != purpose or row.email != pending.get("email"):
        return None
    if row.expires_at <= now_naive():
        db.delete(row)
        db.commit()
        return None
    return row


def registration_is_blocked(db: Session, email: str) -> bool:
    block = db.scalar(
        select(EmailRegistrationBlock).where(EmailRegistrationBlock.email == email)
    )
    if block is None:
        return False
    if block.blocked_until <= now_naive():
        db.delete(block)
        db.commit()
        return False
    return True


def safe_next(next_url: str) -> str:
    if next_url.startswith("/") and not next_url.startswith("//"):
        return next_url
    return "/"


def valid_nickname(nickname: str) -> bool:
    return 3 <= len(nickname) <= 30 and re.fullmatch(r"\w+", nickname) is not None
