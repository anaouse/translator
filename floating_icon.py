# floating_icon.py
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QMouseEvent
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget


class FloatingIcon(QWidget):
    """鼠标选中文本后，在文本右下角出现的翻译小图标"""

    clicked = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(28, 28)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.label = QLabel(self)
        self.label.setFixedSize(18, 18)
        self.label.setStyleSheet("""
            QLabel {
                background-color: white;
                border: 3px solid black;
            }
        """)
        self.label.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.label, alignment=Qt.AlignmentFlag.AlignCenter)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
