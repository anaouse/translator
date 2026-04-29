# input_window.py

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QLineEdit, QVBoxLayout, QWidget


class InputWindow(QWidget):
    """alt + a 如果没有文本的话跳出的输入框翻译"""

    show_and_clear_signal = pyqtSignal()
    check_click_signal = pyqtSignal()
    hide_signal = pyqtSignal()
    submit_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )

        self.resize(340, 52)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.input_edit = QLineEdit(self)
        self.input_edit.setPlaceholderText("输入要翻译的文本，按 Enter 翻译…")
        self.input_edit.setStyleSheet("""
            QLineEdit {
                background-color: rgba(250, 250, 250, 0.98);
                color: #1f1f1f;
                border: 1px solid rgba(0, 0, 0, 0.1);
                border-radius: 10px;
                padding: 10px 16px;
                font-size: 15px;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI",
                             Roboto, Helvetica, Arial, sans-serif;
            }
            QLineEdit:focus {
                border: 1px solid rgba(0, 120, 215, 0.6);
                background-color: rgba(255, 255, 255, 0.98);
            }
        """)
        # 按 Enter 发射文本
        self.input_edit.returnPressed.connect(self._on_submit)

        layout.addWidget(self.input_edit)

        # 绑定信号到对应的槽函数
        self.show_and_clear_signal.connect(self._show_and_clear)
        self.check_click_signal.connect(self._check_click)
        self.hide_signal.connect(self._do_hide)

    def _on_submit(self):
        text = self.input_edit.text().strip()
        if text:
            self.submit_signal.emit(text)
            self.hide()

    def _do_hide(self):
        self.hide()

    def _show_and_clear(self):
        self.input_edit.clear()
        cursor = QCursor.pos()
        self.move(cursor.x() + 15, cursor.y())
        self.show()
        self.raise_()
        self.activateWindow()
        self.input_edit.setFocus()

    def _check_click(self):
        """鼠标点击窗户外边就自己消失"""
        if self.isVisible():
            pos = QCursor.pos()
            if not self.frameGeometry().contains(pos):
                self.hide()
