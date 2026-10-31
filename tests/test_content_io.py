"""
========== 内容导出测试 ==========
"""

import json

from app.content_io import export_content


def test_export_content(tmp_path):
    path = tmp_path / "backup.json"
    export_content(path)

    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data["categories"]) >= 1
    assert len(data["posts"]) >= 1
    assert "content" in data["posts"][0]
    assert "is_published" in data["posts"][0]
    assert isinstance(data["comments"], list)
    assert "password" not in json.dumps(data).lower()
