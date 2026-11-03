"""
========== 邮件发送测试 ==========
"""

from app import mailer
from app.config import settings


def test_send_code_fails_closed_without_smtp_in_production(monkeypatch, capsys):
    monkeypatch.setattr(settings, "debug", False)
    monkeypatch.setattr(settings, "email_enabled", True)
    monkeypatch.setattr(settings, "smtp_host", "")
    monkeypatch.setattr(settings, "smtp_user", "")
    monkeypatch.setattr(settings, "smtp_password", "")

    assert mailer.send_code("user@blog.invalid", "123456") is False

    captured = capsys.readouterr()
    assert "123456" not in captured.out
    assert "123456" not in captured.err


def test_send_email_disabled(monkeypatch, capsys):
    monkeypatch.setattr(settings, "debug", False)
    monkeypatch.setattr(settings, "email_enabled", False)

    assert mailer.send_email("user@blog.invalid", "subject", "body") is False

    captured = capsys.readouterr()
    assert "subject" not in captured.out
    assert "subject" not in captured.err


def test_send_email_skips_test_recipient(monkeypatch):
    monkeypatch.setattr(settings, "debug", False)
    monkeypatch.setattr(settings, "email_enabled", True)
    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")

    def fail_smtp(*args, **kwargs):
        raise AssertionError("测试收件地址不应连接 SMTP")

    monkeypatch.setattr(mailer.smtplib, "SMTP", fail_smtp)

    assert mailer.send_email("__pytest_admin@example.com", "subject", "body") is False
    assert mailer.send_email("user@example.org", "subject", "body") is False
