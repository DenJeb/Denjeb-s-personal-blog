"""
========== 账号服务：验证码、注销邮箱锁与输入规则 ==========
"""

import hashlib
import hmac
import re
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from app.config import settings
from app.mailer import send_code
from app.models import EmailRegistrationBlock, User, VerificationCode
from app.rate_limit import clear_bucket, is_rate_limited, record_event

CODE_TTL_SECONDS = 600
CODE_MAX_ATTEMPTS = 5
EMAIL_BLOCK_HOURS = 24
LOGIN_WINDOW_SECONDS = 300
LOGIN_MAX_FAILURES = 5
_password_hash = PasswordHash.recommended()


@dataclass(frozen=True)
class LoginResult:
    user: User | None
    reason: str
    message: str


def _login_bucket(ip: str) -> str:
    return f"user_login:{ip}"


def authenticate_password(
    db: Session,
    email: str,
    password: str,
    ip: str,
) -> LoginResult:
    """Validate an email/password login, applying the DB rate limit."""
    email = email.strip().lower()
    if is_rate_limited(db, _login_bucket(ip), LOGIN_WINDOW_SECONDS, LOGIN_MAX_FAILURES):
        return LoginResult(None, "blocked", "尝试次数过多，请 5 分钟后再试。")

    user = db.scalar(select(User).where(User.email == email))
    valid = False
    if user is not None:
        try:
            valid = _password_hash.verify(password, user.password_hash)
        except UnknownHashError:
            valid = False

    if user is None or not valid:
        record_event(db, _login_bucket(ip))
        return LoginResult(None, "invalid", "邮箱或密码错误")

    if not user.is_active:
        return LoginResult(None, "inactive", "账号已被禁用，请联系管理员。")

    clear_bucket(db, _login_bucket(ip))
    return LoginResult(user, "ok", "")


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


def code_matches(row: VerificationCode, code: str) -> bool:
    return secrets.compare_digest(row.code_hash, hash_code(code.strip()))


def record_failed_code_attempt(db: Session, row: VerificationCode) -> bool:
    """记录一次验证码错误尝试，返回 True 表示该验证码已失效。"""
    row.attempts += 1
    if row.attempts >= CODE_MAX_ATTEMPTS:
        db.delete(row)
        try:
            db.commit()
        except StaleDataError:
            db.rollback()
        return True

    try:
        db.commit()
    except StaleDataError:
        db.rollback()
        return True
    return False


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
    if (
        next_url.startswith("/")
        and not next_url.startswith("//")
        and "\\" not in next_url
        and not any(ord(char) < 32 or ord(char) == 127 for char in next_url)
    ):
        return next_url
    return "/"


def valid_nickname(nickname: str) -> bool:
    return 3 <= len(nickname) <= 30 and re.fullmatch(r"\w+", nickname) is not None


def toggle_user(db: Session, user: User) -> User:
    user.is_active = not user.is_active
    user.session_version += 1
    if not user.is_active and user.email:
        db.execute(
            delete(VerificationCode).where(VerificationCode.email == user.email.lower())
        )
    db.commit()
    return user


def delete_user(db: Session, user: User) -> None:
    if user.email:
        db.execute(
            delete(VerificationCode).where(VerificationCode.email == user.email.lower())
        )
    db.delete(user)
    db.commit()
