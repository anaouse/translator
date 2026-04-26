# floating_window.py
import time

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor, QMouseEvent
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget


class FloatingWindow(QWidget):
    """鼠标选中文本后，在文本右下角出现的翻译小图标"""

    clicked = pyqtSignal()

    # 使用信号跨线程控制UI
    show_signal = pyqtSignal()
    check_click_signal = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        # 显示时不抢占焦点
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self.resize(28, 28)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.label = QLabel(self)
        self.label.setFixedSize(18, 18)
        self.label.setStyleSheet("""
            QLabel {
                background-color: rgba(255, 255, 255, 0.95);
                border: 1px solid rgba(0, 0, 0, 0.15);
                border-radius: 9px;
            }
            QLabel:hover {
                background-color: rgba(240, 240, 240, 1);
                border: 1px solid rgba(0, 120, 215, 0.8);
            }
        """)
        self.label.setCursor(Qt.CursorShape.PointingHandCursor)
        # Enable mouse tracking on both the window and the label
        self.setMouseTracking(True)
        self.label.setMouseTracking(True)
        self.label.installEventFilter(self)
        self._set_label_normal()

        layout.addWidget(self.label, alignment=Qt.AlignmentFlag.AlignCenter)

        # 绑定信号到对应的槽函数
        self.show_signal.connect(self._do_show_near_cursor)
        self.check_click_signal.connect(self._handle_global_click)

        # 记录上一次显示的时间
        self._show_time = 0.0

    def eventFilter(self, obj, event):
        if obj is self.label:
            if event.type() == event.Type.Enter:
                self._set_label_hovered()
            elif event.type() == event.Type.Leave:
                self._set_label_normal()
        return super().eventFilter(obj, event)

    def _set_label_normal(self):
        self.label.setStyleSheet("""
            QLabel {
                background-color: rgba(255, 255, 255, 0.95);
                border: 1px solid rgba(0, 0, 0, 0.15);
                border-radius: 9px;
            }
        """)

    def _set_label_hovered(self):
        self.label.setStyleSheet("""
            QLabel {
                background-color: rgba(240, 240, 240, 1);
                border: 1px solid rgba(0, 120, 215, 0.8);
                border-radius: 9px;
            }
        """)

    def _do_show_near_cursor(self):
        """主线程中执行的显示逻辑"""
        pos = QCursor.pos()
        self.move(pos.x() + 10, pos.y() + 10)
        self.show()
        self.raise_()
        # 每次显示时，更新时间戳
        self._show_time = time.time()

    def _handle_global_click(self):
        """主线程中执行的隐藏逻辑"""
        # 如果悬浮窗是最近 0.3 秒内才刚显示的，说明是触发双击的那次点击，忽略隐藏指令！
        if time.time() - self._show_time < 0.3:
            return
        if self.isVisible():
            pos = QCursor.pos()
            if not self.frameGeometry().contains(pos):
                self.hide()

    def mousePressEvent(self, event: QMouseEvent):
        # 点击自己会触发事件并隐藏，先隐藏再发送信号
        self.hide()
        self.clicked.emit()
