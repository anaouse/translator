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

# 引入我们刚才写的托盘类
from tray import TranslatorTray

kb = Controller()
_window = None


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
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(420, 260)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        self.text_edit = QTextEdit(self)
        self.text_edit.setReadOnly(True)
        self.text_edit.setStyleSheet("""
            QTextEdit {
                background-color: rgba(255, 255, 255, 1.0);
                color: #222222;
                border: 1px solid #cccccc;
                border-radius: 10px;
                padding: 15px;
                font-size: 15px;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
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
    kb.release(keyboard.Key.alt_l)
    kb.release(keyboard.Key.alt_r)
    kb.release("a")
    time.sleep(0.05)

    original = pyperclip.paste()
    pyperclip.copy("")

    with kb.pressed(keyboard.Key.ctrl):
        kb.press("c")
        time.sleep(0.1)
        kb.release("c")

    time.sleep(0.1)
    text = pyperclip.paste().strip()

    pyperclip.copy(original)
    return text


def on_trigger():
    print("triggered")
    text = get_selected_text()
    print(f"text: {text}")

    if not text or _window is None:
        return

    _window.update_text_signal.emit(text)


def on_mouse_click(x, y, button, pressed):
    if pressed and _window is not None:
        _window.check_click_signal.emit()


def start_listeners():
    kb_listener = GlobalHotKeys({"<alt>+a": on_trigger})
    kb_listener.daemon = True
    kb_listener.start()

    mouse_listener = mouse.Listener(on_click=on_mouse_click)
    mouse_listener.daemon = True
    mouse_listener.start()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 【关键修改 1】：确保即使所有窗口(Popup)被隐藏，程序也不会自动退出
    # 这样程序才能真正在后台运行，必须通过托盘右键退出
    app.setQuitOnLastWindowClosed(False)

    # 初始化弹出窗口
    _window = PopupWindow()

    # 【关键修改 2】：初始化并显示系统托盘
    tray = TranslatorTray()
    tray.show()

    # 启动快捷键和鼠标监听（它们是 daemon 线程，随主程序退出而停止）
    start_listeners()

    sys.exit(app.exec())
