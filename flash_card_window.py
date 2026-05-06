# flash_card_window.py
"""Left-click tray → flash card window showing word lookup history."""

import json
import random
import sys
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


def _get_json_path() -> Path:

    if getattr(sys, "frozen", False):
        base_path = Path(sys.executable).parent
    else:
        base_path = Path(__file__).resolve().parent
    return base_path / "english_words.json"


class FlashCardWindow(QWidget):
    """Show English word lookup history in flash card format."""

    show_signal = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.WindowTitleHint
        )
        self.setWindowTitle("单词回顾")

        self.resize(480, 420)

        self.setStyleSheet("""
            FlashCardWindow {
                background-color: rgba(250, 250, 250, 0.98);
                border-radius: 14px;
                border: 1px solid rgba(0, 0, 0, 0.08);
            }
        """)

        # --- Data ---
        self._words: list[dict] = []
        self._current_index: int = 0

        # --- Layout ---
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(8)

        # == Top panel ==
        top = QHBoxLayout()
        top.setSpacing(8)

        self._count_label = QLabel("单词数：0")
        self._count_label.setStyleSheet("""
            QLabel {
                color: #888;
                font-size: 13px;
                padding: 4px 0;
            }
        """)
        top.addWidget(self._count_label)

        top.addStretch()

        shuffle_btn = QPushButton("🎲 随机")
        shuffle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        shuffle_btn.setFixedSize(80, 28)
        shuffle_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(100, 140, 200, 0.15);
                color: #5E81AC;
                border: 1px solid rgba(94, 129, 172, 0.3);
                border-radius: 6px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: rgba(100, 140, 200, 0.25);
            }
            QPushButton:pressed {
                background-color: rgba(100, 140, 200, 0.35);
            }
        """)
        shuffle_btn.clicked.connect(self._shuffle)
        top.addWidget(shuffle_btn)

        root.addLayout(top)

        # == Card area (scrollable) ==
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid rgba(0, 0, 0, 0.06);
                border-radius: 10px;
                background-color: rgba(255, 255, 255, 0.8);
            }
            QScrollBar:vertical {
                width: 6px;
                background: transparent;
            }
            QScrollBar::handle:vertical {
                background: rgba(0, 0, 0, 0.12);
                border-radius: 3px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
        """)

        card = QWidget()
        card.setStyleSheet("background: transparent;")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(12)

        # Query (headword)
        self._query_label = QLabel()
        self._query_label.setWordWrap(True)
        self._query_label.setStyleSheet("""
            QLabel {
                color: #2E3440;
                font-size: 28px;
                font-weight: bold;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI",
                             Roboto, Helvetica, Arial, sans-serif;
                padding: 0;
            }
        """)
        card_layout.addWidget(self._query_label)

        # Separator
        sep = QLabel()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: rgba(0, 0, 0, 0.06);")
        card_layout.addWidget(sep)

        # Results
        self._results_label = QLabel()
        self._results_label.setWordWrap(True)
        self._results_label.setStyleSheet("""
            QLabel {
                color: #4C566A;
                font-size: 15px;
                line-height: 1.6;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI",
                             Roboto, Helvetica, Arial, sans-serif;
                padding: 2px 0;
            }
        """)
        card_layout.addWidget(self._results_label)

        # Lookup count
        self._lookup_label = QLabel()
        self._lookup_label.setStyleSheet("""
            QLabel {
                color: #81A1C1;
                font-size: 13px;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI",
                             Roboto, Helvetica, Arial, sans-serif;
                padding: 4px 0;
            }
        """)
        card_layout.addWidget(self._lookup_label)

        card_layout.addStretch()
        scroll.setWidget(card)
        root.addWidget(scroll, stretch=1)

        # == Bottom panel (arrows) ==
        bottom = QHBoxLayout()
        bottom.setSpacing(12)

        bottom.addStretch()

        left_btn = QPushButton("← 上一个")
        left_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        left_btn.setFixedSize(90, 30)
        left_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(100, 140, 200, 0.12);
                color: #5E81AC;
                border: 1px solid rgba(94, 129, 172, 0.25);
                border-radius: 6px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: rgba(100, 140, 200, 0.22);
            }
            QPushButton:pressed {
                background-color: rgba(100, 140, 200, 0.32);
            }
            QPushButton:disabled {
                color: #ccc;
                background-color: rgba(0, 0, 0, 0.04);
                border-color: rgba(0, 0, 0, 0.08);
            }
        """)
        left_btn.clicked.connect(self._prev)
        bottom.addWidget(left_btn)
        self._left_btn = left_btn

        self._index_label = QLabel("0 / 0")
        self._index_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._index_label.setFixedWidth(60)
        self._index_label.setStyleSheet("color: #888; font-size: 13px;")
        bottom.addWidget(self._index_label)

        right_btn = QPushButton("下一个 →")
        right_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        right_btn.setFixedSize(90, 30)
        right_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(100, 140, 200, 0.12);
                color: #5E81AC;
                border: 1px solid rgba(94, 129, 172, 0.25);
                border-radius: 6px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: rgba(100, 140, 200, 0.22);
            }
            QPushButton:pressed {
                background-color: rgba(100, 140, 200, 0.32);
            }
            QPushButton:disabled {
                color: #ccc;
                background-color: rgba(0, 0, 0, 0.04);
                border-color: rgba(0, 0, 0, 0.08);
            }
        """)
        right_btn.clicked.connect(self._next)
        bottom.addWidget(right_btn)
        self._right_btn = right_btn

        bottom.addStretch()
        root.addLayout(bottom)

        # Connect signals
        self.show_signal.connect(self._show_and_load)

    def closeEvent(self, event):
        """Override close: hide instead of destroying."""
        self.hide()
        event.ignore()

    # --- Logic ---
    def _load_words(self) -> list[dict]:
        path = _get_json_path()
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except (json.JSONDecodeError, OSError):
            pass
        return []

    def _shuffle(self):
        """Re-shuffle and show first word."""
        random.shuffle(self._words)
        self._current_index = 0
        if self._words:
            self._show_word(0)
        self._update_buttons()

    def _show_word(self, index: int):
        if not self._words or index < 0 or index >= len(self._words):
            self._query_label.setText("")
            self._results_label.setText("")
            self._lookup_label.setText("")
            self._index_label.setText("0 / 0")
            return

        word = self._words[index]
        self._query_label.setText(word.get("query", ""))
        self._results_label.setText(word.get("results", ""))
        count = word.get("lookup_count", 1)
        self._lookup_label.setText(f"查询次数：{count}")
        self._index_label.setText(f"{index + 1} / {len(self._words)}")

    def _update_buttons(self):
        n = len(self._words)
        if n == 0:
            self._left_btn.setEnabled(False)
            self._right_btn.setEnabled(False)
            self._count_label.setText("单词数：0")
            return
        self._left_btn.setEnabled(self._current_index > 0)
        self._right_btn.setEnabled(self._current_index < n - 1)
        self._count_label.setText(f"单词数：{n}")

    def _prev(self):
        if self._current_index > 0:
            self._current_index -= 1
            self._show_word(self._current_index)
            self._update_buttons()

    def _next(self):
        if self._current_index < len(self._words) - 1:
            self._current_index += 1
            self._show_word(self._current_index)
            self._update_buttons()

    # --- Show / Hide ---
    def _show_and_load(self):
        """Load JSON, shuffle, and show window at screen center."""
        self._words = self._load_words()
        if self._words:
            random.shuffle(self._words)
            self._current_index = 0
            self._show_word(0)
        else:
            self._current_index = 0
            self._query_label.setText("（暂无单词记录）")
            self._results_label.setText("")
            self._lookup_label.setText("")
            self._index_label.setText("0 / 0")
        self._update_buttons()

        center = QApplication.primaryScreen().availableGeometry().center()
        self.move(center.x() - self.width() // 2, center.y() - self.height() // 2)
        self.show()
        self.raise_()
        self.activateWindow()


