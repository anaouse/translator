import ctypes

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QCursor, QPainter
from PyQt6.QtWidgets import QWidget


class ReadModeIndicator(QWidget):
    """Read mode 下跟随鼠标的短横线，不接收鼠标输入。"""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.NoDropShadowWindowHint
            | Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(18, 3)
        # Windows 11 会给小窗口加圆角和边框；禁止 DWM 修饰。
        hwnd = int(self.winId())
        value = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(value), ctypes.sizeof(value))
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 2, ctypes.byref(value), ctypes.sizeof(value))

        self._timer = QTimer(self)
        self._timer.setInterval(30)
        self._timer.timeout.connect(self._follow_cursor)

    def set_enabled(self, enabled: bool):
        if enabled:
            self._follow_cursor()
            self.show()
            self._timer.start()
        else:
            self._timer.stop()
            self.hide()

    def _follow_cursor(self):
        pos = QCursor.pos()
        self.move(pos.x() - self.width() // 2, pos.y() + 20)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#0078d7"))

