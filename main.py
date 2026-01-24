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