# floating_icon.py
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QMouseEvent
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget


class FloatingIcon(QWidget):
    """鼠标选中文本后，在文本右下角出现的翻译小图标"""

    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(36, 36)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.label = QLabel("🔤", self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("""
            QLabel {
                background-color: rgba(255, 255, 255, 0.95);
                border: 1px solid #cccccc;
                border-radius: 18px;
                font-size: 18px;
            }
        """)
        self.label.setFixedSize(36, 36)
        layout.addWidget(self.label)

        self.hide()

    def show_at(self, x: int, y: int):
        """在指定坐标（右下角偏移）显示图标"""
        self.move(x + 10, y + 10)
        self.show()
        self.raise_()
        self.activateWindow()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            self.hide()
        super().mousePressEvent(event)
