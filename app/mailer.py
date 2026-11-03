"""
========== 邮件发送 ==========
"""

import smtplib
from email.message import EmailMessage

from app.config import settings


def send_email(to: str, subject: str, body: str) -> bool:
    if not settings.email_enabled:
        if settings.debug:
            print(f"[DEV] email to {to}: {subject}\n{body}")
            return True
        print("[mail] 邮件发送已关闭。")
        return False

    if not settings.smtp_host or (settings.smtp_user and not settings.smtp_password):
        if settings.debug:
            print(f"[DEV] email to {to}: {subject}\n{body}")
            return True
        print("[mail] SMTP 未配置，跳过邮件。")
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.smtp_from or settings.smtp_user
    message["To"] = to
    message.set_content(body)

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


def send_code(email: str, code: str, purpose: str = "验证码") -> bool:
    return send_email(
        email,
        f"{settings.app_name} {purpose}",
        f"你的{purpose}是：{code}\n\n10 分钟内有效。如果不是你本人操作，请忽略。",
    )
