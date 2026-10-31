"""
========== 备份恢复演练脚本测试 ==========
"""

import pytest

from app import rehearse_restore


def test_rehearsal_rejects_non_rehearsal_database(monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        ["rehearse_restore", "--database", "blog"],
    )

    with pytest.raises(SystemExit) as exc:
        rehearse_restore.main()

    assert "_rehearsal" in str(exc.value)
