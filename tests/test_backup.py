"""
========== 备份保留策略测试 ==========
"""

from app import backup


def test_backup_name_re_accepts_legacy_and_microsecond_names():
    assert backup.BACKUP_NAME_RE.fullmatch("20260101-000000")
    assert backup.BACKUP_NAME_RE.fullmatch("20260101-000000-123456")
    assert not backup.BACKUP_NAME_RE.fullmatch("not-a-backup")


def test_prune_old_backups(tmp_path, monkeypatch):
    monkeypatch.setattr(backup, "BACKUP_ROOT", tmp_path)

    names = [f"202601{i:02d}-000000" for i in range(1, 17)]
    for name in names:
        (tmp_path / name).mkdir()
    (tmp_path / "not-a-backup").mkdir()

    backup.prune_old_backups(keep=14)

    remaining = sorted(path.name for path in tmp_path.iterdir())
    assert len([name for name in remaining if name.startswith("2026")]) == 14
    assert "20260101-000000" not in remaining
    assert "20260102-000000" not in remaining
    assert "20260103-000000" in remaining
    assert "not-a-backup" in remaining


def test_backup_regenerates_content_json(tmp_path, monkeypatch):
    content = tmp_path / "content-backup.json"
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    dump_bin = tmp_path / "mysqldump"
    dump_bin.write_text("", encoding="utf-8")
    calls = []

    def fake_export(path):
        calls.append(path)
        path.write_text('{"posts": []}', encoding="utf-8")

    monkeypatch.setattr(backup, "BACKUP_ROOT", tmp_path / "backups")
    monkeypatch.setattr(backup, "CONTENT_BACKUP", content)
    monkeypatch.setattr(backup, "UPLOAD_DIR", uploads)
    monkeypatch.setattr(backup, "export_content", fake_export, raising=False)
    monkeypatch.setattr(backup.settings, "database_url", "sqlite:///unused.db")
    monkeypatch.setattr(backup.settings, "mysqldump_path", str(dump_bin))
    monkeypatch.setattr(backup.subprocess, "run", lambda *args, **kwargs: None)

    target = backup.backup()

    assert calls == [content]
    assert (target / "content-backup.json").read_text(encoding="utf-8") == (
        '{"posts": []}'
    )
    assert (target / "database.sql").is_file()
