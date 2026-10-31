"""
========== 备份保留策略测试 ==========
"""

from app import backup


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
