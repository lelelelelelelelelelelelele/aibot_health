# start_with_env.py
import os
import sys
import subprocess
import glob
import re
from pathlib import Path
from dotenv import load_dotenv

def fix_config_paths(root_dir: Path):
    """自动修正 data1 目录下所有 yaml 文件中的绝对路径"""
    data1_dir = root_dir / "data1"
    if not data1_dir.exists():
        print(f"⚠️  {data1_dir} not found, skipping path fix.")
        return

    current_abs_path = str(data1_dir.absolute()).replace("\\", "/")
    yaml_files = glob.glob(str(data1_dir / "*.yaml"))
    
    # 匹配 Windows (X:\...) 或 Linux (/...) 的 data1 路径模式
    # 我们主要替换 H:\project\aibot\data1 这种硬编码
    pattern = re.compile(r'(?<![A-Za-z])([A-Za-z]:[\\/][^ \n\r"\'$]+[\\/]data1|/[^ \n\r"\'$]+[\\/]data1)')
    sqlite_pattern = re.compile(r"sqlite:/{3,}([^\s]+)")

    for yaml_path in yaml_files:
        with open(yaml_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 将匹配到的旧路径替换为当前环境的路径（但跳过 sqlite URI 内部）
        def _path_repl(match: re.Match) -> str:
            start = match.start()
            prefix = content[max(0, start - 10):start].lower()
            if "sqlite:" in prefix:
                return match.group(0)
            return current_abs_path

        new_content = pattern.sub(_path_repl, content)

        # 特殊处理：规范 sqlite URI 的斜杠与路径分隔符，并替换为当前 data1 路径
        def _sqlite_repl(match: re.Match) -> str:
            path = match.group(1).replace("\\", "/")
            if "/data1/" in path or path.endswith("/data1"):
                suffix = path.split("/data1", 1)[1]
                path = f"{current_abs_path}{suffix}"
            return f"sqlite:///{path}"

        new_content = sqlite_pattern.sub(_sqlite_repl, new_content)

        if new_content != content:
            with open(yaml_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"🔧 Updated paths in {os.path.basename(yaml_path)}")

def check_config_paths(root_dir: Path):
    """检查 basic_settings.yaml 中的关键路径是否存在"""
    config_path = root_dir / "data1" / "basic_settings.yaml"
    if not config_path.exists():
        print(f"⚠️  Missing config: {config_path}")
        return

    with open(config_path, "r", encoding="utf-8") as f:
        content = f.read()

    def _extract_value(key: str) -> str | None:
        match = re.search(rf"^{key}:\s*(.+)$", content, flags=re.MULTILINE)
        return match.group(1).strip() if match else None

    def _sqlite_path(uri: str | None) -> str | None:
        if not uri:
            return None
        if uri.startswith("sqlite:///"):
            return uri.replace("sqlite:///", "", 1)
        return None

    checks = {
        "KB_ROOT_PATH": _extract_value("KB_ROOT_PATH"),
        "DB_ROOT_PATH": _extract_value("DB_ROOT_PATH"),
        "SQLALCHEMY_DATABASE_URI": _sqlite_path(_extract_value("SQLALCHEMY_DATABASE_URI")),
    }

    for key, path_value in checks.items():
        if not path_value:
            print(f"⚠️  {key} not found in {config_path.name}")
            continue
        normalized = path_value.replace("\\", "/")
        exists = os.path.exists(path_value)
        status = "✅" if exists else "❌"
        print(f"{status} {key} -> {normalized}")

def main():
    # 获取项目根目录
    project_root = Path(__file__).parent.absolute()
    
    # 1. 自动修正 data1 中的绝对路径 (关键：实现跨平台零配置)
    fix_config_paths(project_root)

    # 1.1 检查关键路径是否存在
    check_config_paths(project_root)

    # 2. 设置环境变量，确保 chatchat 能找到配置文件
    data1_path = str((project_root / "data1").absolute())
    os.environ["CHATCHAT_ROOT"] = data1_path
    
    # 加载 .env
    env_file = project_root / ".env"
    if env_file.exists():
        print(f"✅ Loading {env_file}")
        load_dotenv(env_file, override=True)
    else:
        print("⚠️  .env not found")

    # 调试：打印关键变量
    print(f"📍 CHATCHAT_ROOT set to: {os.environ['CHATCHAT_ROOT']}")

    # 启动 cpolar 内网穿透 (仅在 Windows 且有 start 命令时)
    if os.name == 'nt':
        print("🌐 Starting cpolar tunnel on port 7861...")
        try:
            subprocess.Popen("start cmd /k cpolar http 7861", shell=True)
            print("✅ cpolar started in a new terminal.")
        except Exception as e:
            print(f"⚠️  Failed to launch cpolar: {e}")

    # 启动 chatchat
    try:
        # 使用当前进程的环境变量启动
        subprocess.run(
            ["chatchat", "start", "--api"],
            shell=(os.name == 'nt'),
            env=os.environ,
            check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"❌ chatchat failed with exit code {e.returncode}")
        sys.exit(e.returncode)
    except KeyboardInterrupt:
        print("\n🛑 Stopped by user")
        sys.exit(0)

if __name__ == "__main__":
    main()