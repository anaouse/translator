# main.py
import sys
import threading
import time

import pyperclip
from pynput import keyboard, mouse
from pynput.keyboard import Controller, GlobalHotKeys
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QApplication, QTextEdit, QVBoxLayout, QWidget

from detect_select_text import create_selection_listener
from floating_window import FloatingWindow
from translation import youdao_translation
from tray import TranslatorTray

kb = Controller()
_window = None
_floating_window = None

_last_trigger_time = 0.0
DEBOUNCE_SECONDS = 0.5


class PopupWindow(QWidget):
    update_text_signal = pyqtSignal(str)
    check_click_signal = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )

        self.resize(420, 260)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.text_edit = QTextEdit(self)
        self.text_edit.setReadOnly(True)
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(250, 250, 250, 0.98);
                border-radius: 14px;
                border: 1px solid rgba(0, 0, 0, 0.08);
            }
        """)
        self.text_edit.setStyleSheet("""
            QTextEdit {
                background-color: transparent;
                color: #1f1f1f;
                border: none;
                padding: 18px;
                font-size: 15px;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                line-height: 1.5;
            }
        """)
        layout.addWidget(self.text_edit)

        self.update_text_signal.connect(self._display_and_show)
        self.check_click_signal.connect(self._handle_global_click)

    def _display_and_show(self, text):
        self.text_edit.setPlainText(text)
        cursor = QCursor.pos()
        self.move(cursor.x() + 15, cursor.y() + 15)
        self.show()
        self.raise_()
        self.activateWindow()

    def _handle_global_click(self):
        if self.isVisible():
            pos = QCursor.pos()
            if not self.frameGeometry().contains(pos):
                self.hide()


def get_selected_text() -> str:
    kb.release(keyboard.Key.alt)
    kb.release("a")
    time.sleep(0.05)

    original = pyperclip.paste()
    pyperclip.copy("")

    with kb.pressed(keyboard.Key.ctrl):
        kb.press("c")
        time.sleep(0.05)
        kb.release("c")

    time.sleep(0.05)
    text = pyperclip.paste().strip()

    pyperclip.copy(original)
    return text


def on_trigger():
    global _last_trigger_time
    now = time.time()
    if now - _last_trigger_time < DEBOUNCE_SECONDS:
        return
    if _floating_window is not None:
        _floating_window.hide_signal.emit()
    print("triggered")
    text = get_selected_text()
    print(f"text: {text}")

    if not text or _window is None:
        return
    result = youdao_translation(text)
    _window.update_text_signal.emit(result)


def on_mouse_click(x, y, button, pressed):
    if not pressed:
        return

    if _floating_window is not None:
        _floating_window.check_click_signal.emit()

    if _window is not None:
        _window.check_click_signal.emit()


def on_select_text(action_type):
    global _floating_window
    print(f"[{time.strftime('%H:%M:%S')}] 文本被选中了！触发方式: {action_type}")

    # 只要实例存在就发送信号
    if _floating_window is not None:
        print("floating 信号已发送")
        _floating_window.show_signal.emit()


def on_alt_tab():
    """按下 Alt+Tab 时隐藏悬浮窗"""
    if _floating_window is not None:
        _floating_window.hide_signal.emit()


def start_listeners():
    kb_listener = GlobalHotKeys(
        {
            "<alt>+a": on_trigger,
            "<alt>+<tab>": on_alt_tab,
        }
    )
    kb_listener.daemon = True
    kb_listener.start()

    mouse_listener = mouse.Listener(on_click=on_mouse_click)
    mouse_listener.daemon = True
    mouse_listener.start()

    select_text_listener = create_selection_listener(on_select_text)
    select_text_listener.daemon = True
    select_text_listener.start()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 确保即使所有窗口(Popup)被隐藏，程序也不会自动退出这样程序才能真正在后台运行，必须通过托盘右键退出
    app.setQuitOnLastWindowClosed(False)

    # 初始化弹出窗口
    _window = PopupWindow()

    # 初始化小图标
    _floating_window = FloatingWindow()
    _floating_window.clicked.connect(
        lambda: threading.Thread(target=on_trigger, daemon=True).start()
    )

    # 初始化系统托盘
    tray = TranslatorTray()
    tray.show()

    # 启动快捷键和鼠标监听（它们是 daemon 线程，随主程序退出而停止）
    start_listeners()

    sys.exit(app.exec())
