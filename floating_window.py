# floating_window.py
import time

from PyQt6.QtCore import QEvent, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QCursor, QMouseEvent
from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget


class FloatingWindow(QWidget):
    """鼠标选中文本后，在文本右下角出现的翻译小图标"""

    clicked = pyqtSignal()

    # 使用信号跨线程控制UI
    show_signal = pyqtSignal()
    check_click_signal = pyqtSignal()
    hide_signal = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        # | Qt.WindowType.WindowDoesNotAcceptFocus
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

        layout.addWidget(self.label, alignment=Qt.AlignmentFlag.AlignCenter)

        # 绑定信号到对应的槽函数
        self.show_signal.connect(self._do_show_near_cursor)
        self.check_click_signal.connect(self._handle_global_click)
        self.hide_signal.connect(self._do_hide)

        # 记录上一次显示的时间
        self._show_time = 0.0

    def _do_hide(self):
        self.hide()

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

    def mouseReleaseEvent(self, event: QMouseEvent):
        # 点击自己会触发事件并隐藏，先隐藏再发送信号
        # 1. 先调用父类方法，让 Qt 走完内部的点击事件流程
        super().mousePressEvent(event)
        # 3. 【核心修复】强制清除 Label 和 悬浮窗的 "鼠标悬停" 状态
        # 这样下次显示时，hover 效果才能正常重新触发
        self.label.setAttribute(Qt.WidgetAttribute.WA_UnderMouse, False)
        self.setAttribute(Qt.WidgetAttribute.WA_UnderMouse, False)

        # 2. 发送触发翻译的信号
        self.clicked.emit()

        # 4. 最后再隐藏窗口
        self.hide()
