import ctypes

from PyQt6.QtCore import QRectF, Qt, QTimer
from PyQt6.QtGui import QColor, QCursor, QPainter
from PyQt6.QtWidgets import QWidget

# DWM 窗口属性编号
DWMWA_BORDER_COLOR = 34
DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMCP_DONOTROUND = 1
DWMWA_COLOR_NONE = 0xFFFFFFFE  # 表示"不画"


class ReadModeIndicator(QWidget):
    """Read mode 下跟随鼠标的蓝色短横线，不接收鼠标输入、不抢焦点、无边框。"""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.NoDropShadowWindowHint
            | Qt.WindowType.WindowTransparentForInput
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(20, 4)

        self._apply_dwm_attributes()

        self._timer = QTimer(self)
        self._timer.setInterval(30)
        self._timer.timeout.connect(self._follow_cursor)

    def _apply_dwm_attributes(self):
        """去掉 Windows 11 给顶层窗口加上的圆角和 1px 边框。"""
        hwnd = int(self.winId())
        no_round = ctypes.c_int(DWMCP_DONOTROUND)
        no_border = ctypes.c_int(DWMWA_COLOR_NONE)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_WINDOW_CORNER_PREFERENCE,
            ctypes.byref(no_round),
            ctypes.sizeof(no_round),
        )
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_BORDER_COLOR,
            ctypes.byref(no_border),
            ctypes.sizeof(no_border),
        )

    def showEvent(self, event):
        # 显示后 DWM 可能重新套用默认边框，再设一次。
        super().showEvent(event)
        self._apply_dwm_attributes()

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
        # 只画一条蓝色圆角细线，不留任何背景或边框。
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#0078d7"))
        radius = self.height() / 2
        painter.drawRoundedRect(QRectF(self.rect()), radius, radius)
