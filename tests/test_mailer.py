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

    assert mailer.send_code("user@example.com", "123456") is False

    captured = capsys.readouterr()
    assert "123456" not in captured.out
    assert "123456" not in captured.err


def test_send_email_disabled(monkeypatch, capsys):
    monkeypatch.setattr(settings, "debug", False)
    monkeypatch.setattr(settings, "email_enabled", False)

    assert mailer.send_email("user@example.com", "subject", "body") is False

    captured = capsys.readouterr()
    assert "subject" not in captured.out
    assert "subject" not in captured.err
