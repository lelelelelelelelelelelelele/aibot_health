# start_with_env.py
import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv

def main():
    # 加载 .env
    env_file = Path(".env")
    if env_file.exists():
        print(f"✅ Loading {env_file}")
        load_dotenv(env_file, override=True)
    else:
        print("⚠️  .env not found")

    # 调试：打印关键变量
    print("API Key preview:", os.getenv("CHATCHAT_ROOT", "")[:10] + "...")

    # 启动 cpolar 内网穿透 (新终端窗口)
    print("🌐 Starting cpolar tunnel on port 7861...")
    try:
        # 使用 start 命令在 Windows 中开启新窗口运行 cpolar
        # cmd /k 保证即使命令退出窗口也不会立即关闭，方便查看 URL
        subprocess.Popen("start cmd /k cpolar http 7861", shell=True)
        print("✅ cpolar started in a new terminal. Please check the popup for the public URL.")
    except Exception as e:
        print(f"⚠️  Failed to launch cpolar: {e}")

    # 启动 chatchat
    try:
        # 直接调用 chatchat 脚本，Windows 下建议开启 shell=True
        subprocess.run(
            ["chatchat", "start", "--api"],
            shell=True,
            env=os.environ,  # 传递环境变量
            check=True       # 失败时抛异常
        )
    except subprocess.CalledProcessError as e:
        print(f"❌ chatchat failed with exit code {e.returncode}")
        sys.exit(e.returncode)
    except KeyboardInterrupt:
        print("\n🛑 Stopped by user")
        sys.exit(0)

if __name__ == "__main__":
    main()