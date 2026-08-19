# main.py
import ctypes
import re
import sys
import threading
import time
import pyttsx3

import pyperclip
from pynput import keyboard, mouse
from pynput.keyboard import Controller, GlobalHotKeys
from PyQt6.QtCore import QEvent, Qt, pyqtSignal
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QApplication, QHBoxLayout, QPushButton, QTextEdit, QVBoxLayout, QWidget

from detect_select_text import create_selection_listener
from flash_card_window import FlashCardWindow
from floating_window import FloatingWindow
from global_variant import g_previous_hwnd, restore_previous_window
from input_window import InputWindow
from translation import youdao_translation
from tray import TranslatorTray
from word_store import add_word, flush

kb = Controller()
_window = None
_floating_window = None
_input_window = None
_flash_card_window = None

_last_trigger_time = 0.0
DEBOUNCE_SECONDS = 0.5


class PopupWindow(QWidget):
    update_text_signal = pyqtSignal(str, str)  # original_text, translated_text
    check_click_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setObjectName("popupWindow")

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )

        self.resize(420, 220)
        self._original_text = ""
        self._speaking = False

        # ---- 整体窗口样式（仅作用于 PopupWindow 自身） ----
        self.setStyleSheet("""
            QWidget#popupWindow {
                background-color: rgba(250, 250, 250, 0.98);
                border-radius: 14px;
                border: 1px solid rgba(0, 0, 0, 0.08);
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ---- Header ----
        header = QWidget()
        header.setStyleSheet("""
            QWidget {
                background: transparent;
                border-bottom: 1px solid rgba(0, 0, 0, 0.06);
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 8, 12, 8)

        self.pronounce_btn = QPushButton("🔊")
        self.pronounce_btn.setFixedSize(32, 32)
        self.pronounce_btn.setToolTip("发音")
        self.pronounce_btn.setStyleSheet("""
            QPushButton {
                background: rgba(0, 0, 0, 0.04);
                border: none;
                border-radius: 8px;
                font-size: 16px;
            }
            QPushButton:hover {
                background: rgba(0, 0, 0, 0.08);
            }
            QPushButton:pressed {
                background: rgba(0, 0, 0, 0.12);
            }
        """)
        self.pronounce_btn.clicked.connect(self._pronounce)
        self.pronounce_btn.hide()  # 默认隐藏，有英文原文时才显示
        header_layout.addWidget(self.pronounce_btn)
        header_layout.addStretch()

        layout.addWidget(header)

        # ---- 翻译结果显示 ----
        self.text_edit = QTextEdit(self)
        self.text_edit.setReadOnly(True)
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

        # 加入 eventfilter 控制 esc 行为：
        self.text_edit.installEventFilter(self)

        self.update_text_signal.connect(self._display_and_show)
        self.check_click_signal.connect(self._handle_global_click)

    # PopupWindow 类内
    def eventFilter(self, obj, event):
        if obj == self.text_edit and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Escape:
                self.hide()
                restore_previous_window()
                return True
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event):
        # 兜底：无论焦点在弹窗内哪个控件上，ESC 都能隐藏弹窗
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            restore_previous_window()
            return
        super().keyPressEvent(event)

    def _display_and_show(self, original_text, translated_text):
        global g_previous_hwnd
        self._original_text = original_text

        current_hwnd = ctypes.windll.user32.GetForegroundWindow()
        if current_hwnd != int(self.winId()):
            g_previous_hwnd = current_hwnd

        self.text_edit.setPlainText(translated_text)

        # 只有原文是英文时才显示发音按钮
        if original_text and _is_english(original_text):
            self.pronounce_btn.show()
        else:
            self.pronounce_btn.hide()

        if not self.isVisible():
            # 只在首次显示时定位到鼠标位置
            self._move_near_cursor()
            self.show()
            self.raise_()
            self.activateWindow()
            # 把键盘焦点给到文本区，否则按键事件到不了 text_edit，ESC 无法生效
            self.text_edit.setFocus()

    def _move_near_cursor(self):
        """把弹窗放到鼠标右下方；超出屏幕时翻转到鼠标左/上方，再夹取到屏幕可用区域内"""
        cursor = QCursor.pos()
        screen = QApplication.screenAt(cursor)
        if screen is None:
            screen = QApplication.primaryScreen()
        area = screen.availableGeometry()

        offset = 15
        w, h = self.width(), self.height()

        # 默认放到鼠标右下方
        x = cursor.x() + offset
        y = cursor.y() + offset

        # 右/下放不下就翻转到左/上方
        if x + w > area.right():
            x = cursor.x() - w - offset
        if y + h > area.bottom():
            y = cursor.y() - h - offset

        # 兜底：夹取到可用屏幕范围内，保证完全可见
        x = max(area.left(), min(x, area.right() - w))
        y = max(area.top(), min(y, area.bottom() - h))

        self.move(x, y)

    def _handle_global_click(self):
        if self.isVisible():
            pos = QCursor.pos()
            if not self.frameGeometry().contains(pos):
                self.hide()

    def _pronounce(self):
        """在子线程中发音，避免阻塞 UI；正在发音时忽略重复点击"""
        if self._original_text and not self._speaking:
            self._speaking = True
            threading.Thread(
                target=self._speak, args=(self._original_text,), daemon=True
            ).start()

    def _speak(self, text: str):
        try:
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
        finally:
            self._speaking = False


def get_selected_text() -> str:
    # 有时候会单单点击 a 就翻译，估计是这里的问题，因为不是用真正的系统级别热键
    # kb.release(keyboard.Key.alt)
    # kb.release("a")
    time.sleep(0.1)

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


def _is_english(text: str) -> bool:
    # 允许：英文字母、数字、空格、常用标点
    # ^[ -~]+$ 匹配 ASCII 32 到 126 的所有可打印字符
    return bool(re.match(r'^[a-zA-Z0-9\s\.,!?"\'-]+$', text))


def _is_successful_result(result: str) -> bool:
    """Return True if the translation result is a real result (not an error)."""
    return not result.startswith("error:")


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
        if _input_window:
            _input_window.show_signal.emit()
        return
    # 先显示"正在翻译..."
    if _window is not None:
        _window.update_text_signal.emit(text, "正在翻译...")
    result = youdao_translation(text)
    _window.update_text_signal.emit(text, result)

    # Store English word lookups
    if _is_english(text) and _is_successful_result(result):
        add_word(text, result)


def on_input_submit(text: str):
    if not text or _window is None:
        return
    _window.update_text_signal.emit(text, "正在翻译...")
    result = youdao_translation(text)
    _window.update_text_signal.emit(text, result)

    # Store English word lookups
    if _is_english(text) and _is_successful_result(result):
        add_word(text, result)


def on_show_input_window():
    if _input_window:
        _input_window.show_signal.emit()


def on_mouse_click(x, y, button, pressed):
    if not pressed:
        return

    if _floating_window is not None:
        _floating_window.check_click_signal.emit()

    if _window is not None:
        _window.check_click_signal.emit()

    if _input_window is not None:
        _input_window.check_click_signal.emit()


def on_select_text(action_type):
    global _floating_window
    print(f"[{time.strftime('%H:%M:%S')}] 文本被选中了！触发方式: {action_type}")

    # 只要实例存在就发送信号
    if _floating_window is not None:
        print("floating 信号已发送")
        _floating_window.show_signal.emit()


def on_any_key(key):
    """按下任意键时隐藏悬浮窗"""
    if _floating_window is not None:
        _floating_window.hide_signal.emit()


def start_listeners():
    kb_listener = GlobalHotKeys(
        {
            "<alt>+q": on_show_input_window,
            "<alt>+a": on_trigger,
        }
    )
    kb_listener.daemon = True
    kb_listener.start()

    # 单独的监听器：任意键按下时隐藏悬浮窗
    any_key_listener = keyboard.Listener(on_press=on_any_key)
    any_key_listener.daemon = True
    any_key_listener.start()

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

    # 初始化输入窗
    _input_window = InputWindow()
    _input_window.submit_signal.connect(
        lambda text: threading.Thread(
            target=on_input_submit, args=(text,), daemon=True
        ).start()
    )

    # 初始化闪卡窗口（左键托盘弹出）
    _flash_card_window = FlashCardWindow()

    # 初始化系统托盘
    tray = TranslatorTray()
    tray.left_clicked.connect(_flash_card_window.show_signal.emit)
    tray.show()

    # 启动快捷键和鼠标监听（它们是 daemon 线程，随主程序退出而停止）
    start_listeners()

    # Flush remaining word store entries when the app quits
    app.aboutToQuit.connect(flush)

    sys.exit(app.exec())
