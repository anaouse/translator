# tray.py
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMenu, QStyle, QSystemTrayIcon


class TranslatorTray(QSystemTrayIcon):
    def __init__(self, parent=None):
        super().__init__(parent)

        # 设置托盘图标
        # 这里默认使用 PyQt 自带的电脑图标作为占位符。
        # 建议后续替换为你自己的图标，例如: self.setIcon(QIcon("icon.png"))
        standard_icon = QApplication.style().standardIcon(
            QStyle.StandardPixmap.SP_ComputerIcon
        )
        self.setIcon(standard_icon)

        # 设置鼠标悬停时的提示文字
        self.setToolTip("AI Translator (Alt+A 唤醒)")

        # 创建右键菜单
        self.menu = QMenu()

        # 添加退出操作
        self.exit_action = self.menu.addAction("退出 (Exit)")
        self.exit_action.triggered.connect(self.exit_app)

        # 将菜单设置给托盘
        self.setContextMenu(self.menu)

    def exit_app(self):
        # 正常退出 PyQt 应用
        # 因为 main.py 中的 pynput 监听器设置了 daemon=True，
        # 主线程退出后，监听器也会自动随之销毁，实现干净利落的退出。
        QApplication.quit()
