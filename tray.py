# tray.py
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QIcon, QLinearGradient, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon


class TranslatorTray(QSystemTrayIcon):
    left_clicked = pyqtSignal()
    auto_speak_toggled = pyqtSignal(bool)  # True 表示开启自动发音
    read_mode_toggled = pyqtSignal(bool)
    toggle_read_mode_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # 默认开启自动发音
        self.auto_speak_enabled = True

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

        # 添加自动发音开关
        self.auto_speak_action = self.menu.addAction("")
        self._update_auto_speak_action()
        self.auto_speak_action.triggered.connect(self._toggle_auto_speak)

        # Read mode 开关（快捷键和菜单同步）
        self.read_mode_enabled = False
        self.read_mode_action = self.menu.addAction("")
        self._update_read_mode_action()
        self.read_mode_action.triggered.connect(self.toggle_read_mode)
        self.toggle_read_mode_requested.connect(self.toggle_read_mode)

        # 添加退出操作
        self.exit_action = self.menu.addAction("退出 (Exit)")
        self.exit_action.triggered.connect(self.exit_app)

        # 将菜单设置给托盘
        self.setContextMenu(self.menu)

        # 左键单击托盘图标时发送信号
        self.activated.connect(self._on_activated)

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.left_clicked.emit()

    def _update_auto_speak_action(self):
        # 勾选状态直接体现在菜单文字上
        self.auto_speak_action.setText(
            "自动发音 ☑️" if self.auto_speak_enabled else "自动发音"
        )

    def _toggle_auto_speak(self):
        self.auto_speak_enabled = not self.auto_speak_enabled
        self._update_auto_speak_action()
        self.auto_speak_toggled.emit(self.auto_speak_enabled)

    def _update_read_mode_action(self):
        self.read_mode_action.setText(
            "Read mode ☑️ (Ctrl+Alt+T)" if self.read_mode_enabled
            else "Read mode (Ctrl+Alt+T)"
        )

    def toggle_read_mode(self):
        self.read_mode_enabled = not self.read_mode_enabled
        self._update_read_mode_action()
        self.read_mode_toggled.emit(self.read_mode_enabled)

    def exit_app(self):
        # 正常退出 PyQt 应用
        QApplication.quit()
