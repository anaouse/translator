# tray.py
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor, QIcon, QLinearGradient, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon


class TranslatorTray(QSystemTrayIcon):
    def __init__(self, parent=None):
        super().__init__(parent)

        # 设置托盘图标
        size = 64  # 画布大小，托盘会自动缩放到合适尺寸

        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        gradient = QLinearGradient(0, 0, 0, size)
        gradient.setColorAt(0.0, QColor("#5E81AC"))
        gradient.setColorAt(1.0, QColor("#88C0D0"))

        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.PenStyle.NoPen)

        # 画圆角正方形，圆角半径设为 8px
        rect = pixmap.rect().adjusted(2, 2, -2, -2)
        painter.drawRoundedRect(rect, 8, 8)

        painter.end()

        self.setIcon(QIcon(pixmap))

        # 设置鼠标悬停时的提示文字
        self.setToolTip("Translator (选中文本后 Alt+A 或点击悬浮窗翻译)")

        # 创建右键菜单
        self.menu = QMenu()

        # 添加退出操作
        self.exit_action = self.menu.addAction("退出 (Exit)")
        self.exit_action.triggered.connect(self.exit_app)

        # 将菜单设置给托盘
        self.setContextMenu(self.menu)

    def exit_app(self):
        # 正常退出 PyQt 应用
        QApplication.quit()
