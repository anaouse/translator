import subprocess
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication


def generate_ico_file(icon_path="icon.ico"):
    """
    使用你 tray.py 中的逻辑，提前渲染一张图片并保存为 .ico 文件供打包使用。
    """
    print("正在生成 exe 图标文件...")

    app = QApplication.instance() or QApplication(sys.argv)

    size = 256

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    gradient = QLinearGradient(0, 0, 0, size)
    gradient.setColorAt(0.0, QColor("#5E81AC"))
    gradient.setColorAt(1.0, QColor("#88C0D0"))

    painter.setBrush(QBrush(gradient))
    painter.setPen(Qt.PenStyle.NoPen)

    # 按比例放大你原本的参数 (原本 64 尺寸下缩进 2，圆角 8；现在 256 尺寸缩进 8，圆角 32)
    rect = pixmap.rect().adjusted(8, 8, -8, -8)
    painter.drawRoundedRect(rect, 32, 32)

    painter.end()

    # 保存为 ico 文件
    success = pixmap.save(icon_path, "ICO")
    if success:
        print(f"图标已成功保存至: {icon_path}")
    else:
        print("图标保存失败！")
        sys.exit(1)


if __name__ == "__main__":
    icon_filename = "icon.ico"

    # 1. 先生成实体图标文件
    generate_ico_file(icon_filename)

    # 2. 将 --icon 参数加入 PyInstaller 命令中
    cmd = [
        "pyinstaller",
        "--onefile",
        "--noconsole",
        f"--icon={icon_filename}",
        "--name",
        "translator",
        "main.py",
    ]

    print("正在打包为exe...")
    result = subprocess.run(cmd, capture_output=False, text=True)

    if result.returncode == 0:
        print("打包成功！exe文件位于 dist/translator.exe")
    else:
        print("打包失败：")
        print(result.stderr)
        sys.exit(1)
