import os
import sys

# 将根目录加入 sys.path 以便导入 main.py 中的函数
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from main import fix_config_paths, validate_basic_settings_paths

def test_fix_config_paths_then_validate_paths(tmp_path):
    """YAML 中是旧绝对路径时，修复后关键路径可通过校验。"""
    data1_dir = tmp_path / "data1"
    data1_dir.mkdir()
    kb_dir = data1_dir / "data" / "knowledge_base"
    kb_dir.mkdir(parents=True)
    (kb_dir / "info.db").write_text("", encoding="utf-8")

    old_win_path = "Z:/legacy/aibot/data1"
    yaml_content = f"""
version: 0.3.1.3
KB_ROOT_PATH: {old_win_path}/data/knowledge_base
DB_ROOT_PATH: {old_win_path}/data/knowledge_base/info.db
SQLALCHEMY_DATABASE_URI: sqlite:///{old_win_path}/data/knowledge_base/info.db
API_SERVER:
  host: 127.0.0.1
    """
    (data1_dir / "basic_settings.yaml").write_text(yaml_content, encoding="utf-8")

    before = validate_basic_settings_paths(tmp_path)
    assert not before.ok
    assert any(item.startswith("KB_ROOT_PATH") for item in before.missing_items)
    assert any(item.startswith("DB_ROOT_PATH") for item in before.missing_items)
    assert any(item.startswith("SQLALCHEMY_DATABASE_URI") for item in before.missing_items)

    fix_config_paths(tmp_path)

    after = validate_basic_settings_paths(tmp_path)
    assert after.ok
    assert bool(after.checked_items["KB_ROOT_PATH"]["exists"])
    assert bool(after.checked_items["DB_ROOT_PATH"]["exists"])
    assert bool(after.checked_items["SQLALCHEMY_DATABASE_URI"]["exists"])

if __name__ == "__main__":
    import pytest
    pytest.main([__file__])
