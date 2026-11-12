"""
========== 后台安全设置服务：TOTP ==========
"""

import pyotp
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError
from sqlalchemy.orm import Session

from app.models import AdminUser

_password_hash = PasswordHash.recommended()


def provisioning_uri(secret: str, name: str, issuer: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=name, issuer_name=issuer)


def verify_totp(secret: str, code: str) -> bool:
    return pyotp.TOTP(secret).verify(code.strip(), valid_window=1)


def enable_totp(db: Session, admin: AdminUser, secret: str) -> None:
    admin.totp_secret = secret
    db.commit()


def disable_totp(db: Session, admin: AdminUser, password: str, code: str) -> bool:
    if not admin.totp_secret:
        return False

    try:
        valid_password = _password_hash.verify(password, admin.password_hash)
    except UnknownHashError:
        valid_password = False

    if not valid_password or not verify_totp(admin.totp_secret, code):
        return False

    admin.totp_secret = None
    admin.session_version += 1
    db.commit()
    return True
