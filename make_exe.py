import subprocess
import sys

if __name__ == "__main__":
    # 使用subprocess运行PyInstaller命令将项目打包为exe
    cmd = ["pyinstaller", "--onefile", "--name", "translator", "main.py"]

    print("正在打包为exe...")
    result = subprocess.run(cmd, capture_output=False, text=True)

    if result.returncode == 0:
        print("打包成功！exe文件位于 dist/translator.exe")
    else:
        print("打包失败：")
        print(result.stderr)
        sys.exit(1)
