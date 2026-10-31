"""
========== 邮件发送 ==========
"""

import smtplib
from email.message import EmailMessage

from app.config import settings


def send_code(email: str, code: str, purpose: str = "验证码") -> bool:
    if not settings.smtp_host or (settings.smtp_user and not settings.smtp_password):
        if settings.debug:
            print(f"[DEV] {purpose} for {email}: {code}")
            return True
        print("[mail] SMTP 未配置，已拒绝发送验证码。")
        return False

    message = EmailMessage()
    message["Subject"] = f"{settings.app_name} {purpose}"
    message["From"] = settings.smtp_from or settings.smtp_user
    message["To"] = email
    message.set_content(
        f"你的{purpose}是：{code}\n\n10 分钟内有效。如果不是你本人操作，请忽略。"
    )

    try:
        if settings.smtp_use_ssl:
            smtp = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=10)
        else:
            smtp = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10)
        with smtp:
            if settings.smtp_use_tls and not settings.smtp_use_ssl:
                smtp.starttls()
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(message)
        return True
    except (OSError, smtplib.SMTPException) as exc:
        print(f"[mail] 发送失败：{exc}")
        return False
