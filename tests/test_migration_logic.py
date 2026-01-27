import pytest
import os
import re
import glob
from pathlib import Path
import sys

# 将根目录加入 sys.path 以便导入 main.py 中的函数
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from main import fix_config_paths

def test_fix_config_paths_logic(tmp_path):
    """
    测试 main.py 中的路径修复逻辑是否能正确处理跨平台转换
    """
    # 1. 模拟一个 data1 文件夹
    data1_dir = tmp_path / "data1"
    data1_dir.mkdir()
    # 2. 创建一个模拟的 basic_settings.yaml，其中包含硬编码的 Windows 绝对路径
    old_win_path = "H:\\project\\aibot\\data1"
    old_win_path_slash = old_win_path.replace("\\", "/")
    yaml_content = f"""
version: 0.3.1.3
KB_ROOT_PATH: {old_win_path}\\data\\knowledge_base
DB_ROOT_PATH: {old_win_path}\\data\\knowledge_base\\info.db
# 混合斜杠测试
SQLALCHEMY_DATABASE_URI: sqlite:///{old_win_path_slash}/data/knowledge_base/info.db
API_SERVER:
  host: 127.0.0.1
    """
    yaml_file = data1_dir / "basic_settings.yaml"
    yaml_file.write_text(yaml_content, encoding="utf-8")

    # 3. 运行修复逻辑 (传入 tmp_path 作为项目根目录)
    fix_config_paths(tmp_path)

    # 4. 读取结果并验证
    updated_content = yaml_file.read_text(encoding="utf-8")
    new_abs_path = str(data1_dir.absolute()).replace("\\", "/")

    # 验证普通路径是否已替换
    assert old_win_path not in updated_content
    assert new_abs_path in updated_content
    
    # 验证 sqlite 格式是否正确 (确保是 sqlite:/// 而不是 sqlite:////)
    assert f"sqlite:///{new_abs_path}" in updated_content
    # 检查是否有重复叠加
    assert f"sqlite:///{new_abs_path}{new_abs_path}" not in updated_content
    
    print(f"\n[Test Success] YAML updated with: {new_abs_path}")

def test_no_data1_dir(tmp_path):
    """测试当没有 data1 目录时不会崩溃"""
    try:
        fix_config_paths(tmp_path)
    except Exception as e:
        pytest.fail(f"fix_config_paths crashed without data1 dir: {e}")

if __name__ == "__main__":
    # 允许直接手动运行
    pytest.main([__file__])
